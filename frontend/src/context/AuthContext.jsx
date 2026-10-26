import { createContext, useContext, useEffect, useState } from "react";
import {
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
} from "firebase/auth";
import {
  DEV_MODE,
  auth,
  googleProvider,
  isFirebaseConfigured,
  firebaseInitError,
  missingFirebaseKeys,
} from "../lib/firebase";

const AuthContext = createContext(null);

const DEV_USER = {
  uid: "dev-admin",
  email: "admin@skillbayacademy.dev",
  displayName: "Admin (dev mode)",
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(() => {
    if (DEV_MODE) {
      try {
        const saved = localStorage.getItem("skillbay_admin_session");
        return saved ? JSON.parse(saved) : null;
      } catch {
        return null;
      }
    }
    return null;
  });
  const [loading, setLoading] = useState(!DEV_MODE);
  const [authError, setAuthError] = useState(
    firebaseInitError ? firebaseInitError.message : null
  );

  useEffect(() => {
    if (DEV_MODE) {
      try {
        const saved = localStorage.getItem("skillbay_admin_session");
        if (saved) {
          setUser(JSON.parse(saved));
        }
      } catch {
        setUser(null);
      }
      setLoading(false);
      return;
    }

    if (!auth) {
      // Firebase is not initialized (missing environment variables or initialization failed)
      setLoading(false);
      if (firebaseInitError) {
        setAuthError(firebaseInitError.message);
      }
      return;
    }

    try {
      const unsub = onAuthStateChanged(
        auth,
        (u) => {
          setUser(u);
          setLoading(false);
          setAuthError(null);
        },
        (err) => {
          console.error("[Auth] onAuthStateChanged error:", err);
          setAuthError(err.message || "Firebase Auth service error");
          setLoading(false);
        }
      );
      return () => {
        if (typeof unsub === "function") {
          unsub();
        }
      };
    } catch (err) {
      console.error("[Auth] Listener registration error:", err);
      setAuthError(err.message || "Failed to initialize Firebase Auth listener");
      setLoading(false);
    }
  }, []);

  const loginWithGoogle = async () => {
    if (DEV_MODE) {
      const adminUser = {
        uid: "dev-admin",
        email: "admin@skillbayacademy.com",
        displayName: "Administrator",
        role: "admin",
      };
      localStorage.setItem("skillbay_admin_session", JSON.stringify(adminUser));
      setUser(adminUser);
      return adminUser;
    }
    if (!auth) {
      const msg =
        firebaseInitError?.message ||
        "Firebase Authentication is not configured. Please ensure VITE_FIREBASE_* environment variables are set in your Vercel settings and redeploy.";
      throw new Error(msg);
    }
    await signInWithPopup(auth, googleProvider);
  };

  const loginWithEmail = async (email, password) => {
    if (DEV_MODE) {
      const adminUser = {
        uid: "dev-admin",
        email: email || "admin@skillbayacademy.com",
        displayName: (email ? email.split("@")[0] : "Admin"),
        role: "admin",
      };
      localStorage.setItem("skillbay_admin_session", JSON.stringify(adminUser));
      setUser(adminUser);
      return adminUser;
    }
    if (!auth) {
      const msg =
        firebaseInitError?.message ||
        "Firebase Authentication is not configured. Please ensure VITE_FIREBASE_* environment variables are set in your Vercel settings and redeploy.";
      throw new Error(msg);
    }
    await signInWithEmailAndPassword(auth, email, password);
  };

  const logout = async () => {
    if (DEV_MODE) {
      localStorage.removeItem("skillbay_admin_session");
      setUser(null);
      return;
    }
    if (!auth) {
      localStorage.removeItem("skillbay_admin_session");
      setUser(null);
      return;
    }
    await signOut(auth);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        loginWithGoogle,
        loginWithEmail,
        logout,
        isFirebaseConfigured,
        authError,
        missingFirebaseKeys,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
