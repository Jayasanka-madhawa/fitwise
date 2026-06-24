import type { Cart, ChatMessage, Department, Product, ProductFilters } from "./types";

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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers,
    },
  });
  if (!res.ok) {
    const detail = await res.text();
    throw new Error(detail || `Request failed: ${res.status}`);
  }
  return res.json() as Promise<T>;
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

export async function addToCart(
  userId: string,
  productId: string,
  quantity = 1,
): Promise<unknown> {
  return request("/cart/add", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, product_id: productId, quantity }),
  });
}

export async function removeFromCart(
  userId: string,
  productId: string,
): Promise<unknown> {
  return request("/cart/remove", {
    method: "DELETE",
    body: JSON.stringify({ user_id: userId, product_id: productId }),
  });
}

export async function fetchCart(userId: string): Promise<Cart> {
  return request<Cart>(`/cart/${userId}`);
}

export async function sendChatMessage(
  userId: string,
  message: string,
): Promise<{ reply: string; tools_used: string[] }> {
  return request("/chat", {
    method: "POST",
    body: JSON.stringify({ user_id: userId, message }),
  });
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

export type { ChatMessage };
