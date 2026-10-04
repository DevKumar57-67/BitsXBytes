"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { useAuth } from "@/lib/auth-context";

export default function Home() {
  const router = useRouter();
  const { user, status, signOut } = useAuth();

  useEffect(() => {
    if (status === "unauthenticated") router.replace("/login");
  }, [router, status]);

  if (status !== "authenticated" || !user) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-[#08090D] px-6 text-sm text-slate-400">
        Loading your account...
      </main>
    );
  }

  async function handleSignOut() {
    await signOut();
    router.replace("/login");
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#08090D] px-6 py-12 text-white">
      <section className="w-full max-w-xl border border-slate-800 bg-[#111318] p-8 sm:p-10">
        <div className="mb-10 flex items-center gap-3">
          <div className="flex h-11 w-11 items-center justify-center bg-[#3B82F6] text-xl font-black">
            B
          </div>
          <span className="text-sm font-semibold tracking-wide">BITSXBYTES</span>
        </div>

        <p className="mb-2 text-sm text-slate-400">Signed in as</p>
        <h1 className="text-3xl font-semibold">Welcome, {user.username}</h1>
        <p className="mt-3 text-slate-400">{user.email}</p>

        <button
          type="button"
          onClick={handleSignOut}
          className="mt-10 border border-slate-700 px-4 py-2.5 text-sm font-medium transition hover:border-slate-500 hover:bg-slate-900"
        >
          Sign out
        </button>
      </section>
    </main>
  );
}
