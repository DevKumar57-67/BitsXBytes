const APP_ORIGIN = "https://bitsxbytes.local";

export function getPostAuthRedirect(next: string | null): string {
  if (!next || !next.startsWith("/") || next.startsWith("//") || next.includes("\\")) {
    return "/";
  }

  try {
    const destination = new URL(next, APP_ORIGIN);
    if (
      destination.origin !== APP_ORIGIN ||
      destination.pathname === "/login" ||
      destination.pathname === "/register"
    ) {
      return "/";
    }

    return `${destination.pathname}${destination.search}${destination.hash}`;
  } catch {
    return "/";
  }
}
