
from pydantic import BaseModel


class InteractionCreate(BaseModel):
    hcp_name: str
    interaction_type: str
    interaction_date: str
    interaction_time: str
    topics: str
    sentiment: str
    followup: str


class InteractionResponse(InteractionCreate):
    id: int

    class Config:
        from_attributes = True


# --- AI Chat (LangGraph + Groq) -------------------------------------------

class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    reply: str
    interaction_created: bool = False