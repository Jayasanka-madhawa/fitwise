"use client";

import { useCallback, useEffect, useState } from "react";
import ChatPanel from "@/components/ChatPanel";
import FilterSidebar from "@/components/FilterSidebar";
import Header from "@/components/Header";
import ProductCard from "@/components/ProductCard";
import {
  addToCart,
  fetchCart,
  fetchDepartments,
  searchProducts,
  sendChatMessage,
} from "@/lib/api";
import type { ChatMessage, Department, Product, ProductFilters } from "@/lib/types";
import { getUserId } from "@/lib/user";

const PAGE_SIZE = 24;

const emptyFilters: ProductFilters = {
  q: "",
  department_final: "",
  brand: "",
  min_price: "",
  max_price: "",
};

export default function HomePage() {
  const [filters, setFilters] = useState<ProductFilters>(emptyFilters);
  const [appliedFilters, setAppliedFilters] = useState<ProductFilters>(emptyFilters);
  const [searchInput, setSearchInput] = useState("");
  const [departments, setDepartments] = useState<Department[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(true);
  const [loadingMore, setLoadingMore] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [cartCount, setCartCount] = useState(0);
  const [addingId, setAddingId] = useState<string | null>(null);
  const [toast, setToast] = useState<string | null>(null);

  const [chatOpen, setChatOpen] = useState(false);
  const [chatInput, setChatInput] = useState("");
  const [chatLoading, setChatLoading] = useState(false);
  const [chatMessages, setChatMessages] = useState<ChatMessage[]>([]);

  const userId = getUserId();

  const refreshCart = useCallback(async () => {
    try {
      const cart = await fetchCart(userId);
      setCartCount(cart.item_count);
    } catch {
      setCartCount(0);
    }
  }, [userId]);

  const loadProducts = useCallback(
    async (nextFilters: ProductFilters, nextOffset: number, append: boolean) => {
      if (append) setLoadingMore(true);
      else setLoading(true);
      setError(null);

      try {
        const results = await searchProducts(nextFilters, PAGE_SIZE, nextOffset);
        setProducts((prev) => (append ? [...prev, ...results] : results));
        setHasMore(results.length === PAGE_SIZE);
        setOffset(nextOffset);
      } catch (err) {
        setError(err instanceof Error ? err.message : "Failed to load products");
        if (!append) setProducts([]);
      } finally {
        setLoading(false);
        setLoadingMore(false);
      }
    },
    [],
  );

  useEffect(() => {
    fetchDepartments()
      .then(setDepartments)
      .catch(() => setDepartments([]));
    refreshCart();
  }, [refreshCart]);

  useEffect(() => {
    loadProducts(appliedFilters, 0, false);
  }, [appliedFilters, loadProducts]);

  const applySearch = () => {
    const next = { ...appliedFilters, q: searchInput.trim() };
    setAppliedFilters(next);
    setFilters(next);
  };

  const applyFilters = () => {
    const next = { ...filters, q: searchInput.trim() };
    setAppliedFilters(next);
    setFilters(next);
  };

  const clearFilters = () => {
    setSearchInput("");
    setFilters(emptyFilters);
    setAppliedFilters(emptyFilters);
  };

  const handleAddToCart = async (productId: string) => {
    setAddingId(productId);
    try {
      await addToCart(userId, productId);
      await refreshCart();
      setToast("Added to cart");
      setTimeout(() => setToast(null), 2000);
    } catch (err) {
      setToast(err instanceof Error ? err.message : "Could not add to cart");
      setTimeout(() => setToast(null), 3000);
    } finally {
      setAddingId(null);
    }
  };

  const handleSendChat = async () => {
    const message = chatInput.trim();
    if (!message || chatLoading) return;

    setChatInput("");
    setChatMessages((prev) => [...prev, { role: "user", content: message }]);
    setChatLoading(true);

    try {
      const result = await sendChatMessage(userId, message);
      setChatMessages((prev) => [...prev, { role: "assistant", content: result.reply }]);
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
  };

  return (
    <div className="min-h-screen bg-[#eaeded]">
      <Header
        searchQuery={searchInput}
        onSearchChange={setSearchInput}
        onSearchSubmit={applySearch}
        cartCount={cartCount}
        chatOpen={chatOpen}
        onToggleChat={() => setChatOpen((v) => !v)}
      />

      <div className={`mx-auto max-w-[1600px] px-4 py-6 ${chatOpen ? "md:pl-[396px]" : ""}`}>
        <div className="flex flex-col gap-6 lg:flex-row">
          <FilterSidebar
            filters={filters}
            departments={departments}
            onChange={setFilters}
            onApply={applyFilters}
            onClear={clearFilters}
          />

          <main className="min-w-0 flex-1">
            <div className="mb-4 flex flex-wrap items-center justify-between gap-2">
              <div>
                <h1 className="text-lg font-semibold text-slate-900">Shop Fashion</h1>
                <p className="text-sm text-slate-600">
                  {loading ? "Loading..." : `${products.length} products shown`}
                  {appliedFilters.q && ` for "${appliedFilters.q}"`}
                </p>
              </div>
              <button
                type="button"
                onClick={() => setChatOpen(true)}
                className="rounded-md bg-violet-600 px-4 py-2 text-sm font-semibold text-white hover:bg-violet-700 md:hidden"
              >
                Open AI Chat
              </button>
            </div>

            {error && (
              <div className="mb-4 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
                {error}. Make sure the backend is running at{" "}
                {process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000"}.
              </div>
            )}

            {loading ? (
              <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                {Array.from({ length: 8 }).map((_, i) => (
                  <div key={i} className="h-96 animate-pulse rounded-xl bg-slate-200" />
                ))}
              </div>
            ) : products.length === 0 ? (
              <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-slate-600">
                No products found. Try different search terms or filters.
              </div>
            ) : (
              <>
                <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4">
                  {products.map((product) => (
                    <ProductCard
                      key={product.product_id}
                      product={product}
                      onAddToCart={handleAddToCart}
                      adding={addingId === product.product_id}
                    />
                  ))}
                </div>

                {hasMore && (
                  <div className="mt-8 flex justify-center">
                    <button
                      type="button"
                      disabled={loadingMore}
                      onClick={() => loadProducts(appliedFilters, offset + PAGE_SIZE, true)}
                      className="rounded-md border border-slate-300 bg-white px-8 py-2.5 text-sm font-semibold text-slate-800 hover:bg-slate-50 disabled:opacity-60"
                    >
                      {loadingMore ? "Loading..." : "Load more products"}
                    </button>
                  </div>
                )}
              </>
            )}
          </main>
        </div>
      </div>

      <ChatPanel
        open={chatOpen}
        onClose={() => setChatOpen(false)}
        messages={chatMessages}
        input={chatInput}
        loading={chatLoading}
        onInputChange={setChatInput}
        onSend={handleSendChat}
      />

      {toast && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full bg-slate-900 px-5 py-2.5 text-sm font-medium text-white shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
