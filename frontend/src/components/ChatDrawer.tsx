'use client';

import React, { useState } from 'react';
import { useChatStore } from '../stores/useChatStore';
import { X, Send, Sparkles, RefreshCw, Bot, User } from 'lucide-react';

export const ChatDrawer: React.FC = () => {
  const { isDrawerOpen, toggleDrawer, messages, sendMessage, isThinking, resetConversation } = useChatStore();
  const [input, setInput] = useState('');

  if (!isDrawerOpen) return null;

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim() || isThinking) return;
    sendMessage(input.trim());
    setInput('');
  };

  const samplePrompts = [
    "What's blocking the Q4 forecast?",
    "Who has overdue tasks this week?",
    "Summarize yesterday's executive meeting.",
  ];

  return (
    <div className="fixed inset-0 z-50 overflow-hidden bg-black/20 backdrop-blur-xs flex justify-end">
      <div className="w-full max-w-lg bg-stone-canvas h-full border-l border-stone-border flex flex-col shadow-xl animate-in slide-in-from-right duration-200">
        {/* Drawer Header */}
        <div className="p-4 bg-white border-b border-stone-border flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Sparkles className="w-5 h-5 text-cyan-signal" />
            <h2 className="font-semibold text-ink-black text-base">Sentinel AI Companion</h2>
          </div>
          <div className="flex items-center gap-1">
            <button
              onClick={resetConversation}
              className="p-1.5 text-warm-gray hover:text-ink-black hover:bg-stone-canvas rounded"
              title="Reset Chat"
            >
              <RefreshCw className="w-4 h-4" />
            </button>
            <button
              onClick={() => toggleDrawer(false)}
              className="p-1.5 text-warm-gray hover:text-ink-black hover:bg-stone-canvas rounded"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Chat Messages Stream */}
        <div className="flex-1 overflow-y-auto p-4 space-y-4">
          {messages.map((msg) => (
            <div
              key={msg.id}
              className={`flex gap-3 text-sm ${msg.sender === 'user' ? 'justify-end' : 'justify-start'}`}
            >
              {msg.sender === 'agent' && (
                <div className="w-7 h-7 rounded-full bg-ink-black text-white flex items-center justify-center shrink-0 mt-0.5">
                  <Bot className="w-4 h-4 text-cyan-signal" />
                </div>
              )}
              <div
                className={`max-w-[85%] p-3.5 rounded-xl space-y-2 ${
                  msg.sender === 'user'
                    ? 'bg-ink-black text-white rounded-br-none'
                    : 'stone-card text-ink-black rounded-bl-none'
                }`}
              >
                <p className="leading-relaxed whitespace-pre-wrap">{msg.content}</p>
                {msg.tool_executions && msg.tool_executions.length > 0 && (
                  <div className="pt-2 border-t border-stone-border text-xs space-y-1">
                    <span className="text-warm-gray font-medium">Executed Actions:</span>
                    {msg.tool_executions.map((t, idx) => (
                      <div key={idx} className="flex items-center gap-1.5 text-cyan-edge font-mono text-[11px]">
                        <span>✓</span>
                        <span>{t.tool}</span>
                      </div>
                    ))}
                  </div>
                )}
                <span className="text-[10px] text-warm-gray block text-right">{msg.timestamp}</span>
              </div>
              {msg.sender === 'user' && (
                <div className="w-7 h-7 rounded-full bg-cyan-signal text-white flex items-center justify-center shrink-0 mt-0.5">
                  <User className="w-4 h-4" />
                </div>
              )}
            </div>
          ))}

          {isThinking && (
            <div className="flex gap-3 text-sm">
              <div className="w-7 h-7 rounded-full bg-ink-black text-white flex items-center justify-center shrink-0">
                <Bot className="w-4 h-4 text-cyan-signal animate-spin" />
              </div>
              <div className="stone-card p-3 rounded-xl text-warm-gray text-xs flex items-center gap-2">
                <span>Sentinel is retrieving context from Postgres & HydraDB...</span>
              </div>
            </div>
          )}
        </div>

        {/* Quick Prompts */}
        <div className="p-3 bg-white border-t border-stone-border/60 flex flex-wrap gap-1.5">
          {samplePrompts.map((prompt, i) => (
            <button
              key={i}
              onClick={() => sendMessage(prompt)}
              className="text-xs px-2.5 py-1 rounded-full border border-stone-border text-warm-gray hover:text-ink-black hover:border-cyan-edge transition"
            >
              {prompt}
            </button>
          ))}
        </div>

        {/* Input Form */}
        <form onSubmit={handleSubmit} className="p-3 bg-white border-t border-stone-border flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            placeholder="Ask Sentinel anything about your business..."
            className="flex-1 px-3.5 py-2 text-sm border border-stone-border rounded-lg focus:outline-none focus:border-cyan-signal"
          />
          <button type="submit" disabled={!input.trim() || isThinking} className="btn-cyan px-4 py-2 text-sm flex items-center gap-1">
            <Send className="w-4 h-4" />
          </button>
        </form>
      </div>
    </div>
  );
};
