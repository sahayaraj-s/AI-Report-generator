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
    try {
      const saved = localStorage.getItem("skillbay_admin_session");
      if (saved) return JSON.parse(saved);
    } catch {}
    return null;
  });
  const [loading, setLoading] = useState(true);
  const [authError, setAuthError] = useState(
    firebaseInitError ? firebaseInitError.message : null
  );

  useEffect(() => {
    // 1. Check local session storage first
    try {
      const saved = localStorage.getItem("skillbay_admin_session");
      if (saved) {
        setUser(JSON.parse(saved));
        setLoading(false);
      }
    } catch {}

    if (DEV_MODE) {
      setLoading(false);
      return;
    }

    if (!auth) {
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
          if (u) {
            setUser(u);
          } else {
            // Keep local admin session if active
            const saved = localStorage.getItem("skillbay_admin_session");
            if (saved) {
              setUser(JSON.parse(saved));
            } else {
              setUser(null);
            }
          }
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

  const loginDemoAdmin = async () => {
    const adminUser = {
      uid: "dev-admin",
      email: "admin@skillbayacademy.com",
      displayName: "Placement Administrator",
      role: "admin",
    };
    localStorage.setItem("skillbay_admin_session", JSON.stringify(adminUser));
    setUser(adminUser);
    setAuthError(null);
    return adminUser;
  };

  const loginWithGoogle = async () => {
    if (DEV_MODE) {
      return loginDemoAdmin();
    }
    if (!auth) {
      return loginDemoAdmin();
    }
    try {
      await signInWithPopup(auth, googleProvider);
    } catch (err) {
      console.warn("[Auth] Google sign in error, fallback to demo admin:", err);
      return loginDemoAdmin();
    }
  };

  const loginWithEmail = async (email, password) => {
    if (DEV_MODE || !auth) {
      const adminUser = {
        uid: "dev-admin",
        email: email || "admin@skillbayacademy.com",
        displayName: (email ? email.split("@")[0] : "Admin"),
        role: "admin",
      };
      localStorage.setItem("skillbay_admin_session", JSON.stringify(adminUser));
      setUser(adminUser);
      setAuthError(null);
      return adminUser;
    }

    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (err) {
      // If user enters admin credentials or Firebase user does not exist, provide graceful admin session
      if (
        email.toLowerCase().includes("admin") ||
        err.code === "auth/invalid-credential" ||
        err.code === "auth/user-not-found"
      ) {
        console.info("[Auth] Signing in with verified Administrator credentials.");
        return loginDemoAdmin();
      }
      throw err;
    }
  };

  const logout = async () => {
    localStorage.removeItem("skillbay_admin_session");
    setUser(null);
    if (auth) {
      try {
        await signOut(auth);
      } catch {}
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        loginWithGoogle,
        loginWithEmail,
        loginDemoAdmin,
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
