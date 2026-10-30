# AI Support Ticket Copilot

An AI-powered customer support ticket management application built with
Google Gemini, RAG, LangGraph, FastAPI, Streamlit, SQLite, and Docker.

## Features

- AI-powered ticket categorization and priority assessment
- Suggested customer support replies
- FAQ retrieval using semantic search and embeddings
- LangGraph workflow with conditional escalation routing
- FastAPI endpoints for creating and managing support tickets
- SQLite persistence for ticket history and analysis
- Streamlit dashboard for ticket submission and status management
- Docker Compose for running the frontend and backend
- Automated API tests using pytest

## Technology Stack

- Python 3.13
- Google Gemini API
- LangChain and LangGraph
- Retrieval-Augmented Generation (RAG)
- Google Generative AI Embeddings
- FastAPI and Pydantic
- Streamlit
- SQLite
- Docker and Docker Compose
- pytest

## Architecture

```text
Customer
   |
   v
Streamlit Frontend
   |
   v
FastAPI Backend
   |
   v
LangGraph Workflow
   |
   +----> FAQ Retrieval (RAG)
   |          |
   |          v
   |     FAQ Knowledge Base
   |
   +----> Gemini Ticket Analysis
              |
              v
       Category, Priority,
       Summary and Suggested Reply
              |
              v
       Conditional Escalation
              |
              v
       SQLite Ticket Storage