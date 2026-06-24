"use client";

import { GoogleLogin, GoogleOAuthProvider } from "@react-oauth/google";
import { useEffect, useState } from "react";
import { fetchAuthConfig } from "@/lib/api";

function githubRedirectUri() {
  if (typeof window === "undefined") return "";
  return `${window.location.origin}/login/github/callback`;
}

function GoogleIcon() {
  return (
    <svg className="h-5 w-5 shrink-0" viewBox="0 0 48 48" aria-hidden>
      <path
        fill="#FFC107"
        d="M43.611 20.083H42V20H24v8h11.303c-1.649 4.657-6.08 8-11.303 8-6.627 0-12-5.373-12-12s5.373-12 12-12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 12.955 4 4 12.955 4 24s8.955 20 20 20 20-8.955 20-20c0-1.341-.138-2.65-.389-3.917z"
      />
      <path
        fill="#FF3D00"
        d="M6.306 14.691l6.571 4.819C14.655 15.108 18.961 12 24 12c3.059 0 5.842 1.154 7.961 3.039l5.657-5.657C34.046 6.053 29.268 4 24 4 16.318 4 9.656 8.337 6.306 14.691z"
      />
      <path
        fill="#4CAF50"
        d="M24 44c5.166 0 9.86-1.977 13.409-5.192l-6.19-5.238A11.91 11.91 0 0124 36c-5.202 0-9.619-3.317-11.283-7.946l-6.522 5.025C9.505 39.556 16.227 44 24 44z"
      />
      <path
        fill="#1976D2"
        d="M43.611 20.083H42V20H24v8h11.303a12.04 12.04 0 01-4.087 5.571l.003-.002 6.19 5.238C36.971 39.205 44 34 44 24c0-1.341-.138-2.65-.389-3.917z"
      />
    </svg>
  );
}

interface SocialLoginButtonsProps {
  mode: "login" | "register";
  disabled?: boolean;
  onGoogleSuccess: (credential: string) => Promise<void>;
  onError: (message: string) => void;
}

function GoogleSignInButton({
  mode,
  disabled,
  googleClientId,
  onGoogleSuccess,
  onError,
}: SocialLoginButtonsProps & { googleClientId: string }) {
  const label = mode === "login" ? "Sign in with Google" : "Sign up with Google";

  if (!googleClientId) {
    return (
      <button
        type="button"
        disabled={disabled}
        onClick={() =>
          onError(
            "Google sign-in is not configured. Add GOOGLE_CLIENT_ID to your project .env file, then restart the backend.",
          )
        }
        className="flex w-full items-center justify-center gap-3 rounded-md border border-slate-300 bg-white py-2.5 text-sm font-medium text-slate-700 shadow-sm hover:bg-slate-50 disabled:opacity-60"
      >
        <GoogleIcon />
        {label}
      </button>
    );
  }

  return (
    <GoogleOAuthProvider clientId={googleClientId}>
      <div className="relative w-full">
        <div
          className="pointer-events-none flex w-full items-center justify-center gap-3 rounded-md border border-slate-300 bg-white py-2.5 text-sm font-medium text-slate-700 shadow-sm"
          aria-hidden
        >
          <GoogleIcon />
          {label}
        </div>
        <div className="absolute inset-0 z-10 flex items-center justify-center opacity-0">
          <GoogleLogin
            onSuccess={async (res) => {
              if (!res.credential) return;
              try {
                await onGoogleSuccess(res.credential);
              } catch (err) {
                onError(err instanceof Error ? err.message : "Google sign-in failed");
              }
            }}
            onError={() => onError("Google sign-in was cancelled")}
            theme="outline"
            size="large"
            text={mode === "login" ? "signin_with" : "signup_with"}
            width="400"
          />
        </div>
      </div>
    </GoogleOAuthProvider>
  );
}

function SocialButtonsInner({
  googleClientId,
  githubClientId,
  ...props
}: SocialLoginButtonsProps & { googleClientId: string; githubClientId: string }) {
  const { mode, disabled, onError } = props;

  const startGithub = () => {
    if (!githubClientId) {
      onError("GitHub sign-in is not configured.");
      return;
    }
    const redirectUri = githubRedirectUri();
    const state = encodeURIComponent(window.location.pathname + window.location.search);
    window.location.href =
      `https://github.com/login/oauth/authorize?client_id=${githubClientId}` +
      `&redirect_uri=${encodeURIComponent(redirectUri)}` +
      "&scope=user:email&state=" +
      state;
  };

  return (
    <div className="mt-6 space-y-3">
      <GoogleSignInButton {...props} googleClientId={googleClientId} />

      {githubClientId && (
        <>
          <div className="flex items-center gap-3">
            <div className="h-px flex-1 bg-slate-200" />
            <span className="text-xs text-slate-400">or</span>
            <div className="h-px flex-1 bg-slate-200" />
          </div>
          <button
            type="button"
            disabled={disabled}
            onClick={startGithub}
            className="flex w-full items-center justify-center gap-2 rounded-md border border-slate-300 bg-slate-900 py-2.5 text-sm font-semibold text-white hover:bg-slate-800 disabled:opacity-60"
          >
            <svg className="h-5 w-5" viewBox="0 0 24 24" fill="currentColor" aria-hidden>
              <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.725-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z" />
            </svg>
            {mode === "login" ? "Sign in with GitHub" : "Sign up with GitHub"}
          </button>
        </>
      )}
    </div>
  );
}

export default function SocialLoginButtons(props: SocialLoginButtonsProps) {
  const [googleClientId, setGoogleClientId] = useState("");
  const [githubClientId, setGithubClientId] = useState("");

  useEffect(() => {
    fetchAuthConfig()
      .then((cfg) => {
        setGoogleClientId(cfg.google_client_id);
        setGithubClientId(cfg.github_client_id);
      })
      .catch(() => {
        /* OAuth IDs load from GET /auth/config */
      });
  }, []);

  return (
    <SocialButtonsInner
      {...props}
      googleClientId={googleClientId}
      githubClientId={githubClientId}
    />
  );
}

export { githubRedirectUri };
