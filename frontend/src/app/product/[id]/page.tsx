"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import { useParams } from "next/navigation";
import Header from "@/components/Header";
import { useAuth } from "@/context/AuthContext";
import { addToCart, fetchProduct, formatPrice } from "@/lib/api";
import type { Product } from "@/lib/types";

export default function ProductPage() {
  const params = useParams<{ id: string }>();
  const productId = params.id;
  const { refreshCart, requireAuth } = useAuth();

  const [product, setProduct] = useState<Product | null>(null);
  const [loading, setLoading] = useState(true);
  const [adding, setAdding] = useState(false);
  const [toast, setToast] = useState<string | null>(null);

  useEffect(() => {
    if (!productId) return;
    setLoading(true);
    fetchProduct(productId)
      .then(setProduct)
      .catch(() => setProduct(null))
      .finally(() => setLoading(false));
  }, [productId]);

  const handleAdd = async () => {
    if (!product) return;
    if (!requireAuth(`/product/${product.product_id}`)) return;
    setAdding(true);
    try {
      await addToCart(product.product_id);
      await refreshCart();
      setToast("Added to cart");
      setTimeout(() => setToast(null), 2000);
    } finally {
      setAdding(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#eaeded]">
      <Header
        searchQuery=""
        onSearchChange={() => {}}
        onSearchSubmit={() => {}}
        chatOpen={false}
        onToggleChat={() => {}}
      />

      <div className="mx-auto max-w-5xl px-4 py-8">
        <Link href="/" className="text-sm font-medium text-violet-600 hover:text-violet-700">
          ← Back to shop
        </Link>

        {loading ? (
          <div className="mt-6 h-96 animate-pulse rounded-xl bg-slate-200" />
        ) : !product ? (
          <div className="mt-6 rounded-xl bg-white p-10 text-center text-slate-600">
            Product not found.
          </div>
        ) : (
          <div className="mt-6 grid gap-8 rounded-xl border border-slate-200 bg-white p-6 shadow-sm md:grid-cols-2">
            <div className="flex items-center justify-center bg-white p-6">
              {product.image_url ? (
                <Image
                  src={product.image_url}
                  alt={product.title}
                  width={400}
                  height={400}
                  className="max-h-[400px] bg-white object-contain"
                />
              ) : (
                <span className="text-slate-400">No image</span>
              )}
            </div>

            <div>
              <p className="text-sm font-medium uppercase text-violet-600">
                {product.department_final || product.department || "Fashion"}
              </p>
              <h1 className="mt-2 text-2xl font-bold text-slate-900">{product.title}</h1>
              {product.brand && (
                <p className="mt-1 text-sm text-slate-600">Brand: {product.brand}</p>
              )}

              <div className="mt-3 flex items-center gap-2 text-sm text-rose-500">
                <span>★ {(product.average_rating ?? 0).toFixed(1)}</span>
                <span className="text-slate-500">
                  ({(product.review_count ?? 0).toLocaleString()} reviews)
                </span>
              </div>

              <p className="mt-4 text-3xl font-bold text-slate-900">
                {formatPrice(Number(product.price), product.currency || "LKR")}
              </p>

              <button
                type="button"
                disabled={adding}
                onClick={handleAdd}
                className="mt-6 w-full rounded-md bg-rose-500 py-3 text-sm font-semibold text-white hover:bg-rose-600 disabled:opacity-60 md:w-auto md:px-10"
              >
                {adding ? "Adding..." : "Add to Cart"}
              </button>

              {product.description && (
                <div className="mt-8">
                  <h2 className="text-sm font-semibold uppercase text-slate-700">Description</h2>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">
                    {product.description}
                  </p>
                </div>
              )}

              {product.features && (
                <div className="mt-6">
                  <h2 className="text-sm font-semibold uppercase text-slate-700">Features</h2>
                  <p className="mt-2 text-sm leading-relaxed text-slate-600">{product.features}</p>
                </div>
              )}
            </div>
          </div>
        )}
      </div>

      {toast && (
        <div className="fixed bottom-6 left-1/2 z-50 -translate-x-1/2 rounded-full bg-slate-900 px-5 py-2.5 text-sm font-medium text-white shadow-lg">
          {toast}
        </div>
      )}
    </div>
  );
}
