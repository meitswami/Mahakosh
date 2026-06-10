"use client";

import { useAuthStore } from "@/store/auth-store";
import { apiFetch } from "@/lib/api";
import type { User } from "@/types";

interface LoginCredentials {
  email: string;
  password: string;
  tenant_slug?: string;
}

interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
}

export function useAuth() {
  const { user, isAuthenticated, setAuth, clearAuth } = useAuthStore();

  const login = async (credentials: LoginCredentials) => {
    const tokens = await apiFetch<TokenResponse>("/auth/login", {
      method: "POST",
      body: JSON.stringify(credentials),
    });

    const profile = await apiFetch<User>("/auth/me", {
      headers: { Authorization: `Bearer ${tokens.access_token}` },
    });

    setAuth(profile, tokens.access_token);
    return profile;
  };

  const logout = () => {
    clearAuth();
  };

  return { user, isAuthenticated, login, logout };
}
