import logging
from contextlib import asynccontextmanager
from uuid import uuid4

from fastapi import FastAPI, HTTPException, Query

from backend.agent import analyze_ticket
from backend.database import (
    init_db,
    save_ticket,
    list_tickets,
    update_ticket_status,
)
from backend.schemas import (
    TicketRequest,
    TicketCreatedResponse,
    TicketStatusUpdate,
)


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Ticket database initialized")
    yield


app = FastAPI(
    title="AI Support Ticket Copilot",
    description="AI-powered support ticket analysis with RAG and LangGraph",
    version="1.0.0",
    lifespan=lifespan,
)


@app.get("/")
def home():
    return {
        "message": "AI Support Ticket Copilot API is running",
        "docs": "/docs",
        "ticket_history": "/tickets",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


# Create, analyze, and save a ticket
@app.post("/tickets", response_model=TicketCreatedResponse)
def create_ticket(ticket: TicketRequest):
    try:
        analysis = analyze_ticket(ticket)

    except RuntimeError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except Exception as exc:
        logger.exception("Ticket analysis failed")
        raise HTTPException(
            status_code=502,
            detail="AI analysis failed. Check the backend logs.",
        ) from exc

    ticket_id = str(uuid4())
    status = "escalated" if analysis.should_escalate else "received"

    try:
        save_ticket(
            ticket_id=ticket_id,
            ticket=ticket,
            status=status,
            analysis=analysis,
        )

    except Exception as exc:
        logger.exception("Failed to save ticket in SQLite")
        raise HTTPException(
            status_code=500,
            detail="Ticket analysis succeeded, but saving failed.",
        ) from exc

    return TicketCreatedResponse(
        ticket_id=ticket_id,
        status=status,
        message="Ticket analyzed and saved successfully.",
        analysis=analysis,
    )


# Retrieve saved tickets
@app.get("/tickets")
def get_ticket_history(
    limit: int = Query(default=20, ge=1, le=100),
):
    try:
        tickets = list_tickets(limit=limit)

        return {
            "count": len(tickets),
            "tickets": tickets,
        }

    except Exception as exc:
        logger.exception("Failed to retrieve ticket history")
        raise HTTPException(
            status_code=500,
            detail="Could not retrieve ticket history.",
        ) from exc


# Update a saved ticket's status
@app.patch("/tickets/{ticket_id}/status")
def change_ticket_status(
    ticket_id: str,
    payload: TicketStatusUpdate,
):
    try:
        updated = update_ticket_status(
            ticket_id=ticket_id,
            status=payload.status,
        )

        if not updated:
            raise HTTPException(
                status_code=404,
                detail="Ticket not found",
            )

        return {
            "message": "Ticket status updated successfully",
            "ticket_id": ticket_id,
            "status": payload.status,
        }

    except HTTPException:
        raise

    except Exception as exc:
        logger.exception("Failed to update ticket status")
        raise HTTPException(
            status_code=500,
            detail="Could not update ticket status.",
        ) from exc