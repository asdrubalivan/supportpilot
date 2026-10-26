"""HTTP API. Run with: uv run uvicorn supportpilot.api:app --reload"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from supportpilot.agent import AgentResult, answer

app = FastAPI(title="SupportPilot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_methods=["POST"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    message: str
    # Fixed in slice 1; real auth will replace this with the authenticated customer.
    customer_id: int


@app.post("/chat")
async def chat(request: ChatRequest) -> AgentResult:
    return await answer(request.message, request.customer_id)
