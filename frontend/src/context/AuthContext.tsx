"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";
import { useRouter } from "next/navigation";
import {
  fetchCart,
  fetchMe,
  loginUser,
  loginWithGoogle,
  loginWithGithub,
  registerUser,
} from "@/lib/api";
import type { AuthUser } from "@/lib/auth-storage";
import {
  clearAuth,
  getStoredToken,
  getStoredUser,
  saveAuth,
} from "@/lib/auth-storage";

interface AuthContextValue {
  user: AuthUser | null;
  loading: boolean;
  cartCount: number;
  login: (email: string, password: string) => Promise<void>;
  register: (email: string, password: string, name?: string) => Promise<void>;
  googleLogin: (idToken: string) => Promise<void>;
  githubLogin: (code: string, redirectUri: string) => Promise<void>;
  logout: () => void;
  refreshCart: () => Promise<void>;
  requireAuth: (nextPath?: string) => boolean;
}

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const router = useRouter();
  const [user, setUser] = useState<AuthUser | null>(null);
  const [loading, setLoading] = useState(true);
  const [cartCount, setCartCount] = useState(0);

  const refreshCart = useCallback(async () => {
    if (!getStoredToken()) {
      setCartCount(0);
      return;
    }
    try {
      const cart = await fetchCart();
      setCartCount(cart.item_count);
    } catch {
      setCartCount(0);
    }
  }, []);

  useEffect(() => {
    const bootstrap = async () => {
      const token = getStoredToken();
      const stored = getStoredUser();
      if (!token) {
        setLoading(false);
        return;
      }
      if (stored) setUser(stored);
      try {
        const me = await fetchMe();
        setUser(me);
        await refreshCart();
      } catch {
        clearAuth();
        setUser(null);
        setCartCount(0);
      } finally {
        setLoading(false);
      }
    };
    bootstrap();
  }, [refreshCart]);

  const handleAuthSuccess = useCallback(
    async (response: Awaited<ReturnType<typeof loginUser>>) => {
      saveAuth(response);
      setUser(response.user);
      await refreshCart();
    },
    [refreshCart],
  );

  const login = useCallback(
    async (email: string, password: string) => {
      const response = await loginUser(email, password);
      await handleAuthSuccess(response);
    },
    [handleAuthSuccess],
  );

  const register = useCallback(
    async (email: string, password: string, name?: string) => {
      const response = await registerUser(email, password, name);
      await handleAuthSuccess(response);
    },
    [handleAuthSuccess],
  );

  const googleLogin = useCallback(
    async (idToken: string) => {
      const response = await loginWithGoogle(idToken);
      await handleAuthSuccess(response);
    },
    [handleAuthSuccess],
  );

  const githubLogin = useCallback(
    async (code: string, redirectUri: string) => {
      const response = await loginWithGithub(code, redirectUri);
      await handleAuthSuccess(response);
    },
    [handleAuthSuccess],
  );

  const logout = useCallback(() => {
    clearAuth();
    setUser(null);
    setCartCount(0);
    router.push("/");
  }, [router]);

  const requireAuth = useCallback(
    (nextPath = "/") => {
      if (user) return true;
      router.push(`/login?next=${encodeURIComponent(nextPath)}`);
      return false;
    },
    [router, user],
  );

  const value = useMemo(
    () => ({
      user,
      loading,
      cartCount,
      login,
      register,
      googleLogin,
      githubLogin,
      logout,
      refreshCart,
      requireAuth,
    }),
    [user, loading, cartCount, login, register, googleLogin, githubLogin, logout, refreshCart, requireAuth],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
