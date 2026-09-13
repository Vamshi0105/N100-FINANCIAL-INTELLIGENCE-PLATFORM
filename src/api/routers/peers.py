from fastapi import APIRouter

router = APIRouter()


@router.get("/peers")
def get_peers():
    return {"status": "ok", "message": "Peers API scaffold"}
