from __future__ import annotations
from fastapi import APIRouter, Depends

from app.auth import get_current_admin

router = APIRouter(prefix="/api/auth", tags=["auth"])


@router.get("/me")
def me(admin=Depends(get_current_admin)):
    return admin
