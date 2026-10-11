import os

with open('frontend/src/App.tsx', 'r', encoding='utf-8') as f:
    content = f.read()

target = '<div className="conflict-list">{p.conflicts.map'
rep = '<div className="conflict-list"><p className="eyebrow" style={{marginBottom: 10, lineHeight: 1.4, color: "#94a3b8", fontSize: "10px", textTransform: "none"}}>Algorithmically predicted conflicts, not confirmed real-world ATC violations. {live && p.conflicts.length > 10 ? `Showing top 10 of ${p.conflicts.length}.` : ""}</p>{p.conflicts.slice(0, 10).map'

content = content.replace(target, rep)

with open('frontend/src/App.tsx', 'w', encoding='utf-8') as f:
    f.write(content)
