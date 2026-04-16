from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
def health():
    return {"ok": True}


@router.get("/ready")
def ready():
    """Same contract as ``GET /health`` — reserved for orchestrators that prefer ``/ready``."""
    return {"ok": True}