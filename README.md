# AI-First CRM HCP Module

## Project Overview

This project is an AI-First Customer Relationship Management (CRM) Healthcare Professional (HCP) Module developed as part of the AIVOA.AI Full Stack Developer assignment.

The application enables pharmaceutical sales representatives to record and manage Healthcare Professional interactions using both a structured form and an AI-powered chat assistant.

The AI assistant uses LangGraph and Groq LLM to understand natural language, extract interaction details, and assist users in logging interactions efficiently.

---

## Features

### Manual Interaction Logging
- Log HCP interactions using a structured form
- Save interaction details to PostgreSQL
- View interaction history

### AI Chat Assistant
- Log interactions using natural language
- AI understands user messages
- AI provides intelligent responses
- AI assists in interaction management

### LangGraph Tools

The project demonstrates the following LangGraph tools:

- Log Interaction
- Edit Interaction
- Get Interaction History
- Search HCP Interactions
- Suggest Follow-up Actions

---

## Technology Stack

### Frontend
- React.js
- Redux Toolkit
- Material UI
- Axios
- Vite

### Backend
- FastAPI
- SQLAlchemy
- PostgreSQL
- LangGraph
- LangChain
- Groq LLM

---

## Project Structure

```
AI-CRM-HCP
│
├── frontend
│
├── backend
│
└── README.md
```

---

## Installation

### Clone Repository

```bash
git clone https://github.com/RAJITHAMORLA/AI-CRM-HCP.git
```

---

## Backend Setup

```bash
cd backend

python -m venv venv

venv\Scripts\activate

pip install -r requirements.txt

uvicorn main:app --reload
```

Backend runs at

```
http://127.0.0.1:8000
```

Swagger Documentation

```
http://127.0.0.1:8000/docs
```

---

## Frontend Setup

```bash
cd frontend

npm install

npm run dev
```

Frontend runs at

```
http://localhost:5173
```

or

```
http://localhost:5174
```

---

## Environment Variables

Create a `.env` file inside the backend folder.

Example:

```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/ai_crm

GROQ_API_KEY=your_groq_api_key

GROQ_MODEL=llama-3.3-70b-versatile
```

---

## API Endpoints

### GET

```
/interactions
```

Returns all HCP interactions.

### POST

```
/interactions
```

Creates a new interaction.

### POST

```
/chat
```

Processes AI chat requests using LangGraph and Groq.

---

## AI Workflow

1. User enters interaction details through chat.
2. LangGraph processes the request.
3. Groq LLM understands the conversation.
4. Appropriate tool is executed.
5. Data is stored in PostgreSQL.
6. AI returns a conversational response.

---

## Database

PostgreSQL is used for storing HCP interaction records.

Information stored includes:

- HCP Name
- Interaction Type
- Date
- Time
- Topics Discussed
- Sentiment
- Follow-up Details

---

## Future Improvements

- User Authentication
- Dashboard Analytics
- Voice-based Interaction Logging
- Email Integration
- Multi-user Support
- AI-based Follow-up Recommendations

---

## Author

**Rajitha Morla**

B.Tech – Computer Science

AI-First CRM HCP Module

Built using React, FastAPI, PostgreSQL, LangGraph, and Groq LLM.

---

## Acknowledgement

This project was developed as part of the **AIVOA.AI Full Stack Developer Assignment** to demonstrate AI-powered CRM functionality using modern web technologies and Large Language Models.
