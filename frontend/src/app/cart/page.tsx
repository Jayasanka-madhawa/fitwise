"use client";

import Image from "next/image";
import Link from "next/link";
import { useEffect, useState } from "react";
import Header from "@/components/Header";
import { fetchCart, formatPrice, removeFromCart } from "@/lib/api";
import type { Cart } from "@/lib/types";
import { getUserId } from "@/lib/user";

export default function CartPage() {
  const userId = getUserId();
  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(true);
  const [removingId, setRemovingId] = useState<string | null>(null);

  const loadCart = async () => {
    setLoading(true);
    try {
      const data = await fetchCart(userId);
      setCart(data);
    } catch {
      setCart(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadCart();
  }, [userId]);

  const handleRemove = async (productId: string) => {
    setRemovingId(productId);
    try {
      await removeFromCart(userId, productId);
      await loadCart();
    } finally {
      setRemovingId(null);
    }
  };

  return (
    <div className="min-h-screen bg-[#eaeded]">
      <Header
        searchQuery=""
        onSearchChange={() => {}}
        onSearchSubmit={() => {}}
        cartCount={cart?.item_count ?? 0}
        chatOpen={false}
        onToggleChat={() => {}}
      />

      <div className="mx-auto max-w-4xl px-4 py-8">
        <div className="mb-6 flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">Shopping Cart</h1>
          <Link href="/" className="text-sm font-medium text-violet-600 hover:text-violet-700">
            Continue shopping
          </Link>
        </div>

        {loading ? (
          <div className="h-48 animate-pulse rounded-xl bg-slate-200" />
        ) : !cart || cart.items.length === 0 ? (
          <div className="rounded-xl border border-slate-200 bg-white p-10 text-center text-slate-600">
            Your cart is empty.
          </div>
        ) : (
          <div className="space-y-4">
            {cart.items.map((item) => (
              <div
                key={item.product_id}
                className="flex flex-col gap-4 rounded-xl border border-slate-200 bg-white p-4 shadow-sm sm:flex-row sm:items-center"
              >
                <div className="flex h-28 w-28 shrink-0 items-center justify-center overflow-hidden bg-white p-1">
                  {item.image_url ? (
                    <Image
                      src={item.image_url}
                      alt={item.title}
                      width={104}
                      height={104}
                      className="h-full w-full bg-white object-contain"
                    />
                  ) : (
                    <span className="text-xs text-slate-400">No image</span>
                  )}
                </div>

                <div className="min-w-0 flex-1">
                  <Link
                    href={`/product/${item.product_id}`}
                    className="line-clamp-2 font-semibold text-slate-900 hover:text-violet-600"
                  >
                    {item.title}
                  </Link>
                  {item.brand && (
                    <p className="mt-1 text-sm text-slate-500">{item.brand}</p>
                  )}
                  <p className="mt-2 text-sm text-slate-600">
                    Qty: {item.quantity} × {formatPrice(Number(item.price), item.currency)}
                  </p>
                </div>

                <div className="flex flex-col items-end gap-2">
                  <p className="font-bold text-slate-900">
                    {formatPrice(Number(item.line_total), item.currency)}
                  </p>
                  <button
                    type="button"
                    disabled={removingId === item.product_id}
                    onClick={() => handleRemove(item.product_id)}
                    className="text-sm font-medium text-red-600 hover:text-red-700 disabled:opacity-60"
                  >
                    {removingId === item.product_id ? "Removing..." : "Remove"}
                  </button>
                </div>
              </div>
            ))}

            <div className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
              <div className="flex items-center justify-between text-lg font-bold text-slate-900">
                <span>Subtotal ({cart.item_count} items)</span>
                <span>{formatPrice(cart.total_lkr)}</span>
              </div>
              <p className="mt-2 text-sm text-slate-500">
                Prices shown in LKR. Checkout is demo-only for this project.
              </p>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
