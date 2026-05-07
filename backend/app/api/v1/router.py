from fastapi import APIRouter

from app.api.v1 import albums, auth, devices, drop, files, folders, health, invites, photos, receipts, shares, tags, trash

api_router = APIRouter()
api_router.include_router(albums.router, prefix="/albums", tags=["albums"])
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(invites.router, prefix="/invites", tags=["invites"])
api_router.include_router(devices.router, prefix="/devices", tags=["devices"])
api_router.include_router(drop.router, prefix="/drop", tags=["drop"])
api_router.include_router(files.router, prefix="/files", tags=["files"])
api_router.include_router(folders.router, prefix="/folders", tags=["folders"])
api_router.include_router(health.router, prefix="/health", tags=["health"])
api_router.include_router(photos.router, prefix="/photos", tags=["photos"])
api_router.include_router(receipts.router, prefix="/receipts", tags=["receipts"])
api_router.include_router(shares.router, prefix="/shares", tags=["shares"])
api_router.include_router(shares.public_router, prefix="/public-share", tags=["public-share"])
api_router.include_router(tags.router, prefix="/tags", tags=["tags"])
api_router.include_router(trash.router, prefix="/trash", tags=["trash"])
