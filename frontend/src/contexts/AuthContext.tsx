import React, { createContext, useContext, useEffect, useState } from 'react';
import { apiClient, UserInfo } from '@/lib/api';

interface AuthContextType {
  user: UserInfo | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  login: (data: { email: string; password: string }) => Promise<void>;
  register: (data: { email: string; password: string; full_name?: string }) => Promise<void>;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const AuthProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);

  // Initialize auth state on mount
  useEffect(() => {
    const initAuth = async () => {
      try {
        const storedUser = apiClient.getUserInfo();
        if (storedUser) {
          setUser(storedUser);
        }
      } finally {
        setIsLoading(false);
      }
    };

    initAuth();
  }, []);

  const login = async (data: { email: string; password: string }) => {
    setIsLoading(true);
    try {
      await apiClient.login(data);
      const userInfo = apiClient.getUserInfo();
      setUser(userInfo);
    } finally {
      setIsLoading(false);
    }
  };

  const register = async (data: { email: string; password: string; full_name?: string }) => {
    setIsLoading(true);
    try {
      // Register the user - this returns tokens and automatically logs them in
      await apiClient.register(data);
      const userInfo = apiClient.getUserInfo();
      setUser(userInfo);
    } finally {
      setIsLoading(false);
    }
  };

  const logout = async () => {
    setIsLoading(true);
    try {
      await apiClient.logout();
      setUser(null);
    } finally {
      setIsLoading(false);
    }
  };

  const isAuthenticated = !!user;

  return (
    <AuthContext.Provider
      value={{
        user,
        isAuthenticated,
        isLoading,
        login,
        register,
        logout,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (context === undefined) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

