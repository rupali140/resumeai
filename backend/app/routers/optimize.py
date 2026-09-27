from fastapi import APIRouter, Depends, HTTPException

from .. import models, schemas, security
from ..services.ai_engine import optimize_bullet

router = APIRouter(prefix="/api/optimize", tags=["optimize"])


@router.post("/bullet", response_model=schemas.BulletOptimizeResponse)
def optimize_bullet_endpoint(
    payload: schemas.BulletOptimizeRequest,
    current_user: models.User = Depends(security.get_current_user),
):
    if not payload.bullet.strip():
        raise HTTPException(status_code=400, detail="Bullet text cannot be empty.")
    result = optimize_bullet(payload.bullet)
    return schemas.BulletOptimizeResponse(**result)
