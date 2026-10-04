const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const LEGACY_AUTH_STORAGE_KEY = "bxb-auth";

let accessToken: string | null = null;
let csrfToken: string | null = null;
let refreshInProgress: Promise<string> | null = null;

export type User = {
  username: string;
  email: string;
};

type RequestOptions = RequestInit;

class ApiError extends Error {
  constructor(
    message: string,
    readonly status: number
  ) {
    super(message);
  }
}

function getErrorMessage(data: unknown): string | undefined {
  if (typeof data === "string") return data;
  if (!data || typeof data !== "object") return undefined;

  const record = data as Record<string, unknown>;
  const preferred = record.detail ?? record.error;
  if (preferred) return getErrorMessage(preferred);

  for (const value of Object.values(record)) {
    const message = getErrorMessage(value);
    if (message) return message;
  }

  return undefined;
}

export async function apiRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const headers = new Headers(options.headers);
  if (
    options.body &&
    !(typeof FormData !== "undefined" && options.body instanceof FormData)
  ) {
    headers.set("Content-Type", "application/json");
  }

  const method = (options.method ?? "GET").toUpperCase();
  if (!["GET", "HEAD", "OPTIONS", "TRACE"].includes(method)) {
    headers.set("X-CSRFToken", await getCsrfToken());
  }

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...options,
    headers,
    credentials: "include",
  });
  const data = await response.json().catch(() => null);

  if (!response.ok) {
    throw new ApiError(
      getErrorMessage(data) ?? "Something went wrong with the request.",
      response.status
    );
  }

  return data as T;
}

export function clearAuth(): void {
  accessToken = null;
  if (typeof window === "undefined") return;
  try {
    window.localStorage.removeItem(LEGACY_AUTH_STORAGE_KEY);
  } catch {
    // Authentication no longer depends on browser storage.
  }
}

if (typeof window !== "undefined") {
  clearAuth();
}

async function getCsrfToken(): Promise<string> {
  if (csrfToken) return csrfToken;

  const result = await apiRequest<{ csrfToken: string }>("/api/auth/csrf/");
  csrfToken = result.csrfToken;
  return csrfToken;
}

async function refreshAccessToken(): Promise<string> {
  if (refreshInProgress) return refreshInProgress;

  const refreshPromise = apiRequest<{ access: string }>("/api/auth/refresh/", {
    method: "POST",
    body: JSON.stringify({}),
  })
    .then(({ access }) => {
      accessToken = access;
      return access;
    })
    .catch((error: unknown) => {
      accessToken = null;
      throw error;
    });

  const sharedRefresh = refreshPromise.finally(() => {
    refreshInProgress = null;
  });
  refreshInProgress = sharedRefresh;
  return sharedRefresh;
}

async function requestWithAccess<T>(
  endpoint: string,
  access: string,
  options: RequestOptions
): Promise<T> {
  const headers = new Headers(options.headers);
  headers.set("Authorization", `Bearer ${access}`);
  return apiRequest<T>(endpoint, { ...options, headers });
}

export async function authenticatedRequest<T>(
  endpoint: string,
  options: RequestOptions = {}
): Promise<T> {
  const currentAccess = accessToken ?? await refreshAccessToken();

  try {
    return await requestWithAccess<T>(endpoint, currentAccess, options);
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
  }

  accessToken = null;
  const refreshedAccess = await refreshAccessToken();
  return requestWithAccess<T>(endpoint, refreshedAccess, options);
}

export async function login(username: string, password: string): Promise<void> {
  const result = await apiRequest<{ access: string }>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
  accessToken = result.access;
}

export async function register(
  username: string,
  email: string,
  password: string
): Promise<User> {
  return apiRequest<User>("/api/auth/register/", {
    method: "POST",
    body: JSON.stringify({ username, email, password }),
  });
}

export async function requestPasswordReset(email: string): Promise<void> {
  await apiRequest<{ detail: string }>("/api/auth/password-reset/", {
    method: "POST",
    body: JSON.stringify({ email }),
  });
}

export async function confirmPasswordReset(
  uid: string,
  token: string,
  newPassword: string,
  confirmPassword: string
): Promise<void> {
  await apiRequest<{ detail: string }>("/api/auth/password-reset/confirm/", {
    method: "POST",
    body: JSON.stringify({
      uid,
      token,
      new_password: newPassword,
      confirm_password: confirmPassword,
    }),
  });
  clearAuth();
}

export function getCurrentUser(): Promise<User> {
  return authenticatedRequest<User>("/api/auth/me/");
}

export async function logout(): Promise<void> {
  try {
    await apiRequest<void>("/api/auth/logout/", {
      method: "POST",
      body: JSON.stringify({}),
    });
  } finally {
    clearAuth();
  }
}
