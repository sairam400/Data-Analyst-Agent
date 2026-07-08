"""FastAPI backend exposing the agent over HTTP: POST /ask runs a question
through the agent loop and returns the final answer plus the full reasoning
trace, POST /upload loads a CSV into the demo database so the agent can query
it like any other table, GET /schema mirrors the get_schema tool for the
frontend's initial schema view."""
import shutil
import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from ..agent.agent import Agent
from ..agent.providers import get_provider
from ..agent.tools import DB_PATH, get_schema
from ..data.csv_loader import load_csv_to_sqlite

app = FastAPI(title="AI Data Analyst Agent")

# Single-user local demo, not a multi-tenant service — wide open CORS is fine here.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class AskRequest(BaseModel):
    question: str


@app.post("/ask")
def ask(request: AskRequest):
    if not request.question.strip():
        raise HTTPException(status_code=400, detail="question must not be empty")
    agent = Agent(get_provider())
    return agent.run(str(uuid.uuid4()), request.question)


@app.post("/upload")
def upload(file: UploadFile = File(...)):
    if not file.filename.lower().endswith(".csv"):
        raise HTTPException(status_code=400, detail="only .csv files are supported")

    table_name = Path(file.filename).stem
    with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as tmp:
        shutil.copyfileobj(file.file, tmp)
        tmp_path = tmp.name

    try:
        return load_csv_to_sqlite(tmp_path, table_name, DB_PATH)
    finally:
        Path(tmp_path).unlink(missing_ok=True)


@app.get("/schema")
def schema():
    return get_schema()
