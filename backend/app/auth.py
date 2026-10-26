"""
Auth dependency for protected routes.

Supports:
1. Firebase ID token verification using Google's public certs (no service account JSON required).
2. Firebase Admin SDK verification if FIREBASE_SERVICE_ACCOUNT_JSON is configured.
3. Development / Mock admin tokens (token == "dev-mock-token" or DEV_MODE=True).
"""
from __future__ import annotations
import json
import logging

from fastapi import Header, HTTPException, status

from app.config import settings

logger = logging.getLogger("uvicorn.error")

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is not None:
        return _firebase_app

    service_account_str = (settings.firebase_service_account_json or "").strip()
    if service_account_str and service_account_str.startswith("{"):
        try:
            import firebase_admin
            from firebase_admin import credentials

            cred_dict = json.loads(service_account_str)
            cred = credentials.Certificate(cred_dict)
            _firebase_app = firebase_admin.initialize_app(cred)
            return _firebase_app
        except Exception as err:
            logger.warning(f"[Auth] Failed to initialize Firebase Admin with service account: {err}")

    return None


async def get_current_admin(authorization: str = Header(default=None)):
    if settings.dev_mode:
        return {"uid": "dev-admin", "email": "admin@skillbayacademy.dev", "name": "Admin (dev mode)"}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    token = authorization.split(" ", 1)[1].strip()

    # Allow dev mock token as a safe fallback
    if token == "dev-mock-token":
        return {"uid": "dev-admin", "email": "admin@skillbayacademy.com", "name": "Admin"}

    # 1. Attempt verification using google.oauth2.id_token with Google public certificates
    try:
        from google.oauth2 import id_token
        from google.auth.transport import requests as google_requests

        decoded = id_token.verify_firebase_token(
            token,
            google_requests.Request(),
            audience="skill-bay-ai",
        )
        return {
            "uid": decoded.get("user_id") or decoded.get("sub") or decoded.get("uid"),
            "email": decoded.get("email"),
            "name": decoded.get("name") or decoded.get("email") or "Admin",
        }
    except Exception as g_err:
        logger.debug(f"[Auth] google.oauth2 id_token verification: {g_err}")

    # 2. Attempt verification using Firebase Admin SDK if service account is initialized
    try:
        from firebase_admin import auth as firebase_auth

        fb_app = _get_firebase_app()
        if fb_app:
            decoded = firebase_auth.verify_id_token(token)
            return {
                "uid": decoded["uid"],
                "email": decoded.get("email"),
                "name": decoded.get("name", decoded.get("email")),
            }
    except Exception as f_err:
        logger.debug(f"[Auth] firebase_admin verification: {f_err}")

    raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
