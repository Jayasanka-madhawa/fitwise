import type { AuthResponse } from "./auth-storage";
import { authHeaders } from "./auth-storage";
import { getStoredToken } from "./auth-storage";
import type { Cart, Department, Product, ProductFilters } from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

function buildQuery(params: Record<string, string | number | undefined>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== "") {
      search.set(key, String(value));
    }
  }
  const qs = search.toString();
  return qs ? `?${qs}` : "";
}

async function request<T>(path: string, init?: RequestInit, auth = false): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(auth ? authHeaders() : {}),
      ...init?.headers,
    },
  });
  if (!res.ok) {
    let detail = await res.text();
    try {
      const parsed = JSON.parse(detail);
      detail = parsed.detail || detail;
    } catch {
      /* keep raw text */
    }
    throw new Error(typeof detail === "string" ? detail : "Request failed");
  }
  return res.json() as Promise<T>;
}

export async function registerUser(
  email: string,
  password: string,
  name?: string,
): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/register", {
    method: "POST",
    body: JSON.stringify({ email, password, name }),
  });
}

export async function loginUser(email: string, password: string): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/login", {
    method: "POST",
    body: JSON.stringify({ email, password }),
  });
}

export async function loginWithGoogle(idToken: string): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/google", {
    method: "POST",
    body: JSON.stringify({ id_token: idToken }),
  });
}

export async function loginWithGithub(code: string, redirectUri: string): Promise<AuthResponse> {
  return request<AuthResponse>("/auth/github", {
    method: "POST",
    body: JSON.stringify({ code, redirect_uri: redirectUri }),
  });
}

export async function fetchAuthConfig(): Promise<{
  google_client_id: string;
  github_client_id: string;
}> {
  return request<{ google_client_id: string; github_client_id: string }>("/auth/config");
}

export async function fetchMe(): Promise<AuthResponse["user"]> {
  return request<AuthResponse["user"]>("/auth/me", {}, true);
}

export async function fetchDepartments(): Promise<Department[]> {
  return request<Department[]>("/products/departments");
}

export async function searchProducts(
  filters: ProductFilters,
  limit = 24,
  offset = 0,
): Promise<Product[]> {
  const query = buildQuery({
    q: filters.q || undefined,
    department_final: filters.department_final || undefined,
    brand: filters.brand || undefined,
    min_price: filters.min_price || undefined,
    max_price: filters.max_price || undefined,
    limit,
    offset,
  });
  return request<Product[]>(`/products/search${query}`);
}

export async function fetchProduct(productId: string): Promise<Product> {
  return request<Product>(`/products/${productId}`);
}

export async function addToCart(productId: string, quantity = 1): Promise<unknown> {
  return request(
    "/cart/add",
    {
      method: "POST",
      body: JSON.stringify({ product_id: productId, quantity }),
    },
    true,
  );
}

export async function removeFromCart(productId: string): Promise<unknown> {
  return request(
    "/cart/remove",
    {
      method: "DELETE",
      body: JSON.stringify({ product_id: productId }),
    },
    true,
  );
}

export async function fetchCart(): Promise<Cart> {
  return request<Cart>("/cart/me", {}, true);
}

export interface ChatHistoryItem {
  role: "user" | "assistant";
  content: string;
}

export async function sendChatMessage(
  message: string,
  history: ChatHistoryItem[] = [],
): Promise<{ reply: string; tools_used: string[]; products: Product[] }> {
  return request(
    "/chat",
    {
      method: "POST",
      body: JSON.stringify({ message, history }),
    },
    Boolean(getStoredToken()),
  );
}

export function toNumber(value: unknown, fallback = 0): number {
  const n = Number(value);
  return Number.isFinite(n) ? n : fallback;
}

export function formatPrice(price: number, currency = "LKR"): string {
  return new Intl.NumberFormat("en-LK", {
    style: "currency",
    currency,
    maximumFractionDigits: 0,
  }).format(price);
}

export function truncate(text: string | null | undefined, max = 120): string {
  if (!text) return "";
  return text.length <= max ? text : `${text.slice(0, max).trim()}…`;
}
