from fastapi import APIRouter

router = APIRouter()


@router.get("/sectors")
def get_sectors():
    return {"status": "ok", "message": "Sectors API scaffold"}
