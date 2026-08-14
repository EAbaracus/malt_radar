from fastapi import APIRouter, HTTPException, Query, Request, Depends
from typing import Optional
from app.services.anonymous_catalog_service import AnonymousCatalogService
from app.security import limiter
from app.routers.db_api import check_db_api_enabled

router = APIRouter(
    prefix="/api/db/public",
    tags=["Public DB Catalog API"],
    dependencies=[Depends(check_db_api_enabled)]
)

def get_public_service() -> AnonymousCatalogService:
    return AnonymousCatalogService()

@router.get("/whiskies")
@limiter.limit("120/minute")
def get_whiskies(
    request: Request,
    limit: int = Query(50, ge=1, le=50),
    offset: int = Query(0, ge=0),
    q: Optional[str] = Query(None),
    filter: Optional[str] = Query(None),
    service: AnonymousCatalogService = Depends(get_public_service)
):
    try:
        return service.get_whiskies(limit, offset, q, filter)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database or artifact file missing")

@router.get("/whiskies/{whisky_id}")
@limiter.limit("120/minute")
def get_whisky(
    request: Request,
    whisky_id: str,
    service: AnonymousCatalogService = Depends(get_public_service)
):
    try:
        result = service.get_whisky(whisky_id)
        if not result:
            raise HTTPException(status_code=404, detail="Whisky not found in public catalog")
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")

@router.get("/whiskies/{whisky_id}/flavor-profile")
@limiter.limit("120/minute")
def get_flavor_profile(
    request: Request,
    whisky_id: str,
    service: AnonymousCatalogService = Depends(get_public_service)
):
    try:
        result = service.get_flavor_profile(whisky_id)
        if not result:
            raise HTTPException(status_code=404, detail="Flavor profile not found in public catalog")
        return result
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")

@router.get("/search")
@limiter.limit("120/minute")
def search(
    request: Request,
    q: str = Query(...),
    service: AnonymousCatalogService = Depends(get_public_service)
):
    if not q or len(q.strip()) < 2:
        raise HTTPException(status_code=400, detail="Search query must be at least 2 characters")
    try:
        return service.search(q)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")

@router.get("/distilleries")
@limiter.limit("120/minute")
def get_distilleries(
    request: Request,
    limit: int = Query(50, ge=1, le=50),
    offset: int = Query(0, ge=0),
    service: AnonymousCatalogService = Depends(get_public_service)
):
    try:
        return service.get_distilleries(limit, offset)
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")

@router.get("/filters")
@limiter.limit("120/minute")
def get_filters(
    request: Request,
    service: AnonymousCatalogService = Depends(get_public_service)
):
    try:
        return service.get_filters()
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="Database file missing")
