# AI-First CRM — HCP Module: Log Interaction Screen

A "Log HCP Interaction" screen for pharma field reps that supports **two ways
of logging an interaction**:

1. A structured **form** (HCP name, type, date/time, topics, sentiment, follow-up).
2. A **conversational AI chat** ("Met Dr. Smith, discussed Product X efficacy,
   positive sentiment, shared brochure") powered by a **LangGraph agent**
   running a **Groq** LLM, which extracts the same structured fields and
   calls tools to save/query/edit data.

Both paths write to the same database table, so the interaction history
panel stays consistent regardless of which method was used.

## Tech Stack

| Layer      | Tech                                             |
|------------|---------------------------------------------------|
| Frontend   | React + Redux (Redux Toolkit) + MUI, Google Inter font |
| Backend    | Python, FastAPI                                   |
| AI Agent   | LangGraph                                          |
| LLM        | Groq — `gemma2-9b-it` (default; `llama-3.3-70b-versatile` selectable via env) |
| Database   | PostgreSQL (via SQLAlchemy — MySQL also works by changing `DATABASE_URL`) |

## Project Structure

```
AI-CRM-HCP/
├── backend/
│   ├── main.py         # FastAPI app entrypoint, CORS, router mount
│   ├── database.py     # SQLAlchemy engine/session (DATABASE_URL from .env)
│   ├── models.py       # Interaction ORM model
│   ├── schemas.py      # Pydantic request/response models (CRUD + Chat)
│   ├── routes.py       # REST CRUD (/interactions) + AI chat (/chat)
│   ├── ai_agent.py     # LangGraph agent + 5 tools, Groq LLM binding
│   ├── requirements.txt
│   └── .env            # DATABASE_URL, GROQ_API_KEY, GROQ_MODEL
└── frontend/
    ├── src/
    │   ├── pages/LogInteractionPage.jsx   # 3-column layout: form | AI chat | history
    │   ├── components/InteractionForm.jsx # structured form (CRUD, unchanged)
    │   ├── components/InteractionHistory.jsx
    │   ├── components/AIChat.jsx          # chat UI, calls POST /chat
    │   ├── redux/                         # Redux Toolkit store/slice
    │   └── services/api.js                # axios client (CRUD)
    └── package.json
```

## LangGraph AI Agent

`backend/ai_agent.py` implements the agent as a small LangGraph `StateGraph`
with two nodes:

- **agent** — calls the Groq LLM (bound to tool definitions) with the
  conversation history and a system prompt describing the CRM domain.
- **tools** — executes whichever tool(s) the LLM decided to call.

The graph loops `agent → tools → agent` (via `tools_condition`) until the LLM
responds without requesting another tool call; that final message is
returned to the frontend as `reply`.

### Tools (5)

| Tool | Purpose |
|------|---------|
| **`log_interaction`** | Extracts/receives HCP name, interaction type, topics, sentiment, follow-up (and defaults date/time to "now" if omitted) and inserts a new row into the `interactions` table — the same table the structured form writes to. |
| **`edit_interaction`** | Updates an existing interaction by `id`; only the fields explicitly provided are changed. |
| `get_interaction_history` | Fetches the most recent interactions for a given HCP name — used for context, or to find an `id` before editing. |
| `search_hcp_interactions` | Keyword search across topics/follow-up notes, for questions not tied to one HCP. |
| `suggest_followup_actions` | LLM-only tool (no DB write) that proposes 2–3 concrete next steps given topics + sentiment. |

`POST /chat` (`backend/routes.py`) accepts `{ "message": "..." }`, runs
`run_agent_chat()`, and returns `{ "reply": "...", "interaction_created": bool }`.
`interaction_created` is `True` whenever the agent invoked `log_interaction`
during that turn, so the frontend knows to refresh the history panel.

## Setup & Run

### 1. Database
Create a Postgres (or MySQL) database and set `DATABASE_URL` in
`backend/.env` (already pre-filled for local Postgres — adjust as needed).
Tables are auto-created on backend startup (`Base.metadata.create_all`).

### 2. Backend

```bash
cd backend
python -m venv venv
# Windows: venv\Scripts\activate   |   macOS/Linux: source venv/bin/activate
pip install -r requirements.txt
```

Edit `backend/.env`:

```
DATABASE_URL=postgresql://<user>:<password>@localhost:5432/ai_crm
GROQ_API_KEY=your_groq_api_key_here   # create one at https://console.groq.com
GROQ_MODEL=gemma2-9b-it               # or llama-3.3-70b-versatile
```

Run the API:

```bash
uvicorn main:app --reload --port 8000
```

- CRUD: `POST/GET http://localhost:8000/interactions`
- AI Chat: `POST http://localhost:8000/chat`

### 3. Frontend

```bash
cd frontend
npm install
npm run dev
```

Open the printed local URL (Vite default `http://localhost:5173`). The AI
chat panel talks to `http://localhost:8000/chat` by default.

## Notes

- The structured-form CRUD endpoints (`/interactions` GET/POST) and their
  UI components are unchanged — the AI chat is purely additive and shares
  the same database table.
- If `GROQ_API_KEY` is missing/invalid, `POST /chat` returns HTTP 502 with
  the underlying error message rather than silently failing.
