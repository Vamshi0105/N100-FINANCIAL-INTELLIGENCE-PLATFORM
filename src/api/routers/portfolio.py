from fastapi import APIRouter

router = APIRouter()


@router.get("/portfolio")
def get_portfolio():
    return {"status": "ok", "message": "Portfolio API scaffold"}
