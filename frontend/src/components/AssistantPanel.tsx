import React, { useState, useRef, useEffect } from 'react';
import { MessageSquare, Send, Loader2, Minimize2, Maximize2 } from 'lucide-react';
import { askAssistant } from '../api/rest';

interface Message {
  role: 'user' | 'assistant';
  content: string;
}

export const AssistantPanel: React.FC<{ activeConflictId?: string }> = ({ activeConflictId }) => {
  const [messages, setMessages] = useState<Message[]>([
    { role: 'assistant', content: 'ATC Assistant ready. How can I help you manage the airspace today?' }
  ]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [expanded, setExpanded] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg = input.trim();
    setInput('');
    setMessages((prev) => [...prev, { role: 'user', content: userMsg }]);
    setLoading(true);

    try {
      const answer = await askAssistant(userMsg, activeConflictId);
      setMessages((prev) => [...prev, { role: 'assistant', content: answer }]);
    } catch (err) {
      setMessages((prev) => [...prev, { role: 'assistant', content: 'Sorry, I encountered an error. Please try again.' }]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  if (!expanded) {
    return (
      <button 
        onClick={() => setExpanded(true)}
        className="absolute bottom-4 right-4 bg-sky-600 hover:bg-sky-500 text-white p-3 rounded-full shadow-2xl transition-all z-20 flex items-center space-x-2"
      >
        <MessageSquare className="w-5 h-5" />
        <span className="font-bold text-sm tracking-wide pr-1">ATC Assistant</span>
      </button>
    );
  }

  return (
    <div className="absolute bottom-4 right-4 w-96 h-96 bg-slate-950/95 border border-slate-800/90 rounded-lg shadow-2xl flex flex-col overflow-hidden z-20 backdrop-blur-md">
      {/* Header */}
      <div className="flex items-center justify-between bg-slate-900 border-b border-slate-800 p-3">
        <div className="flex items-center space-x-2 text-sky-400">
          <MessageSquare className="w-4 h-4" />
          <h3 className="font-bold text-sm tracking-wider">ATC AI ASSISTANT</h3>
        </div>
        <button onClick={() => setExpanded(false)} className="text-slate-400 hover:text-slate-200">
          <Minimize2 className="w-4 h-4" />
        </button>
      </div>

      {/* Messages */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto p-4 space-y-4 custom-scrollbar">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded p-2.5 text-xs leading-relaxed ${
              msg.role === 'user' 
                ? 'bg-sky-600/90 text-white rounded-br-none' 
                : 'bg-slate-800/80 text-slate-200 rounded-bl-none border border-slate-700/50'
            }`}>
              {msg.content}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="bg-slate-800/80 p-2.5 rounded rounded-bl-none border border-slate-700/50 flex items-center space-x-2 text-slate-400">
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
              <span className="text-[10px]">Analyzing data...</span>
            </div>
          </div>
        )}
      </div>

      {/* Input */}
      <div className="p-3 bg-slate-900 border-t border-slate-800 flex items-center space-x-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleKeyDown}
          placeholder={activeConflictId ? `Ask about conflict ${activeConflictId}...` : "Ask about the airspace..."}
          className="flex-1 bg-slate-950 border border-slate-800 rounded px-3 py-2 text-xs text-slate-200 focus:outline-none focus:border-sky-500 transition-colors"
        />
        <button 
          onClick={handleSend}
          disabled={loading || !input.trim()}
          className="bg-sky-600 hover:bg-sky-500 disabled:opacity-50 disabled:hover:bg-sky-600 text-white p-2 rounded transition-colors"
        >
          <Send className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};
