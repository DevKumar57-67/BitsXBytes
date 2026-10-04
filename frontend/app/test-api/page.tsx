"use client";

import { FormEvent, useState } from "react";
import { login } from "@/lib/api";

export default function LoginPage() {
const [username, setUsername] = useState("");
const [password, setPassword] = useState("");
const [error, setError] = useState("");
const [loading, setLoading] = useState(false);

async function handleSubmit(event: FormEvent<HTMLFormElement>) {
event.preventDefault();

setError("");
setLoading(true);

try {
  await login(username, password);

  alert("Login successful!");
} catch (error) {
  setError(
    error instanceof Error
      ? error.message
      : "Login failed."
  );
} finally {
  setLoading(false);
}


}

return ( <main className="flex min-h-screen items-center justify-center bg-[#08090D] px-4 py-10"> <div className="w-full max-w-md">


    {/* Brand */}
    <div className="mb-8 text-center">
      <div className="mb-4 inline-flex items-center justify-center">
        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-[#3B82F6] text-2xl font-black text-white shadow-lg shadow-blue-500/30">
          B
        </div>
      </div>

      <h1 className="text-3xl font-bold tracking-tight text-white">
        Welcome to BxB
      </h1>

      <p className="mt-2 text-sm text-slate-400">
        Your college technology ecosystem.
      </p>
    </div>

    {/* Login Card */}
    <div className="rounded-2xl border border-slate-800 bg-[#111318] p-8 shadow-2xl">

      <div className="mb-7">
        <h2 className="text-xl font-semibold text-white">
          Sign in
        </h2>

        <p className="mt-1 text-sm text-slate-400">
          Continue to your BitsXBytes account.
        </p>
      </div>

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
            placeholder="Enter your username"
            className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-white placeholder:text-slate-500 outline-none transition focus:border-[#3B82F6] focus:ring-2 focus:ring-blue-500/20"
          />
        </div>

        {/* Password */}
        <div>
          <div className="mb-2 flex items-center justify-between">
            <label
              htmlFor="password"
              className="block text-sm font-medium text-slate-200"
            >
              Password
            </label>

            <button
              type="button"
              className="text-xs font-medium text-[#60A5FA] transition hover:text-white"
            >
              Forgot password?
            </button>
          </div>

          <input
            id="password"
            type="password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
            autoComplete="current-password"
            placeholder="Enter your password"
            className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-white placeholder:text-slate-500 outline-none transition focus:border-[#3B82F6] focus:ring-2 focus:ring-blue-500/20"
          />
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
          {loading ? "Signing in..." : "Sign In"}
        </button>
      </form>

      {/* Divider */}
      <div className="my-7 flex items-center gap-4">
        <div className="h-px flex-1 bg-slate-800" />
        <span className="text-xs text-slate-500">
          OR
        </span>
        <div className="h-px flex-1 bg-slate-800" />
      </div>

      {/* OAuth placeholders */}
      <div className="grid grid-cols-2 gap-3">
        <button
          type="button"
          className="rounded-xl border border-slate-700 bg-[#08090D] py-3 text-sm font-medium text-slate-200 transition hover:border-slate-600 hover:bg-slate-900"
        >
          Continue with Google
        </button>

        <button
          type="button"
          className="rounded-xl border border-slate-700 bg-[#08090D] py-3 text-sm font-medium text-slate-200 transition hover:border-slate-600 hover:bg-slate-900"
        >
          Continue with GitHub
        </button>
      </div>

      {/* Signup */}
      <p className="mt-7 text-center text-sm text-slate-400">
        Don&apos;t have a BxB account?{" "}
        <a
          href="/register"
          className="font-semibold text-[#60A5FA] hover:text-white"
        >
          Create one
        </a>
      </p>
    </div>

    {/* Footer */}
    <p className="mt-6 text-center text-xs text-slate-600">
      © 2026 BitsXBytes. Built for the college tech community.
    </p>
  </div>
</main>


);
}
