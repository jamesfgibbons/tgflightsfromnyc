from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse


router = APIRouter(prefix="/api/v5/routes", tags=["routes-v5-alias"])


def _pass(request: Request, to: str) -> RedirectResponse:
    qs = request.url.query
    dest = f"{to}{('?' + qs) if qs else ''}"
    return RedirectResponse(dest, status_code=307)


@router.get("/board")
async def v5_board(request: Request):
    return _pass(request, "/api/board/feed")


@router.get("/arcs")
async def v5_arcs(request: Request):
    # Map arcs to travel routes listing; UI can compute coordinates client-side
    return _pass(request, "/api/travel/routes_nyc")


@router.get("/pricing")
async def v5_pricing(request: Request):
    return _pass(request, "/api/travel/price_quotes_latest")


@router.get("/deals")
async def v5_deals(request: Request):
    return _pass(request, "/api/travel/cheapest_route")

