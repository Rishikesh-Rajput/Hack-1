"""GenAI Explanation Service and Controller Assistant.

Provides clear, natural-language explanations of conflict resolutions
and answers queries based strictly on simulation data.
"""

from __future__ import annotations

import os
import logging
from typing import Any

from core.models.config import GenAIConfig
from core.models.conflict import Conflict
from core.models.resolution import Recommendation

logger = logging.getLogger(__name__)

class ExplanationService:
    """Generates explanations and handles assistant queries."""

    def __init__(self, config: GenAIConfig) -> None:
        self.config = config
        self.api_key = os.getenv("GEMINI_API_KEY", config.api_key)
        self.client = None
        
        # Try to initialize the Gemini client
        if self.api_key:
            try:
                from google import genai
                self.client = genai.Client(api_key=self.api_key)
                logger.info("GenAI client initialized successfully.")
            except ImportError:
                logger.warning("google-genai package not found. Using deterministic fallback.")
            except Exception as e:
                logger.warning(f"Failed to initialize GenAI client: {e}")

    def explain_recommendation(self, conflict: Conflict, recommendation: Recommendation) -> str:
        """Generate an explanation for a recommendation."""
        # 1. Deterministic baseline (always generated to ensure ground truth)
        fallback_text = self._generate_fallback_explanation(conflict, recommendation)

        # 2. If GenAI is enabled and available, enhance it
        if self.client and not self.config.fallback_enabled:
            pass # We always want fallback available as a safety net anyway
            
        if not self.client:
            return fallback_text
            
        # Call Gemini to polish the explanation
        try:
            prompt = (
                f"You are an AI assistant for Air Traffic Controllers. "
                f"Translate this structured resolution into a concise, professional 2-3 sentence summary:\n\n"
                f"Raw Data:\n{fallback_text}\n\n"
                f"Rules: Be concise. State the exact maneuver. Highlight separation improvements and any warnings."
            )
            
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=prompt,
                config={
                    "temperature": self.config.temperature,
                    "max_output_tokens": self.config.max_tokens,
                }
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.error(f"GenAI explanation generation failed: {e}. Falling back.")
            
        return fallback_text

    def answer_assistant_query(self, query: str, context: dict[str, Any]) -> str:
        """Answer a controller's query using the provided context."""
        if not self.client:
            return self._generate_fallback_answer(context)
            
        try:
            prompt = (
                f"You are an Air Traffic Control AI assistant. Answer the controller's question concisely, "
                f"strictly using the following simulation context. Do not invent maneuvers or data.\n\n"
                f"Context:\n{context}\n\n"
                f"Controller Question: {query}"
            )
            
            response = self.client.models.generate_content(
                model=self.config.model,
                contents=prompt,
                config={
                    "temperature": 0.1,
                    "max_output_tokens": self.config.max_tokens,
                }
            )
            if response and response.text:
                return response.text.strip()
        except Exception as e:
            logger.error(f"Assistant query failed: {e}")
            return "I encountered an error processing your request. Please check the dashboard data directly."
            
        return "I could not generate an answer at this time."

    def _generate_fallback_answer(self, context: dict[str, Any]) -> str:
        """Provide useful, grounded context when the optional GenAI service is unavailable."""
        recommendation = context.get("recommendation")
        if recommendation:
            explanation = recommendation.get("explanation")
            warnings = recommendation.get("warnings") or []
            answer = explanation or "A recommendation is available for the selected conflict."
            if warnings:
                answer += " Warnings: " + " ".join(str(warning) for warning in warnings)
            return answer + " Configure GEMINI_API_KEY for free-form generative answers."

        conflicts = context.get("active_conflicts") or []
        if conflicts:
            return (
                f"There are {len(conflicts)} active predicted conflict(s). "
                "Select a conflict to receive its maneuver-specific explanation. "
                "Configure GEMINI_API_KEY for free-form generative answers."
            )
        return "No active predicted conflicts are available. Configure GEMINI_API_KEY for free-form generative answers."

    def _generate_fallback_explanation(self, conflict: Conflict, rec: Recommendation) -> str:
        """Deterministic string-builder explanation."""
        if rec.status != "RECOMMENDATION_AVAILABLE" or not rec.primary_candidate:
            return "No feasible recommendation is available. All generated maneuvers either violated safety thresholds or caused secondary conflicts."
            
        c = rec.primary_candidate
        m = c.maneuver
        
        maneuver_str = ""
        if m.type == "HEADING":
            dir = "Right" if m.heading_change > 0 else "Left"
            maneuver_str = f"Turn {dir} by {abs(m.heading_change)} degrees"
        elif m.type == "ALTITUDE":
            dir = "Climb" if m.altitude_change > 0 else "Descend"
            maneuver_str = f"{dir} by {abs(m.altitude_change)} feet"
        elif m.type == "SPEED":
            dir = "Increase" if m.speed_change > 0 else "Decrease"
            maneuver_str = f"{dir} speed by {abs(m.speed_change)} knots"
            
        text = f"Recommend {c.aircraft_id} to {maneuver_str}. "
        
        if c.simulation_result:
            text += (
                f"This achieves {round(c.simulation_result.min_horizontal_separation_nm, 1)} NM horizontal "
                f"and {round(c.simulation_result.min_vertical_separation_ft, 0)} ft vertical separation at CPA. "
            )
            
            if c.simulation_result.new_conflicts:
                text += f"WARNING: This maneuver introduces {len(c.simulation_result.new_conflicts)} new downstream conflict(s). "
                
        if rec.warnings:
            text += " ".join(rec.warnings)
            
        return text
