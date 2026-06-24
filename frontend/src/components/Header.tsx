"use client";

import Link from "next/link";
import { FormEvent } from "react";

interface HeaderProps {
  searchQuery: string;
  onSearchChange: (value: string) => void;
  onSearchSubmit: () => void;
  cartCount: number;
  chatOpen: boolean;
  onToggleChat: () => void;
}

export default function Header({
  searchQuery,
  onSearchChange,
  onSearchSubmit,
  cartCount,
  chatOpen,
  onToggleChat,
}: HeaderProps) {
  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    onSearchSubmit();
  };

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-[#131921] text-white shadow-md">
      <div className="mx-auto flex max-w-[1600px] items-center gap-4 px-4 py-3">
        <Link href="/" className="shrink-0 text-xl font-bold tracking-tight text-violet-400">
          FitWise
        </Link>

        <button
          type="button"
          onClick={onToggleChat}
          className={`hidden shrink-0 rounded-md px-4 py-2 text-sm font-medium md:inline-flex ${
            chatOpen
              ? "bg-violet-600 text-white"
              : "bg-slate-700 text-white hover:bg-slate-600"
          }`}
        >
          {chatOpen ? "Close AI Chat" : "AI Shopping Assistant"}
        </button>

        <form onSubmit={handleSubmit} className="flex flex-1 items-stretch gap-0">
          <input
            type="search"
            value={searchQuery}
            onChange={(e) => onSearchChange(e.target.value)}
            placeholder="Search fashion products..."
            className="w-full rounded-l-md border-0 px-4 py-2.5 text-sm text-slate-900 outline-none"
          />
          <button
            type="submit"
            className="rounded-r-md bg-violet-600 px-5 text-sm font-semibold text-white hover:bg-violet-700"
          >
            Search
          </button>
        </form>

        <Link
          href="/cart"
          className="relative flex shrink-0 items-center gap-2 rounded-md bg-slate-800 px-4 py-2 text-sm hover:bg-slate-700"
        >
          <span aria-hidden>🛒</span>
          <span>Cart</span>
          {cartCount > 0 && (
            <span className="absolute -right-1 -top-1 flex h-5 min-w-5 items-center justify-center rounded-full bg-rose-500 px-1 text-xs font-bold">
              {cartCount}
            </span>
          )}
        </Link>
      </div>
    </header>
  );
}
