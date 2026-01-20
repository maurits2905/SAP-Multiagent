import os
from typing import List, Dict, Any

from google import genai
from pydantic import BaseModel

from .schemas import RouterDecision, AgentResult, QAReport
from .prompts import (
    #Router system, Technology system, finance system, logistics system, writer system, quality assurance system
    ROUTER_SYSTEM, TECH_SYSTEM, FIN_SYSTEM, LOG_SYSTEM, WRITER_SYSTEM, QA_SYSTEM
)

client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])

MODEL_FAST = os.getenv("GEMINI_MODEL_FAST", "gemini-2.5-flash")
MODEL_SMART = os.getenv("GEMINI_MODEL_SMART", "gemini-2.5-pro")


def _history_to_text(history: List[Dict[str, Any]]) -> str:
    # Keep it simple for PoC. Later: proper conversation objects, tool messages, etc.
    lines = []
    for h in history[-12:]:
        role = h.get("role", "user")
        content = h.get("content", "")
        lines.append(f"{role.upper()}: {content}")
    return "\n".join(lines)


def _generate_json(model: str, system: str, user: str, schema_model: BaseModel):
    """
    Uses Gemini structured outputs via JSON schema-ish enforcement.
    Implementation approach: ask for strict JSON + validate with Pydantic.
    (You can later switch to native response_schema config if you prefer.)
    """
    resp = client.models.generate_content(
        model=model,
        contents=user,
        config={
            "system_instruction": system,
            "temperature": 0.2,
        },
    )
    text = resp.text.strip()
    # Pydantic parse; if model returns extra text, PoC may fail -> QA will reveal.
    return schema_model.model_validate_json(text)


def route(message: str, history: List[Dict[str, Any]]) -> RouterDecision:
    ctx = _history_to_text(history)
    user = f"""Conversation so far:
{ctx}

New user message:
{message}
"""
    return _generate_json(MODEL_FAST, ROUTER_SYSTEM, user, RouterDecision)


def run_specialist(agent: str, message: str, history: List[Dict[str, Any]]) -> AgentResult:
    ctx = _history_to_text(history)
    system_map = {
        "tech": TECH_SYSTEM,
        "finance": FIN_SYSTEM,
        "logistics": LOG_SYSTEM,
        "writer": WRITER_SYSTEM,
    }
    model = MODEL_SMART if agent in ("tech", "finance", "logistics") else MODEL_FAST
    system = system_map[agent]

    user = f"""Conversation so far:
{ctx}

User question:
{message}

Respond with:
- A short answer
- Key points (bullets)
- Assumptions (bullets)
"""
    resp = client.models.generate_content(
        model=model,
        contents=user,
        config={"system_instruction": system, "temperature": 0.3},
    )

    # Very light structure for PoC.
    answer = resp.text.strip()
    return AgentResult(agent=agent, answer=answer, key_points=[], assumptions=[])


def qa_check(message: str, history: List[Dict[str, Any]], drafts: List[AgentResult]) -> QAReport:
    ctx = _history_to_text(history)
    combined = "\n\n".join([f"[{d.agent.upper()}]\n{d.answer}" for d in drafts])

    user = f"""Conversation so far:
{ctx}

User question:
{message}

Draft answers from agents:
{combined}

Return QA report JSON.
"""
    return _generate_json(MODEL_FAST, QA_SYSTEM, user, QAReport)


def writer_finalize(message: str, history: List[Dict[str, Any]], drafts: List[AgentResult], qa: QAReport) -> str:
    ctx = _history_to_text(history)
    combined = "\n\n".join([f"[{d.agent.upper()}]\n{d.answer}" for d in drafts])

    # If QA already produced a safe final answer, use it (fast path)
    if qa.safe_final_answer:
        return qa.safe_final_answer.strip()

    user = f"""Conversation so far:
{ctx}

User question:
{message}

Draft answers:
{combined}

QA issues to address:
- Issues: {qa.issues}
- Required fixes: {qa.required_fixes}

Write the final answer to the user (Danish), concise but helpful, with next steps.
Do not add new facts not supported by drafts.
"""
    resp = client.models.generate_content(
        model=MODEL_FAST,
        contents=user,
        config={"system_instruction": WRITER_SYSTEM, "temperature": 0.2},
    )
    return resp.text.strip()
