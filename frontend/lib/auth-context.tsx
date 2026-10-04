"use client";

import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import {
  clearAuth,
  getCurrentUser,
  login,
  logout,
  register as registerAccount,
  type User,
} from "@/lib/api";

type AuthStatus = "loading" | "authenticated" | "unauthenticated";

type AuthContextValue = {
  user: User | null;
  status: AuthStatus;
  signIn: (username: string, password: string) => Promise<void>;
  signUp: (username: string, email: string, password: string) => Promise<boolean>;
  signOut: () => Promise<void>;
  clearSession: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [status, setStatus] = useState<AuthStatus>("loading");

  useEffect(() => {
    let active = true;

    getCurrentUser()
      .then((currentUser) => {
        if (!active) return;
        setUser(currentUser);
        setStatus("authenticated");
      })
      .catch(() => {
        clearAuth();
        if (!active) return;
        setUser(null);
        setStatus("unauthenticated");
      });

    return () => {
      active = false;
    };
  }, []);

  async function signIn(username: string, password: string) {
    setStatus("loading");
    try {
      await login(username, password);
      const currentUser = await getCurrentUser();
      setUser(currentUser);
      setStatus("authenticated");
    } catch (error) {
      clearAuth();
      setUser(null);
      setStatus("unauthenticated");
      throw error;
    }
  }

  async function signUp(username: string, email: string, password: string) {
    setStatus("loading");
    try {
      const result = await registerAccount(username, email, password);
      clearAuth();
      setUser(null);
      setStatus("unauthenticated");
      return result.email_sent;
    } catch (error) {
      clearAuth();
      setUser(null);
      setStatus("unauthenticated");
      throw error;
    }
  }

  async function signOut() {
    try {
      await logout();
    } finally {
      setUser(null);
      setStatus("unauthenticated");
    }
  }

  function clearSession() {
    clearAuth();
    setUser(null);
    setStatus("unauthenticated");
  }

  return (
    <AuthContext.Provider
      value={{ user, status, signIn, signUp, signOut, clearSession }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) throw new Error("useAuth must be used inside AuthProvider");
  return context;
}