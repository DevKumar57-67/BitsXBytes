"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { confirmPasswordReset } from "@/lib/api";
import { useAuth } from "@/lib/auth-context";

export default function ResetPasswordPage() {
  const router = useRouter();
  const { clearSession } = useAuth();
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    const params = new URLSearchParams(window.location.hash.slice(1));
    const uid = params.get("uid");
    const token = params.get("token");
    if (!uid || !token) {
      setError("This reset link is invalid or has expired. Request a new link.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Passwords do not match.");
      return;
    }

    setLoading(true);
    try {
      await confirmPasswordReset(uid, token, password, confirmPassword);
      clearSession();
      router.replace("/login");
    } catch {
      setError(
        "This reset link or password is invalid. Check your password and try again, or request a new link."
      );
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#08090D] px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#111318] p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#3B82F6] text-2xl font-black text-white">
            B
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Reset your password
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Choose a new password for your BitsXBytes account.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="password"
              className="mb-2 block text-sm font-medium text-slate-200"
            >
              New password
            </label>
            <input
              id="password"
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-white outline-none transition focus:border-[#3B82F6] focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          <div>
            <label
              htmlFor="confirm-password"
              className="mb-2 block text-sm font-medium text-slate-200"
            >
              Confirm new password
            </label>
            <input
              id="confirm-password"
              type="password"
              value={confirmPassword}
              onChange={(event) => setConfirmPassword(event.target.value)}
              required
              minLength={8}
              autoComplete="new-password"
              className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-white outline-none transition focus:border-[#3B82F6] focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          {error && (
            <p role="alert" className="rounded-xl bg-red-950/40 p-3 text-sm text-red-300">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={loading}
            className="w-full rounded-xl bg-[#3B82F6] py-3.5 font-semibold text-white transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {loading ? "Updating password..." : "Update password"}
          </button>
        </form>

        <p className="mt-7 text-center text-sm text-slate-400">
          <Link href="/forgot-password" className="font-semibold text-[#60A5FA] hover:text-white">
            Request a new reset link
          </Link>
        </p>
      </section>
    </main>
  );
}
