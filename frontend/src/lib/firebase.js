import { initializeApp, getApps, getApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

function sanitizeEnv(value) {
  if (typeof value !== "string") return "";
  const trimmed = value.trim();
  // Strip accidental surrounding quotes if copied from .env into Vercel dashboard
  if (
    (trimmed.startsWith('"') && trimmed.endsWith('"')) ||
    (trimmed.startsWith("'") && trimmed.endsWith("'"))
  ) {
    return trimmed.slice(1, -1).trim();
  }
  return trimmed;
}

export const firebaseConfig = {
  apiKey: sanitizeEnv(import.meta.env.VITE_FIREBASE_API_KEY),
  authDomain: sanitizeEnv(import.meta.env.VITE_FIREBASE_AUTH_DOMAIN),
  projectId: sanitizeEnv(import.meta.env.VITE_FIREBASE_PROJECT_ID),
  storageBucket: sanitizeEnv(import.meta.env.VITE_FIREBASE_STORAGE_BUCKET),
  messagingSenderId: sanitizeEnv(import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID),
  appId: sanitizeEnv(import.meta.env.VITE_FIREBASE_APP_ID),
  measurementId: sanitizeEnv(import.meta.env.VITE_FIREBASE_MEASUREMENT_ID),
};

export const DEV_MODE = import.meta.env.VITE_DEV_MODE === "true";

function checkMissingKeys(config) {
  const missing = [];
  if (!config.apiKey || config.apiKey === "undefined" || config.apiKey === "null") {
    missing.push("VITE_FIREBASE_API_KEY");
  }
  if (!config.authDomain || config.authDomain === "undefined" || config.authDomain === "null") {
    missing.push("VITE_FIREBASE_AUTH_DOMAIN");
  }
  if (!config.projectId || config.projectId === "undefined" || config.projectId === "null") {
    missing.push("VITE_FIREBASE_PROJECT_ID");
  }
  if (!config.appId || config.appId === "undefined" || config.appId === "null") {
    missing.push("VITE_FIREBASE_APP_ID");
  }
  return missing;
}

export const missingFirebaseKeys = checkMissingKeys(firebaseConfig);
export const isFirebaseConfigured = missingFirebaseKeys.length === 0;

let firebaseApp = null;
let auth = null;
let firebaseInitError = null;

if (!DEV_MODE) {
  if (!isFirebaseConfigured) {
    const errorMsg = `Firebase is not configured. Missing required environment variable(s): ${missingFirebaseKeys.join(
      ", "
    )}. Please configure these in your Vercel project settings and trigger a redeploy.`;
    console.warn(`[Firebase] ${errorMsg}`);
    firebaseInitError = new Error(errorMsg);
  } else {
    try {
      const activeApps = getApps();
      firebaseApp = activeApps.length > 0 ? getApp() : initializeApp(firebaseConfig);
      auth = getAuth(firebaseApp);
    } catch (err) {
      console.error("[Firebase] Initialization error:", err);
      firebaseInitError = err;
      firebaseApp = null;
      auth = null;
    }
  }
}

export const googleProvider = new GoogleAuthProvider();
export { firebaseApp, auth, firebaseInitError };
