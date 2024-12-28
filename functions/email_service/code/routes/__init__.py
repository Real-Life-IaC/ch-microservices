from code.routes.mailing import router as mailing_router

from fastapi import APIRouter


router = APIRouter()

router.include_router(mailing_router)
