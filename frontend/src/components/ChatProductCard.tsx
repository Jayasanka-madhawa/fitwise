"use client";

import Image from "next/image";
import Link from "next/link";
import type { Product } from "@/lib/types";
import { formatPrice, toNumber } from "@/lib/api";

interface ChatProductCardProps {
  product: Product;
  onAddToCart: (productId: string) => Promise<void>;
  adding: boolean;
}

export default function ChatProductCard({
  product,
  onAddToCart,
  adding,
}: ChatProductCardProps) {
  const rating = toNumber(product.average_rating);
  const reviewCount = toNumber(product.review_count);

  return (
    <div className="flex gap-3 rounded-lg border border-slate-200 bg-white p-2.5 shadow-sm">
      <Link
        href={`/product/${product.product_id}`}
        className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden bg-white"
      >
        {product.image_url ? (
          <Image
            src={product.image_url}
            alt={product.title}
            width={80}
            height={80}
            className="max-h-full max-w-full object-contain"
          />
        ) : (
          <span className="text-[10px] text-slate-400">No image</span>
        )}
      </Link>

      <div className="min-w-0 flex-1">
        <Link href={`/product/${product.product_id}`}>
          <p className="line-clamp-2 text-xs font-semibold leading-snug text-slate-900 hover:text-violet-600">
            {product.title}
          </p>
        </Link>

        <p className="mt-1 text-sm font-bold text-slate-900">
          {formatPrice(Number(product.price), product.currency || "LKR")}
        </p>

        <div className="mt-0.5 flex items-center gap-1 text-[11px] text-rose-500">
          <span>★ {rating.toFixed(1)}</span>
          <span className="text-slate-400">({reviewCount.toLocaleString()})</span>
        </div>

        <button
          type="button"
          disabled={adding}
          onClick={() => onAddToCart(product.product_id)}
          className="mt-2 w-full rounded-md bg-rose-500 py-1 text-[11px] font-semibold text-white hover:bg-rose-600 disabled:opacity-60"
        >
          {adding ? "Adding..." : "Add to Cart"}
        </button>
      </div>
    </div>
  );
}
