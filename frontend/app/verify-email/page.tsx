"use client";

import { FormEvent, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { resendEmailVerification, verifyEmail } from "@/lib/api";
import {
  clearPendingVerification,
  getPendingVerificationEmail,
  getResendCooldownSeconds,
  startResendCooldown,
} from "@/lib/email-verification";

export default function VerifyEmailPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [otp, setOtp] = useState("");
  const [error, setError] = useState("");
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(false);
  const [resending, setResending] = useState(false);
  const [resendCountdown, setResendCountdown] = useState(0);
  const [verified, setVerified] = useState(false);

  useEffect(() => {
    const pendingEmail = getPendingVerificationEmail();
    const cooldown = getResendCooldownSeconds();
    Promise.resolve().then(() => {
      if (pendingEmail) setEmail(pendingEmail);
      setResendCountdown(cooldown);
    });
  }, []);

  useEffect(() => {
    if (resendCountdown <= 0) return undefined;
    const timer = window.setInterval(() => {
      setResendCountdown((remaining) => Math.max(remaining - 1, 0));
    }, 1000);
    return () => window.clearInterval(timer);
  }, [resendCountdown]);

  async function handleVerify(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setMessage("");
    setLoading(true);

    try {
      await verifyEmail(email, otp);
      setVerified(true);
      setMessage("Your email is verified. Redirecting you to sign in...");
      clearPendingVerification();
      window.setTimeout(() => router.replace("/login?verified=1"), 1500);
    } catch {
      setError(
        "That code is invalid or expired. Check the code or request a new one."
      );
    } finally {
      setLoading(false);
    }
  }

  async function handleResend() {
    if (resendCountdown > 0 || resending || !email) return;
    setError("");
    setMessage("");
    setResending(true);

    try {
      await resendEmailVerification(email);
      setOtp("");
      setMessage("If the account needs verification, a new code will be sent.");
      setResendCountdown(startResendCooldown());
    } catch {
      setError("We could not process your request. Please try again shortly.");
    } finally {
      setResending(false);
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-[#08090D] px-4 py-10">
      <section className="w-full max-w-md rounded-2xl border border-slate-800 bg-[#111318] p-8 shadow-2xl">
        <div className="mb-8 text-center">
          <div className="mx-auto mb-4 flex h-14 w-14 items-center justify-center rounded-2xl bg-[#3B82F6] text-2xl font-black text-white shadow-lg shadow-blue-500/30">
            B
          </div>
          <p className="mb-2 text-sm font-semibold uppercase tracking-[0.2em] text-[#60A5FA]">
            BitsXBytes
          </p>
          <h1 className="text-3xl font-bold tracking-tight text-white">
            Verify your email
          </h1>
          <p className="mt-3 text-sm text-slate-400">
            Enter the 6-digit OTP sent to your registered email address.
          </p>
        </div>

        {verified ? (
          <div
            role="status"
            className="rounded-xl border border-emerald-800 bg-emerald-950/40 p-4 text-center text-sm text-emerald-300"
          >
            {message}
          </div>
        ) : (
          <>
            <form onSubmit={handleVerify} className="space-y-5">
              <div>
                <label
                  htmlFor="email"
                  className="mb-2 block text-sm font-medium text-slate-200"
                >
                  Email address
                </label>
                <input
                  id="email"
                  type="email"
                  value={email}
                  onChange={(event) => setEmail(event.target.value)}
                  required
                  autoComplete="email"
                  className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-white outline-none transition focus:border-[#3B82F6] focus:ring-2 focus:ring-blue-500/20"
                />
              </div>

              <div>
                <label
                  htmlFor="otp"
                  className="mb-2 block text-sm font-medium text-slate-200"
                >
                  6-digit OTP
                </label>
                <input
                  id="otp"
                  type="text"
                  inputMode="numeric"
                  autoComplete="one-time-code"
                  pattern="[0-9]{6}"
                  maxLength={6}
                  value={otp}
                  onChange={(event) =>
                    setOtp(event.target.value.replace(/\D/g, "").slice(0, 6))
                  }
                  aria-describedby="otp-hint"
                  required
                  disabled={loading}
                  className="w-full rounded-xl border border-slate-700 bg-[#08090D] px-4 py-3 text-center text-2xl tracking-[0.5em] text-white outline-none transition focus:border-[#3B82F6] focus:ring-2 focus:ring-blue-500/20 disabled:opacity-60"
                />
                <p id="otp-hint" className="mt-2 text-xs text-slate-500">
                  Use the code from your email. You can paste all 6 digits.
                </p>
              </div>

              {error && (
                <p
                  role="alert"
                  className="rounded-xl border border-red-900/50 bg-red-950/40 p-3 text-sm text-red-300"
                >
                  {error}
                </p>
              )}
              {message && (
                <p
                  role="status"
                  className="rounded-xl border border-blue-900/50 bg-blue-950/40 p-3 text-sm text-blue-200"
                >
                  {message}
                </p>
              )}

              <button
                type="submit"
                disabled={loading || otp.length !== 6 || !email}
                className="w-full rounded-xl bg-[#3B82F6] py-3.5 font-semibold text-white shadow-lg shadow-blue-500/20 transition hover:bg-blue-500 disabled:cursor-not-allowed disabled:opacity-50"
              >
                {loading ? "Verifying..." : "Verify email"}
              </button>
            </form>

            <button
              type="button"
              onClick={handleResend}
              disabled={resending || resendCountdown > 0 || !email}
              className="mt-3 w-full rounded-xl border border-slate-700 py-3 font-semibold text-white transition hover:border-[#3B82F6] disabled:cursor-not-allowed disabled:opacity-50"
            >
              {resending
                ? "Sending..."
                : resendCountdown > 0
                  ? `Resend OTP in ${resendCountdown}s`
                  : "Resend OTP"}
            </button>
          </>
        )}

        <p className="mt-7 text-center text-sm text-slate-400">
          <Link
            href="/login"
            className="font-semibold text-[#60A5FA] transition hover:text-white"
          >
            Return to sign in
          </Link>
        </p>
      </section>
    </main>
  );
}
