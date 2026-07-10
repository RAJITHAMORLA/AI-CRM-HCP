"""
LangGraph AI Agent for the HCP Log Interaction chat assistant.

Role of the LangGraph agent
----------------------------
This agent sits behind the "AI Assistant" chat panel on the Log HCP
Interaction screen. A field representative can describe an interaction
with a Healthcare Professional (HCP) in free text (e.g. "Met Dr. Smith,
discussed Product X efficacy, positive sentiment, shared brochure") instead
of filling out the structured form. The agent's job is to:

  1. Understand what the rep is asking for (log a new interaction, correct
     an existing one, or look something up).
  2. Extract structured fields from unstructured text using the LLM
     (HCP name, interaction type, date/time, topics, sentiment, follow-up).
  3. Decide which "tool" to call to actually perform the action (write to
     the database, search history, etc.) and call it with the right
     arguments.
  4. Reply to the rep in plain language, confirming what was done.

It is implemented as a small LangGraph `StateGraph` with two nodes:
  - "agent": calls the Groq-hosted LLM (bound to the tool definitions)
  - "tools": executes whichever tool(s) the LLM asked for

The graph loops agent -> tools -> agent until the LLM responds without
requesting another tool call, at which point the graph ends and the final
message is returned to the frontend.
"""

import os
from datetime import datetime
from typing import Annotated, Optional, Sequence, TypedDict

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langgraph.graph import StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from database import SessionLocal
from models import Interaction

load_dotenv()

GROQ_API_KEY = os.getenv("GROQ_API_KEY")
# Primary model per assignment spec. llama-3.3-70b-versatile can be swapped
# in via env var for higher-quality extraction if needed.
GROQ_MODEL = os.getenv("GROQ_MODEL", "gemma2-9b-it")

llm = ChatGroq(
    api_key=GROQ_API_KEY,
    model=GROQ_MODEL,
    temperature=0.2,
)


# ---------------------------------------------------------------------------
# Tools
# Each tool is a discrete, sales-related capability the agent can invoke.
# Tools talk directly to the same SQLAlchemy models used by the REST CRUD
# endpoints in routes.py, so data logged via chat and data logged via the
# structured form live in the same table and stay consistent.
# ---------------------------------------------------------------------------

def _db():
    return SessionLocal()


@tool
def log_interaction(
    hcp_name: str,
    interaction_type: str,
    topics: str,
    sentiment: str = "Neutral",
    followup: str = "",
    interaction_date: Optional[str] = None,
    interaction_time: Optional[str] = None,
) -> str:
    """Log a brand-new HCP interaction to the CRM database.

    Call this once you have extracted enough detail from the rep's message:
    who the HCP is, the interaction type (Visit, Meeting, Call, or Email),
    what topics were discussed, the HCP's observed sentiment (Positive,
    Neutral, or Negative), and any follow-up actions/commitments. If the
    rep did not mention a date or time, omit them and today's date/time
    will be used automatically.
    """
    db = _db()
    try:
        now = datetime.now()
        interaction = Interaction(
            hcp_name=hcp_name,
            interaction_type=interaction_type,
            interaction_date=interaction_date or now.strftime("%Y-%m-%d"),
            interaction_time=interaction_time or now.strftime("%H:%M"),
            topics=topics,
            sentiment=sentiment,
            followup=followup,
        )
        db.add(interaction)
        db.commit()
        db.refresh(interaction)
        return (
            f"Interaction logged successfully (id={interaction.id}) for "
            f"HCP '{hcp_name}' on {interaction.interaction_date}."
        )
    finally:
        db.close()


@tool
def edit_interaction(
    interaction_id: int,
    hcp_name: Optional[str] = None,
    interaction_type: Optional[str] = None,
    topics: Optional[str] = None,
    sentiment: Optional[str] = None,
    followup: Optional[str] = None,
    interaction_date: Optional[str] = None,
    interaction_time: Optional[str] = None,
) -> str:
    """Edit or correct a previously logged interaction, identified by its id.

    Only the fields you provide (non-null) are updated; every other field
    on the record is left untouched. If you don't know the interaction_id,
    call get_interaction_history or search_hcp_interactions first to find
    it, and confirm with the rep which record they mean before editing.
    """
    db = _db()
    try:
        interaction = (
            db.query(Interaction).filter(Interaction.id == interaction_id).first()
        )
        if not interaction:
            return f"No interaction found with id={interaction_id}."

        updates = {
            "hcp_name": hcp_name,
            "interaction_type": interaction_type,
            "topics": topics,
            "sentiment": sentiment,
            "followup": followup,
            "interaction_date": interaction_date,
            "interaction_time": interaction_time,
        }
        changed = []
        for field, value in updates.items():
            if value is not None:
                setattr(interaction, field, value)
                changed.append(field)

        db.commit()
        db.refresh(interaction)
        return (
            f"Interaction id={interaction_id} updated ({', '.join(changed) or 'no fields changed'})."
        )
    finally:
        db.close()


