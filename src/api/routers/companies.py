from fastapi import APIRouter

router = APIRouter()


@router.get("/companies")
def get_companies():
    return {"status": "ok", "message": "Companies API scaffold"}
