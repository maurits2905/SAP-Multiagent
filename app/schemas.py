from pydantic import BaseModel, Field
from typing import List, Literal, Optional


AgentName = Literal["tech", "finance", "logistics", "writer", "qa"]


class RouterDecision(BaseModel):
    selected_agents: List[AgentName] = Field(
        description="Which specialist agents to run for this user message."
    )
    clarifying_questions: List[str] = Field(
        default_factory=list,
        description="If needed, ask user for missing info. Keep short."
    )
    user_intent: str = Field(description="One-sentence summary of what user wants.")


class AgentResult(BaseModel):
    agent: AgentName
    answer: str
    key_points: List[str] = Field(default_factory=list)
    assumptions: List[str] = Field(default_factory=list)


class QAReport(BaseModel):
    pass_: bool = Field(alias="pass")
    issues: List[str] = Field(default_factory=list)
    required_fixes: List[str] = Field(default_factory=list)
    safe_final_answer: Optional[str] = Field(
        default=None,
        description="If QA can produce a corrected/safer final answer, put it here."
    )


class ChatRequest(BaseModel):
    message: str
    history: List[dict] = Field(default_factory=list)  # [{role, content}] for UI simplicity


class ChatResponse(BaseModel):
    answer: str
    debug: dict
