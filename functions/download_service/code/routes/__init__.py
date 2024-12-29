from code.routes.download import router as download_router

from fastapi import APIRouter


router = APIRouter()

router.include_router(download_router)
