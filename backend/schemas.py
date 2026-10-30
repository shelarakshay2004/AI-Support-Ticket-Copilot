from typing import Literal

from pydantic import BaseModel, Field


class TicketRequest(BaseModel):
    subject: str = Field(min_length=5, max_length=120)
    message: str = Field(min_length=10, max_length=3000)

    category_hint: Literal[
        "billing", "technical", "account", "general"
    ] | None = None


class TicketAnalysis(BaseModel):
    category: Literal["billing", "technical", "account", "general"]
    priority: Literal["low", "medium", "high"]
    summary: str
    suggested_reply: str
    should_escalate: bool
    escalation_reason: str | None = None


class TicketCreatedResponse(BaseModel):
    ticket_id: str
    status: Literal[
        "received", "in_progress", "resolved", "escalated"
    ]
    message: str
    analysis: TicketAnalysis
class TicketStatusUpdate(BaseModel):
    status: Literal[
        "received",
        "in_progress",
        "resolved",
        "escalated",
]