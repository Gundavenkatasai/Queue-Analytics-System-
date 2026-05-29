import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const AuthContext = createContext();

export const useAuth = () => useContext(AuthContext);

// Decode a Google JWT token payload without any external library
function decodeGoogleJwt(token) {
  try {
    const base64Payload = token.split('.')[1];
    // Fix base64 padding
    const padded = base64Payload.replace(/-/g, '+').replace(/_/g, '/');
    const jsonPayload = decodeURIComponent(
      atob(padded)
        .split('')
        .map((c) => '%' + ('00' + c.charCodeAt(0).toString(16)).slice(-2))
        .join('')
    );
    return JSON.parse(jsonPayload);
  } catch (e) {
    console.error('Failed to decode Google JWT:', e);
    return null;
  }
}

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(null);

  const logout = useCallback(() => {
    localStorage.removeItem('auth_token');
    localStorage.removeItem('auth_user');
    setUser(null);
    setAuthError(null);
  }, []);

  const fetchUser = useCallback(async () => {
    try {
      const storedUser = localStorage.getItem('auth_user');
      if (storedUser) {
        setUser(JSON.parse(storedUser));
      }
    } catch (error) {
      console.error('Failed to restore user session', error);
      logout();
    } finally {
      setLoading(false);
    }
  }, [logout]);

  useEffect(() => {
    const token = localStorage.getItem('auth_token');
    if (token) {
      fetchUser();
    } else {
      setLoading(false);
    }
  }, [fetchUser]);

  // ─── Email/password REGISTER — calls Laravel backend, stores in MongoDB ───
  const register = async (name, email, password) => {
    setAuthError(null);
    try {
      const response = await fetch('http://localhost:8000/api/auth/register', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, email, password }),
        signal: AbortSignal.timeout(8000),
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        const userData = {
          id: data.user?.id,
          name: data.user?.name || name,
          email: data.user?.email || email,
          role: data.user?.role || 'Operator',
          avatar: `https://ui-avatars.com/api/?name=${encodeURIComponent(data.user?.name || name)}&background=6366f1&color=fff`,
        };
        localStorage.setItem('auth_token', data.token);
        localStorage.setItem('auth_user', JSON.stringify(userData));
        setUser(userData);
        return { success: true };
      }

      // Handle server-side error messages (409 conflict, 500, etc.)
      const errorMsg = data.message || 'Registration failed. Please try again.';
      setAuthError(errorMsg);
      return { success: false, error: errorMsg };

    } catch (err) {
      const isTimeout = err.name === 'TimeoutError' || err.name === 'AbortError';
      const errorMsg = isTimeout
        ? 'Server took too long to respond. Make sure Laravel is running: php artisan serve'
        : 'Cannot connect to server. Run: php artisan serve (in backend directory).';
      console.error('Register network error:', err.message);
      setAuthError(errorMsg);
      return { success: false, error: errorMsg };
    }
  };

  // ─── Email/password LOGIN — calls Laravel backend, verifies MongoDB record ──
  const login = async (email, password) => {
    setAuthError(null);
    try {
      const response = await fetch('http://localhost:8000/api/auth/login', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
        signal: AbortSignal.timeout(8000),
      });

      const data = await response.json();

      if (response.ok && data.status === 'success') {
        const userData = {
          id: data.user?.id,
          name: data.user?.name || email.split('@')[0],
          email: data.user?.email || email,
          role: data.user?.role || 'Operator',
          avatar: data.user?.picture || `https://ui-avatars.com/api/?name=${encodeURIComponent(data.user?.name || email)}&background=6366f1&color=fff`,
        };
        localStorage.setItem('auth_token', data.token);
        localStorage.setItem('auth_user', JSON.stringify(userData));
        setUser(userData);
        return { success: true };
      }

      // Handle 401 (wrong password / not found) or 500
      const errorMsg = data.message || 'Login failed. Please check your credentials.';
      setAuthError(errorMsg);
      return { success: false, error: errorMsg };

    } catch (err) {
      const isTimeout = err.name === 'TimeoutError' || err.name === 'AbortError';
      const errorMsg = isTimeout
        ? 'Server took too long to respond. Make sure Laravel is running: php artisan serve'
        : 'Cannot connect to server. Run: php artisan serve (in backend directory).';
      console.error('Login network error:', err.message);
      setAuthError(errorMsg);
      return { success: false, error: errorMsg };
    }
  };

  // ─── Google OAuth — decodes real JWT, syncs with MongoDB backend ────────────
  const googleLogin = async (credentialResponse) => {
    setAuthError(null);
    const token = credentialResponse?.credential;

    if (!token) {
      console.error('No credential token from Google');
      return false;
    }

    // Decode the real Google profile from the JWT
    const payload = decodeGoogleJwt(token);

    if (!payload) {
      console.error('Failed to decode Google token');
      return false;
    }

    const realUser = {
      id: payload.sub,        // Google's unique user ID
      name: payload.name,
      email: payload.email,
      role: 'Operator',
      avatar: payload.picture,
      google_id: payload.sub,
    };

    // Attempt to register/login the user in the backend (stores in MongoDB)
    try {
      const response = await fetch('http://localhost:8000/api/auth/google', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          google_id: payload.sub,
          name: payload.name,
          email: payload.email,
          picture: payload.picture,
        }),
      });

      if (response.ok) {
        const data = await response.json();
        if (data.user?.role) realUser.role = data.user.role;
        if (data.user?.id) realUser.id = data.user.id;
      }
    } catch (err) {
      // Backend unavailable — still allow login with decoded Google data
      console.warn('Could not sync Google user to backend:', err.message);
    }

    localStorage.setItem('auth_token', token);
    localStorage.setItem('auth_user', JSON.stringify(realUser));
    setUser(realUser);
    return true;
  };

  return (
    <AuthContext.Provider value={{ user, login, register, googleLogin, logout, loading, authError, setAuthError }}>
      {!loading && children}
    </AuthContext.Provider>
  );
};
