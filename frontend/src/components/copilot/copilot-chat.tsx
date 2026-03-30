"use client";

import { useState, useRef, useEffect } from "react";
import { portalApi } from "@/lib/api/portal";
import { CopilotMessage, SuggestedAction } from "@/lib/types/portal";
import Link from "next/link";

function actionLink(action: SuggestedAction): string {
  switch (action.type) {
    case "lesson": return `/learn/lesson/${action.slug}`;
    case "exercise": return `/practice/python/${action.slug}`;
    case "article": return `/knowledge/${action.slug}`;
    default: return "#";
  }
}

function actionIcon(type: string): string {
  switch (type) {
    case "lesson": return "📖";
    case "exercise": return "🔧";
    case "article": return "📄";
    default: return "→";
  }
}

export function CopilotChat() {
  const [messages, setMessages] = useState<CopilotMessage[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const handleSubmit = async () => {
    const trimmed = input.trim();
    if (!trimmed || isLoading) return;

    const userMsg: CopilotMessage = { role: "user", content: trimmed };
    const newMessages = [...messages, userMsg];
    setMessages(newMessages);
    setInput("");
    setError(null);
    setIsLoading(true);

    try {
      const apiMessages = newMessages.map((m) => ({ role: m.role, content: m.content }));
      const result = await portalApi.sendCopilotMessage(apiMessages);
      const assistantMsg: CopilotMessage = {
        role: "assistant",
        content: result.response,
        suggestedActions: result.suggested_actions,
      };
      setMessages([...newMessages, assistantMsg]);
    } catch (err: any) {
      setError(err.message || "Something went wrong");
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit();
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-12rem)]">
      {/* Messages */}
      <div className="flex-1 overflow-y-auto space-y-4 pb-4">
        {messages.length === 0 && (
          <div className="text-center py-16">
            <p className="text-2xl font-semibold text-[#14213d] mb-2">AI Study Copilot</p>
            <p className="text-[#14213d]/60 max-w-md mx-auto">
              Ask me anything about AI engineering. I have access to your learning progress,
              lessons, exercises, and knowledge articles.
            </p>
          </div>
        )}

        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[80%] rounded-2xl px-4 py-3 ${
                msg.role === "user"
                  ? "bg-[#14213d] text-[#f8f3e8]"
                  : "bg-[#f8f3e8] text-[#14213d] border border-[#e7d8c9]"
              }`}
            >
              <div className="whitespace-pre-wrap text-sm leading-relaxed">
                {msg.content}
              </div>

              {msg.suggestedActions && msg.suggestedActions.length > 0 && (
                <div className="mt-3 pt-3 border-t border-[#e7d8c9] space-y-2">
                  <p className="text-xs font-semibold uppercase tracking-wide text-[#14213d]/50">
                    Suggested next steps
                  </p>
                  {msg.suggestedActions.map((action, j) => (
                    <Link
                      key={j}
                      href={actionLink(action)}
                      className="flex items-center gap-2 text-sm text-[#f77f00] hover:text-[#14213d] transition-colors"
                    >
                      <span>{actionIcon(action.type)}</span>
                      <span className="underline underline-offset-2">{action.title}</span>
                    </Link>
                  ))}
                </div>
              )}
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-[#f8f3e8] text-[#14213d] border border-[#e7d8c9] rounded-2xl px-4 py-3">
              <div className="flex items-center gap-1">
                <div className="w-2 h-2 bg-[#f77f00] rounded-full animate-bounce" style={{ animationDelay: "0ms" }}></div>
                <div className="w-2 h-2 bg-[#f77f00] rounded-full animate-bounce" style={{ animationDelay: "150ms" }}></div>
                <div className="w-2 h-2 bg-[#f77f00] rounded-full animate-bounce" style={{ animationDelay: "300ms" }}></div>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="flex justify-center">
            <div className="bg-red-50 text-red-700 border border-red-200 rounded-lg px-4 py-2 text-sm">
              {error}
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input */}
      <div className="border-t border-[#e7d8c9] pt-4">
        <div className="flex gap-3">
          <textarea
            ref={textareaRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Ask about AI engineering..."
            rows={2}
            className="flex-1 resize-none rounded-xl border border-[#e7d8c9] bg-white px-4 py-3 text-sm text-[#14213d] placeholder:text-[#14213d]/40 focus:outline-none focus:ring-2 focus:ring-[#f77f00]/30 focus:border-[#f77f00]"
            disabled={isLoading}
          />
          <button
            onClick={handleSubmit}
            disabled={isLoading || !input.trim()}
            className="self-end rounded-xl bg-[#f77f00] px-6 py-3 text-sm font-medium text-white hover:bg-[#e06f00] disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  );
}
