import React, { useState } from "react";
import { Send, ShieldCheck, FileText } from "lucide-react";
import { Button } from "../components/ui/Button";

export const AssistantPage: React.FC = () => {
  const [messages, setMessages] = useState([
    {
      role: "assistant",
      text: "AirOps Nexus AI Assistant initialized. I operate strictly in read-only mode using verified API tools and pgvector RAG citations. How can I assist with schedule analysis today?",
      sources: ["docs/scope-and-boundaries.md", "active-plan-v1.0"],
    },
  ]);
  const [input, setInput] = useState("");

  const handleSend = () => {
    if (!input.trim()) return;
    const userMsg = { role: "user", text: input, sources: [] };
    setMessages((prev) => [...prev, userMsg]);
    setInput("");

    setTimeout(() => {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          text: `Based on active baseline plan v1.0, fleet availability currently sits at 82.5% with 33 of 40 airframes ready. 3 critical spare parts are currently below minimum safety stock levels at Zone Delta.`,
          sources: ["GET /api/v1/overview", "GET /api/v1/spares"],
        },
      ]);
    }, 700);
  };

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between pb-4 border-b border-slate-200">
        <div>
          <h2 className="text-xl font-bold text-slate-900 tracking-tight">AI Assistant & Grounded RAG</h2>
          <p className="text-sm text-slate-500">
            Read-only decision support with mandatory document citations and zero autonomous write capability.
          </p>
        </div>
        <div className="flex items-center gap-1.5 text-xs text-emerald-600 font-medium">
          <ShieldCheck className="w-4 h-4" />
          <span>Read-Only Guardrails Active</span>
        </div>
      </div>

      <div className="bg-white rounded-lg border border-slate-200 h-[480px] flex flex-col shadow-sm">
        {/* Messages Scroll Area */}
        <div className="flex-1 p-5 overflow-y-auto space-y-4">
          {messages.map((m, idx) => (
            <div
              key={idx}
              className={`flex flex-col ${m.role === 'user' ? 'items-end' : 'items-start'}`}
            >
              <div
                className={`max-w-xl p-3.5 rounded-xl text-sm ${
                  m.role === 'user'
                    ? 'bg-blue-600 text-white'
                    : 'bg-slate-100 text-slate-800'
                }`}
              >
                {m.text}
              </div>
              {m.sources.length > 0 && (
                <div className="flex items-center gap-1.5 mt-1 text-[11px] text-slate-400">
                  <FileText className="w-3 h-3" />
                  <span>Cited Sources: {m.sources.join(", ")}</span>
                </div>
              )}
            </div>
          ))}
        </div>

        {/* Input bar */}
        <div className="p-3 border-t border-slate-200 flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleSend()}
            placeholder="Ask about active alerts, plan differences, or resource shortages..."
            className="flex-1 px-4 py-2 border border-slate-300 rounded-lg text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <Button variant="primary" size="sm" onClick={handleSend}>
            <Send className="w-4 h-4 mr-1" />
            Send
          </Button>
        </div>
      </div>
    </div>
  );
};
