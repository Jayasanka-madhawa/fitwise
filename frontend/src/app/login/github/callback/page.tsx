"use client";

import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useState } from "react";
import { useAuth } from "@/context/AuthContext";
import { githubRedirectUri } from "@/components/SocialLoginButtons";

function GithubCallbackInner() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const { githubLogin } = useAuth();
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const code = searchParams.get("code");
    const state = searchParams.get("state");
    const oauthError = searchParams.get("error");

    if (oauthError) {
      setError("GitHub sign-in was cancelled");
      return;
    }
    if (!code) {
      setError("Missing authorization code from GitHub");
      return;
    }

    const finish = async () => {
      try {
        await githubLogin(code, githubRedirectUri());
        router.replace(state ? decodeURIComponent(state) : "/");
      } catch (err) {
        setError(err instanceof Error ? err.message : "GitHub sign-in failed");
      }
    };
    finish();
  }, [searchParams, githubLogin, router]);

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#eaeded] px-4">
      <div className="w-full max-w-md rounded-2xl border border-slate-200 bg-white p-8 text-center shadow-sm">
        <Link href="/" className="text-xl font-bold text-violet-600">
          FitWise
        </Link>
        {error ? (
          <>
            <p className="mt-6 text-sm text-red-600">{error}</p>
            <Link
              href="/login"
              className="mt-4 inline-block text-sm font-medium text-violet-600 hover:text-violet-700"
            >
              Back to sign in
            </Link>
          </>
        ) : (
          <p className="mt-6 text-sm text-slate-600">Signing you in with GitHub...</p>
        )}
      </div>
    </div>
  );
}

export default function GithubCallbackPage() {
  return (
    <Suspense fallback={<div className="min-h-screen bg-[#eaeded]" />}>
      <GithubCallbackInner />
    </Suspense>
  );
}
