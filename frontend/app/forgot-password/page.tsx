"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { requestPasswordReset } from "@/lib/api";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [message, setMessage] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setMessage("");
    setError("");
    setLoading(true);

    try {
      await requestPasswordReset(email);
      setMessage(
        "If an account with that email exists, password reset instructions have been sent."
      );
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "We could not process your request. Please try again."
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
            Forgot password?
          </h1>
          <p className="mt-2 text-sm text-slate-400">
            Enter your account email and we&apos;ll send reset instructions.
          </p>
        </div>

        <form onSubmit={handleSubmit} className="space-y-5">
          <div>
            <label
              htmlFor="email"
              className="mb-2 block text-sm font-medium text-slate-200"
            >
              Email
            </label>
            <input
              id="email"
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              required
              autoComplete="email"
              placeholder="you@example.com"
              className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-white placeholder:text-slate-500 outline-none transition focus:border-[#3B82F6] focus:ring-2 focus:ring-blue-500/20"
            />
          </div>

          {message && (
            <p role="status" className="rounded-xl bg-emerald-950/40 p-3 text-sm text-emerald-300">
              {message}
            </p>
          )}
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
            {loading ? "Sending..." : "Send reset instructions"}
          </button>
        </form>

        <p className="mt-7 text-center text-sm text-slate-400">
          Remembered your password?{" "}
          <Link href="/login" className="font-semibold text-[#60A5FA] hover:text-white">
            Sign in
          </Link>
        </p>
      </section>
    </main>
  );
}
