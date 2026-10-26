import axios from "axios";
import { DEV_MODE, auth } from "./firebase";

export const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || import.meta.env.VITE_API_BASE_URL || "",
});

api.interceptors.request.use(async (config) => {
  if (DEV_MODE) {
    if (!config.headers.Authorization) {
      config.headers.Authorization = "Bearer dev-mock-token";
    }
  } else if (auth?.currentUser) {
    try {
      const token = await auth.currentUser.getIdToken();
      config.headers.Authorization = `Bearer ${token}`;
    } catch (err) {
      console.warn("[API] Failed to get Firebase ID token:", err);
    }
  }
  return config;
});
