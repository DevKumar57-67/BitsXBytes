const EMAIL_KEY = "bxb-pending-verification-email";
const RESEND_AVAILABLE_AT_KEY = "bxb-verification-resend-available-at";

export const VERIFICATION_RESEND_COOLDOWN_SECONDS = 60;

export function savePendingVerification(email: string): void {
  try {
    window.sessionStorage.setItem(EMAIL_KEY, email);
    window.sessionStorage.setItem(
      RESEND_AVAILABLE_AT_KEY,
      String(Date.now() + VERIFICATION_RESEND_COOLDOWN_SECONDS * 1000)
    );
  } catch {
    // The verification page allows the email to be entered manually.
  }
}

export function getPendingVerificationEmail(): string {
  try {
    return window.sessionStorage.getItem(EMAIL_KEY) ?? "";
  } catch {
    return "";
  }
}

export function getResendCooldownSeconds(): number {
  try {
    const availableAt = Number(
      window.sessionStorage.getItem(RESEND_AVAILABLE_AT_KEY)
    );
    if (!Number.isFinite(availableAt) || availableAt <= 0) return 0;
    return Math.max(0, Math.ceil((availableAt - Date.now()) / 1000));
  } catch {
    return 0;
  }
}

export function startResendCooldown(): number {
  const availableAt =
    Date.now() + VERIFICATION_RESEND_COOLDOWN_SECONDS * 1000;
  try {
    window.sessionStorage.setItem(
      RESEND_AVAILABLE_AT_KEY,
      String(availableAt)
    );
  } catch {
    // The API continues to enforce the resend limit.
  }
  return VERIFICATION_RESEND_COOLDOWN_SECONDS;
}

export function clearPendingVerification(): void {
  try {
    window.sessionStorage.removeItem(EMAIL_KEY);
    window.sessionStorage.removeItem(RESEND_AVAILABLE_AT_KEY);
  } catch {
    // Verification has completed; storage is only a client-side convenience.
  }
}