@tool
def get_interaction_history(hcp_name: str, limit: int = 5) -> str:
    """Retrieve the most recent logged interactions for a given HCP.

    Useful when the rep asks things like "what did we last discuss with
    Dr. Smith?" or before editing a record, to find its interaction_id.
    """
    db = _db()
    try:
        rows = (
            db.query(Interaction)
            .filter(Interaction.hcp_name.ilike(f"%{hcp_name}%"))
            .order_by(Interaction.id.desc())
            .limit(limit)
            .all()
        )
        if not rows:
            return f"No interactions found for '{hcp_name}'."

        return "\n".join(
            f"id={r.id} | {r.interaction_date} {r.interaction_time} | "
            f"{r.interaction_type} | sentiment={r.sentiment} | "
            f"topics={r.topics} | followup={r.followup}"
            for r in rows
        )
    finally:
        db.close()


@tool
def search_hcp_interactions(keyword: str, limit: int = 5) -> str:
    """Search all logged interactions by keyword in topics or follow-up notes.

    Useful for questions like "did anyone mention OncoBoost recently?" that
    aren't tied to a single HCP name.
    """
    db = _db()
    try:
        rows = (
            db.query(Interaction)
            .filter(
                (Interaction.topics.ilike(f"%{keyword}%"))
                | (Interaction.followup.ilike(f"%{keyword}%"))
            )
            .order_by(Interaction.id.desc())
            .limit(limit)
            .all()
        )
        if not rows:
            return f"No interactions matched keyword '{keyword}'."

        return "\n".join(
            f"id={r.id} | {r.hcp_name} | {r.interaction_date} | topics={r.topics}"
            for r in rows
        )
    finally:
        db.close()


@tool
def suggest_followup_actions(topics: str, sentiment: str = "Neutral") -> str:
    """Suggest 2-3 concrete next-step follow-up actions for a sales rep.

    Given the topics discussed with an HCP and their observed sentiment,
    return short, concrete suggestions (e.g. schedule a follow-up meeting,
    send a specific brochure, add to an advisory board list). This tool
    does not touch the database - it only proposes ideas for the rep, who
    can then ask you to log_interaction or edit_interaction with them.
    """
    prompt = (
        "You are a life-sciences CRM assistant. Given the topics discussed "
        f"with a healthcare professional: '{topics}' and their observed "
        f"sentiment '{sentiment}', suggest 2-3 short, concrete follow-up "
        "actions a pharma sales rep should take next. Reply as a short "
        "bullet list, no preamble."
    )
    response = llm.invoke([HumanMessage(content=prompt)])
    return response.content


TOOLS = [
    log_interaction,
    edit_interaction,
    get_interaction_history,
    search_hcp_interactions,
    suggest_followup_actions,
]

llm_with_tools = llm.bind_tools(TOOLS)

SYSTEM_PROMPT = SystemMessage(
    content=(
        "You are the AI assistant embedded in an AI-first CRM's 'Log HCP "
        "Interaction' screen for pharmaceutical field representatives. "
        "Reps describe, in free text, meetings/calls/visits/emails they "
        "had with Healthcare Professionals (HCPs). Your job:\n"
        "1. Understand the rep's message.\n"
        "2. Extract structured details where possible: HCP name, "
        "interaction type (Visit/Meeting/Call/Email), date, time, topics "
        "discussed, the HCP's observed sentiment (Positive/Neutral/"
        "Negative), and any follow-up actions/commitments.\n"
        "3. Call log_interaction to save new interactions, edit_interaction "
        "to correct/update existing ones, and the retrieval tools "
        "(get_interaction_history, search_hcp_interactions) when the rep "
        "is asking about past interactions rather than logging a new one.\n"
        "4. Use suggest_followup_actions when the rep wants ideas for next "
        "steps.\n"
        "Always confirm briefly, in plain language, what you did (or "
        "found) after calling a tool. Never invent HCP names, ids, or data "
        "that was not given to you or returned by a tool. If required "
        "details (like HCP name) are missing, ask a brief clarifying "
        "question instead of guessing."
    )
)


class AgentState(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]


def call_model(state: AgentState):
    messages = [SYSTEM_PROMPT] + list(state["messages"])
    response = llm_with_tools.invoke(messages)
    return {"messages": [response]}


tool_node = ToolNode(TOOLS)

graph_builder = StateGraph(AgentState)
graph_builder.add_node("agent", call_model)
graph_builder.add_node("tools", tool_node)
graph_builder.set_entry_point("agent")
graph_builder.add_conditional_edges("agent", tools_condition)
graph_builder.add_edge("tools", "agent")

agent_graph = graph_builder.compile()


def run_agent_chat(user_message: str) -> dict:
    """Entry point used by the POST /chat route.

    Runs the LangGraph agent for a single conversational turn and returns
    a dict with the assistant's natural-language reply, plus a flag telling
    the frontend whether a new interaction was created during this turn (so
    it knows to refresh the interaction history panel).
    """
    result = agent_graph.invoke({"messages": [HumanMessage(content=user_message)]})
    messages = result["messages"]

    interaction_created = any(
        call.get("name") == "log_interaction"
        for msg in messages
        for call in (getattr(msg, "tool_calls", None) or [])
    )

    final_message = messages[-1]
    reply = (
        final_message.content
        if isinstance(final_message.content, str)
        else str(final_message.content)
    )

    return {"reply": reply, "interaction_created": interaction_created}
