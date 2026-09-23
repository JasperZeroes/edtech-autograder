import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from "react";

import {
  apiRequest,
  clearTokens,
  getAccessToken,
  loginRequest,
  setTokens,
} from "../api/client";

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(Boolean(getAccessToken()));

  const loadCurrentUser = useCallback(async () => {
    if (!getAccessToken()) {
      setUser(null);
      setLoading(false);
      return null;
    }

    try {
      const currentUser = await apiRequest("/auth/me");
      setUser(currentUser);
      return currentUser;
    } catch {
      clearTokens();
      setUser(null);
      return null;
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadCurrentUser();
  }, [loadCurrentUser]);

  const login = useCallback(async (email, password) => {
    const tokens = await loginRequest(email, password);
    setTokens(tokens);

    try {
      const currentUser = await apiRequest("/auth/me");
      setUser(currentUser);
      return currentUser;
    } catch (error) {
      clearTokens();
      throw error;
    }
  }, []);

  const register = useCallback(async (form) => {
    return apiRequest("/auth/register", {
      method: "POST",
      authenticated: false,
      body: {
        full_name: form.fullName,
        email: form.email,
        password: form.password,
        role: form.role,
      },
    });
  }, []);

  const logout = useCallback(() => {
    clearTokens();
    setUser(null);
  }, []);

  const value = useMemo(
    () => ({
      user,
      loading,
      isAuthenticated: Boolean(user),
      login,
      register,
      logout,
      refreshUser: loadCurrentUser,
    }),
    [user, loading, login, register, logout, loadCurrentUser],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const context = useContext(AuthContext);

  if (!context) {
    throw new Error("useAuth must be used inside AuthProvider.");
  }

  return context;
}
