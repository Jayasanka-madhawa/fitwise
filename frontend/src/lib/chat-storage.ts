import type { ChatMessage } from "./types";

export interface StoredChat {
  messages: ChatMessage[];
  open: boolean;
}

const PREFIX = "fitwise_chat_";

export function chatSessionKey(userId: string | null | undefined): string {
  return `${PREFIX}${userId ?? "guest"}`;
}

export function loadStoredChat(sessionKey: string): StoredChat | null {
  if (typeof window === "undefined") return null;
  const raw = sessionStorage.getItem(sessionKey);
  if (!raw) return null;
  try {
    return JSON.parse(raw) as StoredChat;
  } catch {
    return null;
  }
}

export function saveStoredChat(sessionKey: string, data: StoredChat): void {
  if (typeof window === "undefined") return;
  sessionStorage.setItem(sessionKey, JSON.stringify(data));
}

export function clearStoredChat(sessionKey: string): void {
  if (typeof window === "undefined") return;
  sessionStorage.removeItem(sessionKey);
}
