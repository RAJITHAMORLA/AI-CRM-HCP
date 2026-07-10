import traceback
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models import Interaction
from schemas import InteractionCreate, ChatRequest, ChatResponse
from ai_agent import run_agent_chat

router = APIRouter()


@router.post("/interactions")
def create_interaction(data: InteractionCreate, db: Session = Depends(get_db)):
    interaction = Interaction(
        hcp_name=data.hcp_name,
        interaction_type=data.interaction_type,
        interaction_date=data.interaction_date,
        interaction_time=data.interaction_time,
        topics=data.topics,
        sentiment=data.sentiment,
        followup=data.followup,
    )

    db.add(interaction)
    db.commit()
    db.refresh(interaction)

    return {
        "message": "Interaction Saved Successfully",
        "id": interaction.id
    }


@router.get("/interactions")
def get_interactions(db: Session = Depends(get_db)):
    return db.query(Interaction).all()


# --- AI Chat (LangGraph + Groq) --------------------------------------------
# The frontend's AIChat component posts free-text messages here. The
# LangGraph agent (backend/ai_agent.py) decides which tool(s) to call
# (log_interaction, edit_interaction, get_interaction_history,
# search_hcp_interactions, suggest_followup_actions) and returns a plain
# language reply plus a flag telling the frontend whether a new
# interaction was created, so it knows to refresh the history panel.

@router.post("/chat", response_model=ChatResponse)
def chat_with_agent(payload: ChatRequest):
    if not payload.message or not payload.message.strip():
        raise HTTPException(status_code=400, detail="message must not be empty")

    try:
        result = run_agent_chat(payload.message)
    except Exception as exc:
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(exc))

    return ChatResponse(**result)