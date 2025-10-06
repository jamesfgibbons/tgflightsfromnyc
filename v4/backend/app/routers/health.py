from fastapi import APIRouter

router = APIRouter()


@router.get("/api/healthz")
async def healthz():
    return {"status": "healthy", "version": "4.0.0"}

