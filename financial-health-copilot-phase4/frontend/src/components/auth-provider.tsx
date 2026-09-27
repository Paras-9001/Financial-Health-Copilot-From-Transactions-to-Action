"use client";
import { createContext, useContext, useState, type ReactNode } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { api, type User } from "@/lib/api";

type Auth = {
  user: User | null;
  token: string | null;
  authenticate: (
    mode: "login" | "signup",
    email: string,
    password: string,
    name?: string,
  ) => Promise<void>;
  logout: () => void;
};
const Context = createContext<Auth | null>(null);
export function AuthProvider({ children }: { children: ReactNode }) {
  const [client] = useState(() => new QueryClient());
  const [user, setUser] = useState<User | null>(null);
  const [token, setToken] = useState<string | null>(null);
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
  }
  function logout() {
    setToken(null);
    setUser(null);
    client.clear();
  }
  return (
    <QueryClientProvider client={client}>
      <Context.Provider value={{ user, token, authenticate, logout }}>
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
