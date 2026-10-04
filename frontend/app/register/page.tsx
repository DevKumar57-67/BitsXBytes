"use client";

import { FormEvent, useState } from "react";
import Link from "next/link";
import { useAuth } from "@/lib/auth-context";
import { resendEmailVerification } from "@/lib/api";

export default function RegisterPage() {
  const { signUp } = useAuth();
  const [username, setUsername] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const [registered, setRegistered] = useState(false);
  const [resendMessage, setResendMessage] = useState("");
  const [resendLoading, setResendLoading] = useState(false);

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();

    setError("");
    setLoading(true);

    try {
      await signUp(username, email, password);
      setRegistered(true);
    } catch (error) {
      setError(
        error instanceof Error
          ? error.message
          : "Registration failed."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    setResendLoading(true);
    setResendMessage("");
    try {
      await resendEmailVerification(email);
      setResendMessage(
        "If the account needs verification, a verification link will be sent."
      );
    } catch {
      setResendMessage("We could not process the request. Please try again.");
    } finally {
      setResendLoading(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#08090D] px-4 py-10">
      <div className="w-full max-w-md">

        {/* Brand */}
        <div className="mb-8 text-center">
          <div className="mb-4 inline-flex items-center justify-center">
            <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#3B82F6] text-2xl font-black text-white shadow-lg shadow-blue-500/30">
              B
            </div>
          </div>

          <h1 className="text-3xl font-bold tracking-tight text-white">
            Join BxB
          </h1>

          <p className="mt-2 text-sm text-slate-400">
            Build. Connect. Learn. Create.
          </p>
        </div>

        {/* Registration Card */}
        <div className="rounded-2xl border border-slate-800 bg-[#111318] p-8 shadow-2xl">

          <div className="mb-7">
            <h2 className="text-xl font-semibold text-white">
              Create your account
            </h2>

            <p className="mt-1 text-sm text-slate-400">
              Start your BitsXBytes journey.
            </p>
          </div>

          {registered ? (
            <div className="space-y-5">
              <div role="status" className="rounded-xl bg-emerald-950/40 p-4 text-sm text-emerald-300">
                <h3 className="font-semibold text-white">Check your email</h3>
                <p className="mt-2">
                  We sent a verification link to <strong>{email}</strong>. Verify
                  your email before signing in.
                </p>
              </div>
              <button
                type="button"
                onClick={handleResend}
                disabled={resendLoading}
                className="w-full rounded-xl border border-slate-700 py-3 font-semibold text-white transition hover:border-[#3B82F6] disabled:opacity-50"
              >
                {resendLoading ? "Sending..." : "Resend verification email"}
              </button>
              {resendMessage && (
                <p role="status" className="text-center text-sm text-slate-300">
                  {resendMessage}
                </p>
              )}
            </div>
          ) : (
          <form onSubmit={handleSubmit} className="space-y-5">

            {/* Username */}
            <div>
              <label
                htmlFor="username"
                className="mb-2 block text-sm font-medium text-slate-200"
              >
                Username
              </label>

              <input
                id="username"
                type="text"
                value={username}
                onChange={(event) => setUsername(event.target.value)}
                required
                autoComplete="username"
                placeholder="Choose a username"
                className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-white placeholder:text-slate-500 outline-none transition focus:border-[#3B82F6] focus:ring-2 focus:ring-blue-500/20"
              />
            </div>

            {/* Email */}
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

            {/* Password */}
            <div>
              <label
                htmlFor="password"
                className="mb-2 block text-sm font-medium text-slate-200"
              >
                Password
              </label>

              <input
                id="password"
                type="password"
                value={password}
                onChange={(event) => setPassword(event.target.value)}
                required
                minLength={8}
                autoComplete="new-password"
                placeholder="Create a password"
                className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-white placeholder:text-slate-500 outline-none transition focus:border-[#3B82F6] focus:ring-2 focus:ring-blue-500/20"
              />

              <p className="mt-2 text-xs text-slate-500">
                Minimum 8 characters.
              </p>
            </div>

            {/* Error */}
            {error && (
              <div className="rounded-xl border border-red-900/50 bg-red-950/30 p-3">
                <p className="text-sm text-red-400">
                  {error}
                </p>
              </div>
            )}

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="w-full rounded-xl bg-[#3B82F6] py-3.5 font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:bg-blue-500 hover:shadow-blue-500/30 disabled:cursor-not-allowed disabled:opacity-50"
            >
              {loading ? "Creating account..." : "Create Account"}
            </button>
          </form>
          )}

          {/* Login */}
          <p className="mt-7 text-center text-sm text-slate-400">
            Already have an account?{" "}
            <Link
              href="/login"
              className="font-semibold text-[#60A5FA] hover:text-white"
            >
              Sign in
            </Link>
          </p>
        </div>

        <p className="mt-6 text-center text-xs text-slate-600">
          © 2026 BitsXBytes. Built for the college tech community.
        </p>
      </div>
    </main>
  );
}