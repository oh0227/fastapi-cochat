from fastapi import APIRouter
from schemas import MessageBase
from rag.rag_module import run_rag_pipeline

router = APIRouter(
    prefix="/rag",
    tags=["rag"]
)

@router.post("/analyze")
async def analyze_message(message: MessageBase):
    result = run_rag_pipeline(message)
    return {"result": result}