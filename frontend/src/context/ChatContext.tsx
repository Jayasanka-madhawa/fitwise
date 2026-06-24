"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  addToCart,
  sendChatMessage,
  type ChatHistoryItem,
} from "@/lib/api";
import {
  chatSessionKey,
  loadStoredChat,
  saveStoredChat,
} from "@/lib/chat-storage";
import type { ChatMessage } from "@/lib/types";
import { useAuth } from "@/context/AuthContext";
import ChatPanel from "@/components/ChatPanel";

function toChatHistory(messages: ChatMessage[]): ChatHistoryItem[] {
  return messages.map((msg) => {
    let content = msg.content;
    if (msg.role === "assistant" && msg.products?.length) {
      const productList = msg.products
        .map((p, i) => `${i + 1}) ${p.title} (id: ${p.product_id})`)
        .join("; ");
      content = `${content}\n[Products shown: ${productList}]`;
    }
    return { role: msg.role, content };
  });
}

interface ChatContextValue {
  chatOpen: boolean;
  chatLoading: boolean;
  addingProductId: string | null;
  setChatOpen: (open: boolean) => void;
  toggleChat: () => void;
}

const ChatContext = createContext<ChatContextValue | null>(null);

export function ChatProvider({ children }: { children: React.ReactNode }) {
  const { user, loading: authLoading, refreshCart, requireAuth } = useAuth();
  const sessionKey = chatSessionKey(user?.id);

  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);
  const [addingProductId, setAddingProductId] = useState<string | null>(null);

  const prevSessionRef = useRef<string | null>(null);
  const hydratedRef = useRef(false);

  useEffect(() => {
    if (authLoading) return;

    const prev = prevSessionRef.current;
    if (prev !== null && prev !== sessionKey) {
      setChatMessages([]);
      setChatOpen(false);
      setChatInput("");
      hydratedRef.current = true;
    } else if (!hydratedRef.current || prev === null) {
      const stored = loadStoredChat(sessionKey);
      setChatMessages(stored?.messages ?? []);
      setChatOpen(stored?.open ?? false);
      hydratedRef.current = true;
    }

    prevSessionRef.current = sessionKey;
  }, [sessionKey, authLoading]);

  useEffect(() => {
    if (authLoading || !hydratedRef.current) return;
    saveStoredChat(sessionKey, { messages: chatMessages, open: chatOpen });
  }, [chatMessages, chatOpen, sessionKey, authLoading]);

  const toggleChat = useCallback(() => {
    setChatOpen((v) => !v);
  }, []);

  const handleAddToCart = useCallback(
    async (productId: string) => {
      if (!requireAuth("/")) return;
      setAddingProductId(productId);
      try {
        await addToCart(productId);
        await refreshCart();
      } finally {
        setAddingProductId(null);
      }
    },
    [requireAuth, refreshCart],
  );

  const handleSendChat = useCallback(async () => {
    const message = chatInput.trim();
    if (!message || chatLoading) return;

    const history = toChatHistory(chatMessages);

    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: message }]);
    setChatLoading(true);

    try {
      const result = await sendChatMessage(message, history);
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: result.reply,
          products: result.products?.length ? result.products : undefined,
        },
      ]);
      await refreshCart();
    } catch (err) {
      setChatMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: err instanceof Error ? err.message : "Sorry, something went wrong.",
        },
      ]);
    } finally {
      setChatLoading(false);
    }
  }, [chatInput, chatLoading, chatMessages, refreshCart]);

  const value = useMemo(
    () => ({
      chatOpen,
      chatLoading,
      addingProductId,
      setChatOpen,
      toggleChat,
    }),
    [chatOpen, chatLoading, addingProductId, toggleChat],
  );

  return (
    <ChatContext.Provider value={value}>
      {children}
      <ChatPanel
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        messages={chatMessages}
        input={chatInput}
        loading={chatLoading}
        onInputChange={setChatInput}
        onSend={handleSendChat}
        onAddToCart={handleAddToCart}
        addingProductId={addingProductId}
      />
    </ChatContext.Provider>
  );
}

export function useChat() {
  const ctx = useContext(ChatContext);
  if (!ctx) throw new Error("useChat must be used within ChatProvider");
  return ctx;
}
