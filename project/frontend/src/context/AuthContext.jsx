import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import axios from 'axios';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  // Define logout early so fetchUser can reference it
  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    delete axios.defaults.headers.common['Authorization'];
    setUser(null);
  }, []);

  // fetchUser must be defined BEFORE the useEffect that calls it
  const fetchUser = useCallback(async () => {
    try {
      const storedUser = localStorage.getItem('auth_user');
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      }
    } catch (error) {
      console.error('Failed to fetch user', error);
      logout();
    } finally {
      setLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      axios.defaults.headers.common['Authorization'] = `Bearer ${token}`;
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [fetchUser]);

  const login = async (email, password) => {
    const mockUser = {
      id: 1,
      name: 'Admin User',
      email: email,
      role: 'Admin',
    };
    const mockToken = 'mock_jwt_token_12345';

    localStorage.setItem('auth_token', mockToken);
    localStorage.setItem('auth_user', JSON.stringify(mockUser));

    axios.defaults.headers.common['Authorization'] = `Bearer ${mockToken}`;
    setUser(mockUser);
    return true;
  };

  const googleLogin = async (credential) => {
    const mockUser = {
      id: 2,
      name: 'Google User',
      email: 'google@example.com',
      role: 'Viewer',
      avatar: 'https://ui-avatars.com/api/?name=Google+User',
    };
    const mockToken = 'mock_google_jwt_token_12345';

    localStorage.setItem('auth_token', mockToken);
    localStorage.setItem('auth_user', JSON.stringify(mockUser));

    axios.defaults.headers.common['Authorization'] = `Bearer ${mockToken}`;
    setUser(mockUser);
    return true;
  };

  return (
    <AuthContext.Provider value={{ user, login, googleLogin, logout, loading }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
