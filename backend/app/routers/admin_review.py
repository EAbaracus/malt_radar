import os
from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from app.models.schemas import (
    ReviewQueueItem, ReviewQueueResponse, ReviewDetailResponse, 
    AllowedAction, ReviewActionRequest, ReviewActionResponse
)
from app.services.review_query_service import ReviewQueryService

router = APIRouter(prefix="/admin/review", tags=["Admin Review"])

def get_query_service():
    return ReviewQueryService()

def check_feature_flag():
    enabled = os.getenv("ADMIN_REVIEW_API_ENABLED", "false").lower() == "true"
    if not enabled:
        raise HTTPException(status_code=403, detail="Admin Review API is currently disabled.")

@router.get("/queue", response_model=ReviewQueueResponse, dependencies=[Depends(check_feature_flag)])
async def get_queue(
    status: Optional[str] = None,
    source_table: Optional[str] = None,
    limit: int = 50,
    offset: int = 0,
    service: ReviewQueryService = Depends(get_query_service)
):
    rows = service.get_unified_queue(status, source_table, limit, offset)
    items = []
    for r in rows:
        items.append(ReviewQueueItem(**r))
        
    return ReviewQueueResponse(items=items, total=len(items), limit=limit, offset=offset)

@router.get("/item", response_model=ReviewDetailResponse, dependencies=[Depends(check_feature_flag)])
async def get_item(
    source_table: str,
    source_record_key: str,
    service: ReviewQueryService = Depends(get_query_service)
):
    item = service.get_item_details(source_table, source_record_key)
    if not item:
        raise HTTPException(status_code=404, detail="Item not found")
        
    status = item.get("approval_status", "pending_review")
    actions = service.get_allowed_actions(status)
    
    return ReviewDetailResponse(
        source_table=source_table,
        source_record_key=source_record_key,
        item=item,
        allowed_actions=[AllowedAction(**a) for a in actions],
        related_conflicts=[],
        raw_payload=None
    )

@router.get("/actions", response_model=List[AllowedAction], dependencies=[Depends(check_feature_flag)])
async def get_actions(
    current_status: str,
    service: ReviewQueryService = Depends(get_query_service)
):
    actions = service.get_allowed_actions(current_status)
    return [AllowedAction(**a) for a in actions]

@router.post("/action", response_model=ReviewActionResponse, dependencies=[Depends(check_feature_flag)])
async def post_action(
    req: ReviewActionRequest,
    service: ReviewQueryService = Depends(get_query_service)
):
    if not req.dry_run:
        write_enabled = os.getenv("ADMIN_REVIEW_WRITE_ENABLED", "false").lower() == "true"
        if not write_enabled:
            raise HTTPException(status_code=400, detail="Real production writes are blocked. ADMIN_REVIEW_WRITE_ENABLED is false.")
        
    if req.action_type == "PROMOTE" or req.target_status == "promoted":
        promo_enabled = os.getenv("ADMIN_REVIEW_PROMOTION_ENABLED", "false").lower() == "true"
        if not promo_enabled:
            raise HTTPException(status_code=400, detail="Promotion action is not allowed. ADMIN_REVIEW_PROMOTION_ENABLED is false.")
        
    item = service.get_item_details(req.source_table, req.source_record_key)
    if not item:
        raise HTTPException(status_code=404, detail="Source record not found")
        
    status = item.get("approval_status", "pending_review")
    actions = service.get_allowed_actions(status)
    
    allowed = False
    requires_note = False
    for a in actions:
        if a["action_type"] == req.action_type and a["to_status"] == req.target_status:
            allowed = True
            requires_note = bool(a["requires_note"])
            break
            
    if not allowed:
        raise HTTPException(status_code=400, detail=f"Action {req.action_type} to {req.target_status} not allowed from {status}.")
        
    if requires_note and not req.reviewer_note:
        raise HTTPException(status_code=400, detail="Reviewer note is required for this action.")

    if not req.dry_run:
        try:
            service.execute_action(
                source_table=req.source_table,
                source_record_key=req.source_record_key,
                target_status=req.target_status,
                action_type=req.action_type,
                reviewer=req.reviewer,
                reviewer_note=req.reviewer_note,
                previous_status=status
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
        
    return ReviewActionResponse(
        success=True,
        message=f"Action successful for {req.action_type}" if not req.dry_run else f"Dry run successful for {req.action_type}",
        dry_run=req.dry_run,
        action_logged=not req.dry_run
    )
