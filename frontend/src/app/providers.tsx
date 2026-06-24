"use client";

import { AuthProvider } from "@/context/AuthContext";
import { ChatProvider } from "@/context/ChatContext";

export default function Providers({ children }: { children: React.ReactNode }) {
  return (
    <AuthProvider>
      <ChatProvider>{children}</ChatProvider>
    </AuthProvider>
  );
}
