'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useChatStore } from '@/stores/useChatStore';
import { useAuthStore } from '@/stores/useAuthStore';
import { ToolExecutionPanel } from '@/components/chat';
import { MarkdownText, BrandMark, SentinelBot } from '@/components/ui';
import { ArrowUp, Plus, MessageSquare, Trash2, AlertCircle, PanelLeft, X } from 'lucide-react';

const SUGGESTIONS = [
  "What's overdue right now?",
  'What is blocking the team this week?',
  'Summarize commitments from our last meeting',
  'What did we decide about pricing?',
];

export default function ChatPage() {
  const {
    conversations,
    conversationId,
    messages,
    isThinking,
    isLoadingThread,
    error,
    fetchConversations,
    selectConversation,
    newConversation,
    deleteConversation,
    sendMessage,
  } = useChatStore();
  const { user } = useAuthStore();
  const [input, setInput] = useState('');
  // Below lg the thread list is an overlay rather than a permanent column.
  const [showThreads, setShowThreads] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const assistantName = user?.company?.persona_config?.assistant_name || 'Sentinel';

  useEffect(() => {
    fetchConversations();
  }, [fetchConversations]);

  // Keep the newest turn in view as the thread grows.
  useEffect(() => {
    scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight, behavior: 'smooth' });
  }, [messages, isThinking]);

  const submit = async (text: string) => {
    const trimmed = text.trim();
    if (!trimmed || isThinking) return;
    setInput('');
    await sendMessage(trimmed);
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    submit(input);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter sends, Shift+Enter breaks the line — the convention people expect.
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      submit(input);
    }
  };

  const isEmpty = messages.length === 0 && !isLoadingThread;

  return (
    <div className="flex h-full min-h-0 gap-5">
      {/* Thread list — a column on desktop, an overlay on small screens. */}
      {showThreads && (
        <div
          onClick={() => setShowThreads(false)}
          className="fixed inset-0 bg-ink-black/30 z-40 lg:hidden animate-in fade-in duration-200"
          aria-hidden="true"
        />
      )}
      <aside
        className={`
          w-60 shrink-0 flex-col gap-3
          ${showThreads
            ? 'flex fixed left-0 top-16 bottom-0 z-50 bg-stone-canvas border-r border-stone-border p-3 animate-in slide-in-from-left duration-200'
            : 'hidden'}
          lg:flex lg:static lg:z-auto lg:bg-transparent lg:border-0 lg:p-0 lg:animate-none
        `}
      >
        <div className="flex items-center justify-between lg:hidden">
          <span className="text-xs font-semibold text-ink-black">Conversations</span>
          <button
            onClick={() => setShowThreads(false)}
            className="p-1 text-warm-gray hover:text-ink-black rounded-full transition"
            aria-label="Close conversations"
          >
            <X className="w-4 h-4" />
          </button>
        </div>

        <button
          onClick={() => {
            newConversation();
            setShowThreads(false);
          }}
          className="btn-ghost text-xs py-2 flex items-center justify-center gap-1.5 hover:border-cyan-edge transition shrink-0"
        >
          <Plus className="w-3.5 h-3.5" /> New chat
        </button>

        <div className="flex-1 overflow-y-auto space-y-0.5 min-h-0">
          <p className="hidden lg:block text-[10px] uppercase tracking-wider text-warm-gray font-medium px-2 py-1.5">
            Conversations
          </p>
          {conversations.length === 0 && (
            <p className="text-xs text-ash-gray px-2 py-1">No conversations yet.</p>
          )}
          {conversations.map((c) => (
            <div
              key={c.id}
              className={`group flex items-center gap-1.5 rounded-lg pr-1 transition ${
                c.id === conversationId
                  ? 'bg-white border border-stone-border shadow-subtle'
                  : 'hover:bg-white/70 border border-transparent'
              }`}
            >
              <button
                onClick={() => {
                  selectConversation(c.id);
                  setShowThreads(false);
                }}
                className="flex-1 flex items-center gap-2 px-2.5 py-2 text-left min-w-0"
              >
                <MessageSquare
                  className={`w-3.5 h-3.5 shrink-0 ${
                    c.id === conversationId ? 'text-cyan-signal' : 'text-ash-gray'
                  }`}
                />
                <span className="text-xs text-ink-black truncate">{c.title}</span>
              </button>
              <button
                onClick={() => deleteConversation(c.id)}
                title="Delete conversation"
                className="opacity-0 group-hover:opacity-100 p-1 text-ash-gray hover:text-rose-600 transition"
              >
                <Trash2 className="w-3.5 h-3.5" />
              </button>
            </div>
          ))}
        </div>
      </aside>

      {/* Thread */}
      <section className="flex-1 min-w-0 flex flex-col stone-card overflow-hidden">
        <header className="px-3 sm:px-5 py-3 border-b border-stone-border flex items-center gap-2.5 shrink-0">
          <button
            onClick={() => setShowThreads(true)}
            className="lg:hidden p-1.5 -ml-1 text-warm-gray hover:text-ink-black hover:bg-stone-canvas rounded-lg transition shrink-0"
            aria-label="Show conversations"
          >
            <PanelLeft className="w-4 h-4" />
          </button>
          <div className="shrink-0 flex items-center justify-center">
            <SentinelBot size={30} state="idle" />
          </div>
          <div className="min-w-0">
            <h1 className="text-sm font-medium text-ink-black tracking-tight truncate">
              Chat with {assistantName}
            </h1>
            <p className="text-[11px] text-warm-gray truncate hidden sm:block">
              Read-only. Answers come from your tasks, people, and meeting history.
            </p>
          </div>
          <button
            onClick={newConversation}
            className="ml-auto lg:hidden btn-ghost text-xs py-1.5 px-3 flex items-center gap-1 shrink-0"
          >
            <Plus className="w-3.5 h-3.5" /> New
          </button>
        </header>

        <div ref={scrollRef} className="flex-1 overflow-y-auto px-3 sm:px-5 py-6 min-h-0">
          {isLoadingThread && (
            <p className="text-xs text-warm-gray text-center py-8">Loading conversation…</p>
          )}

          {isEmpty && (
            <div className="max-w-xl mx-auto text-center space-y-6 py-12 animate-in fade-in duration-500">
              <div className="mx-auto flex items-center justify-center pb-1">
                <SentinelBot size={80} state="idle" showGlow={true} />
              </div>
              <div className="space-y-1.5">
                <h2 className="text-2xl font-normal text-ink-black tracking-tight">
                  Ask <span className="cyan-highlight">{assistantName}</span>
                </h2>
                <p className="text-xs text-warm-gray">
                  Your operational memory — commitments, blockers, and decisions.
                </p>
              </div>
              <div className="grid sm:grid-cols-2 gap-2 text-left">
                {SUGGESTIONS.map((s) => (
                  <button
                    key={s}
                    onClick={() => submit(s)}
                    className="px-3.5 py-2.5 border border-stone-border rounded-lg bg-white text-xs text-ink-black hover:border-cyan-edge hover:shadow-subtle transition text-left"
                  >
                    {s}
                  </button>
                ))}
              </div>
            </div>
          )}

          <div className="max-w-3xl mx-auto space-y-6">
            {messages.map((m) =>
              m.sender === 'user' ? (
                <div
                  key={m.id}
                  className="flex justify-end animate-in fade-in slide-in-from-bottom-1 duration-300"
                >
                  <div className="max-w-[88%] sm:max-w-[85%] bg-sky-wash/60 border border-stone-border rounded-2xl rounded-br-sm px-4 py-2.5">
                    <p className="text-sm text-ink-black whitespace-pre-wrap break-words leading-relaxed">
                      {m.content}
                    </p>
                  </div>
                </div>
              ) : (
                <div
                  key={m.id}
                  className="flex gap-3 animate-in fade-in slide-in-from-bottom-1 duration-300"
                >
                  <div className="shrink-0 mt-0.5 flex items-center justify-center">
                    <SentinelBot size={28} state="idle" />
                  </div>
                  <div className="min-w-0 flex-1 space-y-1">
                    <ToolExecutionPanel executions={m.tool_executions ?? []} />
                    {/* The model writes Markdown; render it rather than showing
                        the founder raw ** around every emphasised phrase. */}
                    <MarkdownText content={m.content} />
                  </div>
                </div>
              )
            )}

            {isThinking && (
              <div className="flex gap-3">
                <div className="shrink-0 flex items-center justify-center">
                  <SentinelBot size={28} state="thinking" />
                </div>
                <div className="flex items-center gap-1 pt-2" aria-label="Thinking">
                  {[0, 150, 300].map((delay) => (
                    <span
                      key={delay}
                      className="w-1.5 h-1.5 rounded-full bg-ash-gray animate-bounce"
                      style={{ animationDelay: `${delay}ms` }}
                    />
                  ))}
                </div>
              </div>
            )}

            {error && (
              <div className="flex items-start gap-2 p-3 bg-rose-50 border border-rose-200 rounded-lg text-xs text-rose-700">
                <AlertCircle className="w-4 h-4 shrink-0 mt-px" />
                <span>{error}</span>
              </div>
            )}
          </div>
        </div>

        <form onSubmit={handleSubmit} className="border-t border-stone-border p-3 shrink-0 bg-white">
          <div className="max-w-3xl mx-auto flex items-end gap-2 border border-stone-muted rounded-2xl px-3 py-2 bg-white focus-within:border-cyan-signal transition">
            <textarea
              rows={1}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={`Ask ${assistantName} about your business…`}
              className="flex-1 resize-none bg-transparent text-sm text-ink-black placeholder:text-ash-gray focus:outline-none max-h-40 py-1"
            />
            <button
              type="submit"
              disabled={!input.trim() || isThinking}
              className="w-8 h-8 rounded-full bg-cyan-signal text-white flex items-center justify-center shrink-0 disabled:opacity-40 disabled:cursor-not-allowed hover:bg-cyan-edge transition"
              aria-label="Send message"
            >
              <ArrowUp className="w-4 h-4" />
            </button>
          </div>
          <p className="max-w-3xl mx-auto text-[10px] text-ash-gray text-center pt-1.5">
            {assistantName} reads your data but never writes without approval.
          </p>
        </form>
      </section>
    </div>
  );
}
