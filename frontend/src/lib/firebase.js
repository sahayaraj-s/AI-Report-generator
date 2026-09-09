import { initializeApp } from "firebase/app";
import { getAuth, GoogleAuthProvider } from "firebase/auth";

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
  storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
  messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
  appId: import.meta.env.VITE_FIREBASE_APP_ID,
  measurementId: import.meta.env.VITE_FIREBASE_MEASUREMENT_ID,
};

export const DEV_MODE = import.meta.env.VITE_DEV_MODE === "true";

// In DEV_MODE (no real Firebase project yet) we skip initializing the SDK
// entirely, since a blank config would throw. AuthContext handles the mock
// session in that case.
export const firebaseApp = DEV_MODE ? null : initializeApp(firebaseConfig);
export const auth = DEV_MODE ? null : getAuth(firebaseApp);
export const googleProvider = new GoogleAuthProvider();
