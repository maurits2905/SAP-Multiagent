import os
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from dotenv import load_dotenv

from .schemas import ChatRequest, ChatResponse
from .agents import route, run_specialist, qa_check, writer_finalize

load_dotenv()

if not os.getenv("GEMINI_API_KEY"):
    raise RuntimeError("Missing GEMINI_API_KEY in environment (.env)")

app = FastAPI(title="SAP Multi-Agent PoC")

app.mount("/static", StaticFiles(directory="app/static"), name="static")


@app.get("/", response_class=HTMLResponse)
def index():
    with open("app/templates/index.html", "r", encoding="utf-8") as f:
        return f.read()


@app.post("/chat", response_model=ChatResponse)
def chat(req: ChatRequest):
    decision = route(req.message, req.history)

    # If clarification needed, ask user directly (no specialist calls yet)
    if decision.clarifying_questions:
        return ChatResponse(
            answer="Jeg mangler lige lidt info:\n- " + "\n- ".join(decision.clarifying_questions),
            debug={"router": decision.model_dump()}
        )

    # Run specialists
    drafts = []
    for agent_name in decision.selected_agents:
        if agent_name in ("qa",):  # QA runs later
            continue
        if agent_name == "writer":  # writer is used for final, not as specialist draft
            continue
        drafts.append(run_specialist(agent_name, req.message, req.history))

    # QA gate
    qa = qa_check(req.message, req.history, drafts)

    # Final answer
    final = writer_finalize(req.message, req.history, drafts, qa)

    return ChatResponse(
        answer=final,
        debug={
            "router": decision.model_dump(),
            "drafts": [d.model_dump() for d in drafts],
            "qa": qa.model_dump(by_alias=True),
        },
    )
