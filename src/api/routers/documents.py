from fastapi import APIRouter

router = APIRouter()


@router.get("/documents")
def get_documents():
    return {"status": "ok", "message": "Documents API scaffold"}
