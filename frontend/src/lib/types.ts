export interface Product {
  product_id: string;
  title: string;
  brand: string | null;
  department: string | null;
  department_final: string | null;
  price_usd: number | null;
  price: number;
  currency: string;
  average_rating: number | null;
  review_count: number | null;
  popularity_score: number | null;
  features: string | null;
  description: string | null;
  image_url: string | null;
  main_category: string | null;
}

export interface Department {
  department: string;
  count: number;
}

export interface CartItem {
  product_id: string;
  quantity: number;
  title: string;
  brand: string | null;
  price: number;
  currency: string;
  image_url: string | null;
  line_total: number;
}

export interface Cart {
  user_id: string;
  item_count: number;
  total_lkr: number;
  items: CartItem[];
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: string;
}

export interface ProductFilters {
  q: string;
  department_final: string;
  brand: string;
  min_price: string;
  max_price: string;
}
