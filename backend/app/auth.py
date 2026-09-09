"""
Auth dependency for protected routes.

Production path: verifies a Firebase ID token sent as
`Authorization: Bearer <token>` using the Firebase Admin SDK.

Local/dev path (DEV_MODE=true, the default until you wire up a real
Firebase project): skips verification and returns a fixed admin user, so
the whole app is runnable and testable with zero external accounts.
"""
from __future__ import annotations
import json

from fastapi import Header, HTTPException, status

from app.config import settings

_firebase_app = None


def _get_firebase_app():
    global _firebase_app
    if _firebase_app is None:
        import firebase_admin
        from firebase_admin import credentials

        cred_dict = json.loads(settings.firebase_service_account_json)
        cred = credentials.Certificate(cred_dict)
        _firebase_app = firebase_admin.initialize_app(cred)
    return _firebase_app


async def get_current_admin(authorization: str = Header(default=None)):
    if settings.dev_mode:
        return {"uid": "dev-admin", "email": "admin@skillbayacademy.dev", "name": "Admin (dev mode)"}

    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Missing bearer token")

    token = authorization.split(" ", 1)[1]
    try:
        from firebase_admin import auth as firebase_auth

        _get_firebase_app()
        decoded = firebase_auth.verify_id_token(token)
        return {
            "uid": decoded["uid"],
            "email": decoded.get("email"),
            "name": decoded.get("name", decoded.get("email")),
        }
    except Exception as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, f"Invalid token: {exc}")
