"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { FormEvent, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { useChat } from "@/context/ChatContext";

interface HeaderProps {
  searchQuery?: string;
  onSearchChange?: (value: string) => void;
  onSearchSubmit?: () => void;
}

function CartIcon() {
  return (
    <svg className="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor" aria-hidden>
      <path
        strokeLinecap="round"
        strokeLinejoin="round"
        strokeWidth={1.75}
        d="M2.25 3h1.386c.51 0 .955.343 1.087.835l.383 1.437M7.5 14.25a3 3 0 00-3 3h15.75m-12.75-3h11.218c1.121-2.3 2.1-4.684 2.924-7.138a60.114 60.114 0 00-16.536-1.84M7.5 14.25L5.106 5.272M6 20.25a.75.75 0 11-1.5 0 .75.75 0 011.5 0zm12.75 0a.75.75 0 11-1.5 0 .75.75 0 011.5 0z"
      />
    </svg>
  );
}

function SparkleIcon() {
  return (
    <svg className="h-4 w-4" fill="currentColor" viewBox="0 0 24 24" aria-hidden>
      <path d="M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09zM18.259 8.715L18 9.75l-.259-1.035a3.375 3.375 0 00-2.455-2.456L14.25 6l1.036-.259a3.375 3.375 0 002.455-2.456L18 2.25l.259 1.035a3.375 3.375 0 002.455 2.456L21.75 6l-1.036.259a3.375 3.375 0 00-2.455 2.456z" />
    </svg>
  );
}

export default function Header({
  searchQuery: controlledQuery,
  onSearchChange,
  onSearchSubmit,
}: HeaderProps) {
  const router = useRouter();
  const { user, cartCount, logout } = useAuth();
  const { chatOpen, toggleChat } = useChat();
  const [localQuery, setLocalQuery] = useState("");

  const searchQuery = controlledQuery ?? localQuery;
  const handleSearchChange = onSearchChange ?? setLocalQuery;

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault();
    if (onSearchSubmit) {
      onSearchSubmit();
      return;
    }
    const q = searchQuery.trim();
    router.push(q ? `/?q=${encodeURIComponent(q)}` : "/");
  };

  const aiButtonClass = chatOpen
    ? "bg-violet-600 text-white ring-2 ring-violet-400/50"
    : "bg-slate-700/80 text-white hover:bg-slate-600";

  const searchForm = (className: string) => (
    <form onSubmit={handleSubmit} className={className}>
      <input
        type="search"
        value={searchQuery}
            onChange={(e) => handleSearchChange(e.target.value)}
        placeholder="Search fashion products..."
        aria-label="Search products"
        className="min-w-0 flex-1 rounded-l-md border-0 bg-white px-3 py-2 text-sm text-slate-900 placeholder:text-slate-500 outline-none focus:ring-2 focus:ring-violet-500 sm:px-4 sm:py-2.5"
      />
      <button
        type="submit"
        className="shrink-0 rounded-r-md bg-violet-600 px-4 text-sm font-semibold text-white hover:bg-violet-500 sm:px-5"
      >
        Search
      </button>
    </form>
  );

  return (
    <header className="sticky top-0 z-40 border-b border-slate-800 bg-[#131921] text-white shadow-md">
      <div className="mx-auto max-w-[1600px] px-3 py-2 sm:px-4 sm:py-2.5">
        <div className="flex flex-wrap items-center gap-x-3 gap-y-2 lg:flex-nowrap lg:gap-4">
          {/* Logo */}
          <Link
            href="/"
            className="order-1 shrink-0 text-xl font-bold tracking-tight text-violet-400 sm:text-2xl"
          >
            FitWise
          </Link>

          {/* Desktop AI toggle */}
          <button
            type="button"
            onClick={toggleChat}
            className={`order-2 hidden shrink-0 items-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium lg:inline-flex ${aiButtonClass}`}
          >
            <SparkleIcon />
            {chatOpen ? "Close AI" : "AI Assistant"}
          </button>

          <div className="order-3 ml-auto flex shrink-0 items-center gap-2 sm:gap-3 lg:gap-4">
            {searchForm("hidden min-w-0 lg:flex lg:w-[42rem] lg:flex-none")}

            {/* Mobile AI toggle */}
            <button
              type="button"
              onClick={toggleChat}
              aria-label={chatOpen ? "Close AI assistant" : "Open AI assistant"}
              className={`inline-flex items-center gap-1 rounded-md px-2.5 py-2 text-xs font-semibold lg:hidden ${aiButtonClass}`}
            >
              <SparkleIcon />
              AI
            </button>

            {user ? (
              <>
                <div className="hidden min-w-0 flex-col leading-tight xl:flex">
                  <span className="text-[11px] text-slate-400">Hello,</span>
                  <span className="max-w-[120px] truncate text-sm font-medium">
                    {user.name || user.email.split("@")[0]}
                  </span>
                </div>

                <Link
                  href="/cart"
                  aria-label={`Cart${cartCount > 0 ? `, ${cartCount} items` : ""}`}
                  className="relative flex items-center gap-1.5 rounded-md px-2 py-2 text-sm hover:bg-slate-800 sm:gap-2 sm:px-3"
                >
                  <CartIcon />
                  <span className="hidden font-medium sm:inline">Cart</span>
                  {cartCount > 0 && (
                    <span className="absolute -right-0.5 -top-0.5 flex h-[18px] min-w-[18px] items-center justify-center rounded-full bg-rose-500 px-1 text-[10px] font-bold leading-none">
                      {cartCount > 99 ? "99+" : cartCount}
                    </span>
                  )}
                </Link>

                <button
                  type="button"
                  onClick={logout}
                  className="rounded-md px-2 py-2 text-xs text-slate-300 hover:bg-slate-800 hover:text-white sm:px-3 sm:text-sm"
                >
                  Sign out
                </button>
              </>
            ) : (
              <>
                <Link
                  href="/login"
                  className="hidden min-w-0 flex-col leading-tight hover:text-violet-300 xl:flex"
                >
                  <span className="text-[11px] text-slate-400">Hello, sign in</span>
                  <span className="text-sm font-semibold">Account</span>
                </Link>
                <Link
                  href="/login"
                  className="rounded-md bg-violet-600 px-3 py-2 text-sm font-semibold hover:bg-violet-500 xl:hidden"
                >
                  Sign in
                </Link>
              </>
            )}
          </div>

          {searchForm("order-4 flex min-w-0 basis-full items-stretch lg:hidden")}
        </div>
      </div>
    </header>
  );
}
