from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse

alias_router = APIRouter()


@alias_router.get("/api/cheapest_route")
def cheapest_route_alias(request: Request):
    qs = str(request.query_params) or ""
    dest = "/api/travel/cheapest_route"
    if qs:
        dest = f"{dest}?{qs}"
    return RedirectResponse(url=dest, status_code=307)

