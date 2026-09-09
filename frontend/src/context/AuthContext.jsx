import { createContext, useContext, useEffect, useState } from "react";
import {
  GoogleAuthProvider,
  onAuthStateChanged,
  signInWithEmailAndPassword,
  signInWithPopup,
  signOut,
} from "firebase/auth";
import { DEV_MODE, auth, googleProvider } from "../lib/firebase";

const AuthContext = createContext(null);

const DEV_USER = {
  uid: "dev-admin",
  email: "admin@skillbayacademy.dev",
  displayName: "Admin (dev mode)",
};

export function AuthProvider({ children }) {
  const [user, setUser] = useState(DEV_MODE ? DEV_USER : null);
  const [loading, setLoading] = useState(!DEV_MODE);

  useEffect(() => {
    if (DEV_MODE) return;
    const unsub = onAuthStateChanged(auth, (u) => {
      setUser(u);
      setLoading(false);
    });
    return unsub;
  }, []);

  const loginWithGoogle = async () => {
    if (DEV_MODE) {
      setUser(DEV_USER);
      return;
    }
    await signInWithPopup(auth, googleProvider);
  };

  const loginWithEmail = async (email, password) => {
    if (DEV_MODE) {
      setUser({ ...DEV_USER, email });
      return;
    }
    await signInWithEmailAndPassword(auth, email, password);
  };

  const logout = async () => {
    if (DEV_MODE) {
      setUser(null);
      return;
    }
    await signOut(auth);
  };

  return (
    <AuthContext.Provider value={{ user, loading, loginWithGoogle, loginWithEmail, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
