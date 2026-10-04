"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { resendEmailVerification, verifyEmail } from "@/lib/api";

type VerificationStatus =
  | "checking"
  | "verified"
  | "already_verified"
  | "invalid";

export default function VerifyEmailPage() {
  const [status, setStatus] = useState<VerificationStatus>("checking");
  const [email, setEmail] = useState("");
  const [resendMessage, setResendMessage] = useState("");
  const [resendLoading, setResendLoading] = useState(false);

  useEffect(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    window.history.replaceState(null, "", window.location.pathname);
    if (!token) {
      Promise.resolve().then(() => setStatus("invalid"));
      return;
    }

    verifyEmail(token)
      .then((result) => setStatus(result.status))
      .catch(() => setStatus("invalid"));
  }, []);

  async function handleResend(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
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

  const statusMessage = {
    checking: "Checking your verification link...",
    verified: "Your email is verified. You can now sign in.",
    already_verified: "This email address is already verified. You can sign in.",
    invalid: "This verification link is invalid or has expired.",
  }[status];

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#08090D] px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#111318] p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#3B82F6] text-2xl font-black text-white">
            B
          </div>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Verify your email
          </h1>
          <p
            role={status === "invalid" ? "alert" : "status"}
            className="mt-3 text-sm text-slate-300"
          >
            {statusMessage}
          </p>
        </div>

        {status === "invalid" && (
          <form onSubmit={handleResend} className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="mb-2 block text-sm font-medium text-slate-200"
              >
                Account email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(event) => setEmail(event.target.value)}
                required
                autoComplete="email"
                className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-white outline-none focus:border-[#3B82F6]"
              />
            </div>
            <button
              type="submit"
              disabled={resendLoading}
              className="w-full rounded-xl bg-[#3B82F6] py-3 font-semibold text-white transition hover:bg-blue-500 disabled:opacity-50"
            >
              {resendLoading ? "Sending..." : "Resend verification email"}
            </button>
            {resendMessage && (
              <p role="status" className="text-sm text-slate-300">
                {resendMessage}
              </p>
            )}
          </form>
        )}

        {status !== "checking" && (
          <p className="mt-7 text-center text-sm text-slate-400">
            <Link href="/login" className="font-semibold text-[#60A5FA] hover:text-white">
              Continue to sign in
            </Link>
          </p>
        )}
      </section>
    </main>
  );
}
