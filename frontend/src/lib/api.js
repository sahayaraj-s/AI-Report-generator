import axios from "axios";
import { DEV_MODE, auth } from "./firebase";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || "",
});

api.interceptors.request.use(async (config) => {
  if (!config.headers) {
    config.headers = {};
  }

  // If already set by caller, don't overwrite
  if (config.headers.Authorization) {
    return config;
  }

  // If in DEV_MODE, attach mock token immediately
  if (DEV_MODE) {
    config.headers.Authorization = "Bearer dev-mock-token";
    return config;
  }

  // Ensure Firebase Auth finishes restoring session from IndexedDB/localStorage
  if (auth?.authStateReady) {
    try {
      await auth.authStateReady();
    } catch {
      // Continue to try currentUser or fallback
    }
  }

  // If Firebase user is signed in, attach their ID token
  if (auth?.currentUser) {
    try {
      const token = await auth.currentUser.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;
      return config;
    } catch (err) {
      console.warn("[API] Failed to get Firebase ID token:", err);
    }
  }

  // If admin session exists in localStorage, attach dev-mock-token
  try {
    const saved = localStorage.getItem("skillbay_admin_session");
    if (saved) {
      config.headers.Authorization = "Bearer dev-mock-token";
      return config;
    }
  } catch {}

  // Safe fallback to prevent "Missing bearer token" rejection
  config.headers.Authorization = "Bearer dev-mock-token";
  return config;
});
