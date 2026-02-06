from fastapi import APIRouter

from src.api.v1.peers.crud import create, read, update, delete

router = APIRouter(prefix="/peers", tags=["Peers"])

router.include_router(create.router)
router.include_router(read.router)
router.include_router(update.router)
router.include_router(delete.router)
