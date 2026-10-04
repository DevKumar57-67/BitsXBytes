"use client";

import { useEffect, type ReactNode } from "react";
import { usePathname, useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";
import { getPostAuthRedirect } from "@/lib/route-auth";

const GUEST_AUTH_PATHS = new Set(["/login", "/register"]);
const PUBLIC_PATHS = new Set([
  "/",
  "/login",
  "/register",
  "/forgot-password",
  "/reset-password",
  "/verify-email",
]);

export function AuthRouteGuard({ children }: { children: ReactNode }) {
  const pathname = usePathname();
  const router = useRouter();
  const { status } = useAuth();
  const isGuestAuthPage = GUEST_AUTH_PATHS.has(pathname);
  const isPublicPage = PUBLIC_PATHS.has(pathname);

  useEffect(() => {
    if (status === "loading") return;

    if (!isPublicPage && status === "unauthenticated") {
      const next = `${pathname}${window.location.search}`;
      router.replace(`/login?next=${encodeURIComponent(next)}`);
      return;
    }

    if (isGuestAuthPage && status === "authenticated") {
      const next = new URLSearchParams(window.location.search).get("next");
      router.replace(getPostAuthRedirect(next));
    }
  }, [isGuestAuthPage, isPublicPage, pathname, router, status]);

  if (
    (!isPublicPage && status !== "authenticated") ||
    (isGuestAuthPage && status === "authenticated")
  ) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#08090D] px-6 text-sm text-slate-400">
        Loading your account...
      </main>
    );
  }

  return children;
}
