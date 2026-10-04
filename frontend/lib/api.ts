const API_URL = process.env.NEXT_PUBLIC_API_URL ?? "http://127.0.0.1:8000";
const AUTH_STORAGE_KEY = "bxb-auth";

export type AuthTokens = {
  access: string;
  refresh: string;
};

export type User = {
  username: string;
  email: string;
};

type RequestOptions = RequestInit & {
  token?: string;
};

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
  const { token, ...fetchOptions } = options;
  const headers = new Headers(fetchOptions.headers);
  headers.set("Content-Type", "application/json");

  if (token) headers.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_URL}${endpoint}`, {
    ...fetchOptions,
    headers,
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

export function hasStoredAuth(): boolean {
  return Boolean(readStoredAuth());
}

export function saveAuth(tokens: AuthTokens): void {
  if (typeof window !== "undefined") {
    window.localStorage.setItem(AUTH_STORAGE_KEY, JSON.stringify(tokens));
  }
}

export function clearAuth(): void {
  if (typeof window !== "undefined") {
    window.localStorage.removeItem(AUTH_STORAGE_KEY);
  }
}

function readStoredAuth(): AuthTokens | null {
  if (typeof window === "undefined") return null;

  try {
    const value: unknown = JSON.parse(
      window.localStorage.getItem(AUTH_STORAGE_KEY) ?? "null"
    );
    if (
      value &&
      typeof value === "object" &&
      "access" in value &&
      "refresh" in value &&
      typeof value.access === "string" &&
      typeof value.refresh === "string"
    ) {
      return { access: value.access, refresh: value.refresh };
    }
  } catch {
    clearAuth();
  }

  return null;
}

let refreshInProgress: Promise<AuthTokens> | null = null;

async function refreshStoredAuth(): Promise<AuthTokens> {
  if (refreshInProgress) return refreshInProgress;

  const refreshPromise = (async (): Promise<AuthTokens> => {
    const current = readStoredAuth();
    if (!current) {
      throw new Error("Your session has expired. Please sign in again.");
    }

    const refreshed = await apiRequest<Partial<AuthTokens>>(
      "/api/auth/refresh/",
      {
        method: "POST",
        body: JSON.stringify({ refresh: current.refresh }),
      }
    );
    if (!refreshed.access) {
      throw new Error("Your session has expired. Please sign in again.");
    }

    const next: AuthTokens = {
      access: refreshed.access,
      refresh: refreshed.refresh ?? current.refresh,
    };
    saveAuth(next);
    return next;
  })();

  const sharedRefresh = refreshPromise.finally(() => {
    refreshInProgress = null;
  });
  refreshInProgress = sharedRefresh;
  return sharedRefresh;
}

export async function authenticatedRequest<T>(
  endpoint: string,
  options: Omit<RequestOptions, "token"> = {}
): Promise<T> {
  const current = readStoredAuth();
  if (!current) throw new Error("Please sign in to continue.");

  try {
    return await apiRequest<T>(endpoint, { ...options, token: current.access });
  } catch (error) {
    if (!(error instanceof ApiError) || error.status !== 401) throw error;
  }

  try {
    const refreshed = await refreshStoredAuth();
    return await apiRequest<T>(endpoint, { ...options, token: refreshed.access });
  } catch (error) {
    clearAuth();
    throw error;
  }
}

export async function login(
  username: string,
  password: string
): Promise<AuthTokens> {
  return apiRequest<AuthTokens>("/api/auth/login/", {
    method: "POST",
    body: JSON.stringify({ username, password }),
  });
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

export function getCurrentUser(): Promise<User> {
  return authenticatedRequest<User>("/api/auth/me/");
}

export async function logout(): Promise<void> {
  const tokens = readStoredAuth();
  if (!tokens) return;

  await authenticatedRequest<void>("/api/auth/logout/", {
    method: "POST",
    body: JSON.stringify({ refresh: tokens.refresh }),
  });
}