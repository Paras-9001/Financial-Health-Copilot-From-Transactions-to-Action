"use client";
import {
  createContext,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api, type User } from "@/lib/api";

type Auth = {
  user: User | null;
  token: string | null;
  ready: boolean;
  authenticate: (
    mode: "login" | "signup",
    email: string,
    password: string,
    name?: string,
  ) => Promise<User>;
  logout: () => void;
};
const Context = createContext<Auth | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient());
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
  const [ready, setReady] = useState(false);
  useEffect(() => {
    try {
      const saved = window.localStorage.getItem("fhc-session");
      if (saved) {
        const parsed = JSON.parse(saved) as { token: string; user: User };
        setToken(parsed.token);
        setUser(parsed.user);
      }
    } finally {
      setReady(true);
    }
  }, []);
  async function authenticate(
    mode: "login" | "signup",
    email: string,
    password: string,
    name?: string,
  ) {
    const result = await api<{ token: string }>(`/auth/${mode}`, {
      method: "POST",
      body: JSON.stringify({
        email,
        password,
        ...(mode === "signup" ? { name } : {}),
      }),
    });
    const current = await api<User>("/users/me", {}, result.token);
    client.clear();
    setToken(result.token);
    setUser(current);
    window.localStorage.setItem(
      "fhc-session",
      JSON.stringify({ token: result.token, user: current }),
    );
    return current;
  }
  function logout() {
    setToken(null);
    setUser(null);
    client.clear();
    window.localStorage.removeItem("fhc-session");
  }
  return (
    <QueryClientProvider client={client}>
      <Context.Provider value={{ user, token, ready, authenticate, logout }}>
        {children}
      </Context.Provider>
    </QueryClientProvider>
  );
}
export function useAuth() {
  const value = useContext(Context);
  if (!value) throw new Error("AuthProvider is required");
  return value;
}
