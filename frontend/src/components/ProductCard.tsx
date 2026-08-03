"use client";

import Image from "next/image";
import Link from "next/link";
import type { Product } from "@/lib/types";
import { formatPrice, toNumber, truncate } from "@/lib/api";

interface ProductCardProps {
  product: Product;
  onAddToCart: (productId: string) => Promise<void>;
  adding: boolean;
}

export default function ProductCard({ product, onAddToCart, adding }: ProductCardProps) {
  const description = truncate(product.description || product.features, 100);
  const rating = toNumber(product.average_rating);
  const reviewCount = toNumber(product.review_count);

  return (
    <article className="flex h-full flex-col overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm transition hover:shadow-md">
      <Link href={`/product/${product.product_id}`} className="block">
        <div className="relative flex h-52 items-center justify-center bg-white p-4">
          {product.image_url ? (
            <Image
              src={product.image_url}
              alt={product.title}
              width={200}
              height={200}
              className="max-h-full max-w-full object-contain"
            />
          ) : (
            <div className="text-sm text-slate-400">No image</div>
          )}
        </div>
      </Link>

      <div className="flex flex-1 flex-col p-4">
        <p className="text-xs font-medium uppercase tracking-wide text-violet-600">
          {product.department_final || product.department || "Fashion"}
        </p>

        <Link href={`/product/${product.product_id}`}>
          <h3 className="mt-1 line-clamp-2 text-sm font-semibold text-slate-900 hover:text-violet-600">
            {product.title}
          </h3>
        </Link>

        {product.brand && (
          <p className="mt-1 text-xs text-slate-500">Brand: {product.brand}</p>
        )}

        {description && (
          <p className="mt-2 line-clamp-2 text-xs leading-relaxed text-slate-600">
            {description}
          </p>
        )}

        <div className="mt-2 flex items-center gap-1 text-xs text-rose-500">
          <span>★ {rating.toFixed(1)}</span>
          <span className="text-slate-400">({reviewCount.toLocaleString()} reviews)</span>
        </div>

        <div className="mt-auto pt-3">
          <p className="text-lg font-bold text-slate-900">
            {formatPrice(Number(product.price), product.currency || "LKR")}
          </p>
          <button
            type="button"
            disabled={adding}
            onClick={() => onAddToCart(product.product_id)}
            className="mt-3 w-full rounded-md bg-rose-500 py-2 text-sm font-semibold text-white hover:bg-rose-600 disabled:opacity-60"
          >
            {adding ? "Adding..." : "Add to Cart"}
          </button>
        </div>
      </div>
    </article>
  );
}
