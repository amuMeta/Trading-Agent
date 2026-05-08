"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import { useRouter } from "next/navigation";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  timestamp: number;
}

interface Source {
  content: string;
  score: number;
  metadata: {
    title?: string;
    session_id?: string;
    user_query?: string;
  };
}

interface Conversation {
  id: string;
  title: string;
  preview: string;
  messages: Message[];
  createdAt: number;
  updatedAt: number;
}

const STORAGE_KEY = "chat_conversations";

function generateId() {
  return `conv_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

function loadConversations(): Conversation[] {
  if (typeof window === "undefined") return [];
  try {
    const data = localStorage.getItem(STORAGE_KEY);
    return data ? JSON.parse(data) : [];
  } catch {
    return [];
  }
}

export default function ChatPage() {
  const router = useRouter();
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [currentConversationId, setCurrentConversationId] = useState<string | null>(null);
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [showHistory, setShowHistory] = useState(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Refs for performance optimization
  const saveTimerRef = useRef<NodeJS.Timeout | null>(null);
  const sseAccumRef = useRef<{ content: string; sources: Source[] }>({ content: "", sources: [] });
  const updateTimerRef = useRef<NodeJS.Timeout | null>(null);
  const messagesRef = useRef<Message[]>([]);
  const conversationsRef = useRef<Conversation[]>([]);

  // Keep refs in sync with state
  useEffect(() => {
    messagesRef.current = messages;
  }, [messages]);

  useEffect(() => {
    conversationsRef.current = conversations;
  }, [conversations]);

  // Debounced save to localStorage (500ms delay)
  const debouncedSave = useCallback(() => {
    if (saveTimerRef.current) {
      clearTimeout(saveTimerRef.current);
    }
    saveTimerRef.current = setTimeout(() => {
      const currentMessages = messagesRef.current;
      const currentConvs = conversationsRef.current;
      const currentConvId = conversationsRef.current.find(c => c.id === currentConversationId)?.id;

      if (currentConvId && currentMessages.length > 0) {
        const updated = currentConvs.map((conv) =>
          conv.id === currentConvId
            ? {
                ...conv,
                messages: currentMessages,
                preview: currentMessages[currentMessages.length - 1]?.content?.slice(0, 50) || "",
                updatedAt: Date.now(),
              }
            : conv
        );
        try {
          localStorage.setItem(STORAGE_KEY, JSON.stringify(updated));
        } catch (e) {
          console.error("保存对话失败:", e);
        }
      }
    }, 500);
  }, [currentConversationId]);

  // Load history on mount
  useEffect(() => {
    const loaded = loadConversations();
    setConversations(loaded);
    if (loaded.length > 0) {
      setCurrentConversationId(loaded[0].id);
      setMessages(loaded[0].messages);
    }

    // RAG Engine preheat - warm up on page load
    fetch("/api/chat/rag/stream", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: "hello",
        history: [],
        top_k: 1,
        collection: "finance_knowledge"
      }),
    }).catch(() => {}); // Ignore errors, just warm up

  }, []);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  // Start new conversation
  const startNewConversation = async () => {
    // Save current conversation (triggers debounced save)
    if (currentConversationId && messages.length > 0) {
      debouncedSave();
    }

    const newConvId = generateId();

    // Create conversation on server (fire and forget)
    fetch("/api/chat/conversations", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        user_id: "default_user",
        title: `新对话 ${conversations.length + 1}`
      }),
    }).catch(() => {});

    // Create new conversation
    const newConversation: Conversation = {
      id: newConvId,
      title: `新对话 ${conversations.length + 1}`,
      preview: "",
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    const newConversations = [newConversation, ...conversations];
    setConversations(newConversations);
    setCurrentConversationId(newConversation.id);
    setMessages([]);
    setShowHistory(false);
  };

  // Load conversation
  const loadConversation = (convId: string) => {
    // Save current conversation (triggers debounced save)
    if (currentConversationId && messages.length > 0) {
      debouncedSave();
    }

    // Load selected conversation
    const conv = conversations.find((c) => c.id === convId);
    if (conv) {
      setCurrentConversationId(conv.id);
      setMessages(conv.messages);
      setShowHistory(false);
    }
  };

  // Delete conversation
  const deleteConversation = async (convId: string, e: React.MouseEvent) => {
    e.stopPropagation();

    // Delete from server (fire and forget)
    fetch(`/api/chat/conversations/${convId}?user_id=default_user`, {
      method: "DELETE"
    }).catch(() => {});

    const updated = conversations.filter((c) => c.id !== convId);
    setConversations(updated);

    if (currentConversationId === convId) {
      if (updated.length > 0) {
        setCurrentConversationId(updated[0].id);
        setMessages(updated[0].messages);
      } else {
        startNewConversation();
      }
    }
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: "user",
      content: input,
      timestamp: Date.now(),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsLoading(true);

    // Trigger debounced save
    debouncedSave();

    try {
      const history = messages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));

      const response = await fetch("/api/chat/rag/stream", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          message: input,
          history: history,
          top_k: 5,
          collection: "finance_knowledge",
        }),
      });

      if (!response.ok) throw new Error("请求失败");

      const reader = response.body?.getReader();
      const decoder = new TextDecoder();
      let assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: "assistant",
        content: "",
        sources: [],
        timestamp: Date.now(),
      };

      setMessages((prev) => [...prev, assistantMessage]);

      if (reader) {
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value);
          const lines = chunk.split("\n");

          for (const line of lines) {
            if (line.startsWith("data: ")) {
              try {
                const data = JSON.parse(line.slice(6));

                if (data.type === "content") {
                  assistantMessage.content += data.content;
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = { ...assistantMessage };
                    return newMessages;
                  });
                } else if (data.type === "sources") {
                  assistantMessage.sources = data.sources;
                  setMessages((prev) => {
                    const newMessages = [...prev];
                    newMessages[newMessages.length - 1] = { ...assistantMessage };
                    return newMessages;
                  });
                }
              } catch (e) {
                // 解析错误，忽略
              }
            }
          }
        }
      }

      // Trigger debounced save after conversation ends
      debouncedSave();

      // Save to server (fire and forget, don't wait)
      if (currentConversationId) {
        fetch(`/api/chat/conversations/${currentConversationId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: userMessage.role,
            content: userMessage.content,
            sources: [],
            user_id: "default_user"
          }),
        }).catch(() => {});

        fetch(`/api/chat/conversations/${currentConversationId}/messages`, {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            role: assistantMessage.role,
            content: assistantMessage.content,
            sources: assistantMessage.sources || [],
            user_id: "default_user"
          }),
        }).catch(() => {});
      }
    } catch (error) {
      console.error("对话错误:", error);
      setMessages((prev) => [
        ...prev,
        {
          id: (Date.now() + 1).toString(),
          role: "assistant",
          content: "抱歉，对话服务暂不可用，请稍后重试。",
          timestamp: Date.now(),
        },
      ]);
    } finally {
      setIsLoading(false);
      debouncedSave();
    }
  };

  const formatTime = (timestamp: number) => {
    const date = new Date(timestamp);
    const now = new Date();
    const isToday = date.toDateString() === now.toDateString();

    if (isToday) {
      return date.toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
    }
    return date.toLocaleDateString("zh-CN", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  return (
    <div className="flex h-[calc(100vh-64px)] bg-white">
      {/* 历史对话侧边栏 */}
      <div
        className={`border-r border-gray-200 bg-gray-50 transition-all duration-300 ${
          showHistory ? "w-72" : "w-0 overflow-hidden"
        }`}
      >
        <div className="p-4">
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-lg font-semibold text-gray-800">历史对话</h2>
            <button
              onClick={startNewConversation}
              className="flex items-center gap-2 px-3 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm"
            >
              + 新对话
            </button>
          </div>

          <div className="space-y-2">
            {conversations.map((conv) => (
              <div
                key={conv.id}
                onClick={() => loadConversation(conv.id)}
                className={`p-3 rounded-lg cursor-pointer transition-colors group ${
                  currentConversationId === conv.id
                    ? "bg-blue-100 border border-blue-300"
                    : "bg-white hover:bg-gray-100 border border-transparent"
                }`}
              >
                <div className="flex items-start justify-between">
                  <div className="flex-1 min-w-0">
                    <div className="font-medium text-gray-900 truncate">{conv.title}</div>
                    {conv.preview && (
                      <div className="text-xs text-gray-500 truncate mt-1">{conv.preview}</div>
                    )}
                    <div className="text-xs text-gray-400 mt-1">
                      {formatTime(conv.updatedAt)}
                    </div>
                  </div>
                  <button
                    onClick={(e) => deleteConversation(conv.id, e)}
                    className="opacity-0 group-hover:opacity-100 p-1 text-gray-400 hover:text-red-500 transition-opacity"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path
                        strokeLinecap="round"
                        strokeLinejoin="round"
                        strokeWidth={2}
                        d="M6 18L18 6M6 6l12 12"
                      />
                    </svg>
                  </button>
                </div>
              </div>
            ))}

            {conversations.length === 0 && (
              <div className="text-center text-gray-400 py-8">
                <div className="text-4xl mb-2">💬</div>
                <div className="text-sm">暂无历史对话</div>
                <button
                  onClick={startNewConversation}
                  className="mt-3 px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 transition-colors text-sm"
                >
                  开始新对话
                </button>
              </div>
            )}
          </div>
        </div>
      </div>

      {/* 主对话区域 */}
      <div className="flex-1 flex flex-col">
        {/* 标题栏 */}
        <div className="border-b border-gray-200 px-6 py-4 flex items-center justify-between">
          <div className="flex items-center gap-3">
            <button
              onClick={() => setShowHistory(!showHistory)}
              className="p-2 hover:bg-gray-100 rounded-lg transition-colors"
              title="显示/隐藏历史"
            >
              <svg className="w-5 h-5 text-gray-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h7" />
              </svg>
            </button>
            <div>
              <h1 className="text-xl font-semibold text-gray-800">💬 金融智能对话</h1>
              <p className="text-sm text-gray-500">基于RAG的股票分析问答助手</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <button
              onClick={() => window.location.href = "/"}
              className="flex items-center gap-2 px-4 py-2 bg-gray-100 hover:bg-gray-200 text-gray-700 rounded-lg transition-colors"
            >
              ← 返回主界面
            </button>
          </div>
        </div>

        {/* 消息列表 */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {messages.length === 0 && (
            <div className="flex items-center justify-center h-full">
              <div className="text-center text-gray-400">
                <div className="text-5xl mb-4">💬</div>
                <div className="text-lg font-medium mb-2">金融智能对话</div>
                <div className="text-sm mb-1">输入问题开始对话</div>
                <div className="text-sm">基于您之前的分析报告和金融知识</div>
              </div>
            </div>
          )}

          {messages.map((message) => (
            <div
              key={message.id}
              className={`flex ${message.role === "user" ? "justify-end" : "justify-start"}`}
            >
              <div
                className={`max-w-[80%] rounded-2xl p-4 ${
                  message.role === "user"
                    ? "bg-blue-500 text-white"
                    : "bg-gray-100 text-gray-900"
                }`}
              >
                <div className="whitespace-pre-wrap">{message.content}</div>

                {/* 来源引用 */}
                {message.sources && message.sources.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-gray-200">
                    <div className="text-xs font-medium mb-2 text-gray-500">📚 参考来源：</div>
                    <div className="space-y-2">
                      {message.sources.map((source, index) => (
                        <div
                          key={index}
                          className={`text-xs p-2 rounded ${
                            message.role === "user" ? "bg-blue-600" : "bg-white"
                          }`}
                        >
                          <div className="font-medium">
                            {source.metadata?.session_id
                              ? `会话: ${source.metadata.session_id}`
                              : `来源 ${index + 1}`}
                          </div>
                          <div className="truncate mt-1 opacity-80">{source.content}</div>
                          <div className="mt-1 opacity-60">
                            相似度: {(source.score * 100).toFixed(1)}%
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}

                <div className={`text-xs mt-2 ${message.role === "user" ? "text-blue-100" : "text-gray-400"}`}>
                  {formatTime(message.timestamp)}
                </div>
              </div>
            </div>
          ))}

          {isLoading && (
            <div className="flex justify-start">
              <div className="bg-gray-100 rounded-2xl p-4">
                <div className="flex space-x-2">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.1s" }}
                  />
                  <div
                    className="w-2 h-2 bg-gray-400 rounded-full animate-bounce"
                    style={{ animationDelay: "0.2s" }}
                  />
                </div>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>

        {/* 输入框 */}
        <div className="border-t border-gray-200 p-4">
          <div className="flex gap-3 max-w-4xl mx-auto">
            <input
              type="text"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === "Enter" && !e.shiftKey && handleSend()}
              placeholder="输入您的问题，例如：招商银行601939的基本面分析如何？"
              className="flex-1 border border-gray-300 rounded-xl px-4 py-3 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"
              disabled={isLoading}
            />
            <button
              onClick={handleSend}
              disabled={isLoading || !input.trim()}
              className="bg-blue-500 text-white px-6 py-3 rounded-xl hover:bg-blue-600 disabled:opacity-50 disabled:cursor-not-allowed font-medium transition-colors"
            >
              发送
            </button>
          </div>
          <div className="text-center mt-2 text-xs text-gray-400">
            按Enter发送，Shift+Enter换行
          </div>
        </div>
      </div>
    </div>
  );
}