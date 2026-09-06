import os
import json
import uuid
import shutil
from typing import Dict, Any, List, Optional
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

from langchain_groq import ChatGroq
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

from tools.agent_tools import (
    SESSION_STATE,
    parse_sow_pdf,
    synthesize_hld_architecture,
    generate_implementation_guidance,
    render_requested_diagrams,
    compile_hld_deliverables
)

load_dotenv()

app = FastAPI(title="SOW-to-HLD Agent API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_DIR = os.path.abspath("./tmp/uploads")
DIAGRAMS_DIR = os.path.abspath("./tmp/diagrams")
DELIVERABLES_DIR = os.path.abspath("./tmp/deliverables")
os.makedirs(UPLOAD_DIR, exist_ok=True)
os.makedirs(DIAGRAMS_DIR, exist_ok=True)
os.makedirs(DELIVERABLES_DIR, exist_ok=True)

TOOLS_MAP = {
    "parse_sow_pdf": parse_sow_pdf,
    "synthesize_hld_architecture": synthesize_hld_architecture,
    "generate_implementation_guidance": generate_implementation_guidance,
    "render_requested_diagrams": render_requested_diagrams,
    "compile_hld_deliverables": compile_hld_deliverables,
}

SYSTEM_PROMPT = (
    "You are an expert autonomous AI Software Architecture Agent.\n"
    "You have access to tools: parse_sow_pdf, synthesize_hld_architecture, generate_implementation_guidance, "
    "render_requested_diagrams, and compile_hld_deliverables.\n\n"
    "STRICT EXECUTION RULES:\n"
    "1. NEVER ask user confirmation to run prerequisites. Execute them automatically.\n"
    "2. ONLY generate the specific diagram requested:\n"
    "   - Step A: If HLD is not synthesized yet, run `synthesize_hld_architecture`.\n"
    "   - Step B: Run `render_requested_diagrams` passing only that diagram name: e.g. ['er_diagram'], ['data_flow_diagram'], ['sequence'], ['deployment'].\n"
    "3. When the user asks for implementation guidance, tech stack, or FOSS options, execute `generate_implementation_guidance`.\n"
    "4. Keep explanations concise to conserve token bandwidth."
)

CHAT_SESSIONS: Dict[str, List[Any]] = {}

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = "default"


def get_current_manifest() -> Dict[str, Any]:
    """Retrieves all generated diagram schemas and manifests."""
    manifest = {}
    manifest_path = os.path.join(DIAGRAMS_DIR, "diagrams_manifest.json")
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                raw = json.load(f)
                manifest = raw.get("diagrams", raw)
        except Exception:
            pass

    if os.path.exists(DIAGRAMS_DIR):
        for fname in os.listdir(DIAGRAMS_DIR):
            if fname.endswith(".json") and fname != "diagrams_manifest.json":
                key = fname.replace(".json", "")
                fpath = os.path.join(DIAGRAMS_DIR, fname)
                try:
                    with open(fpath, "r", encoding="utf-8") as f:
                        item_data = json.load(f)
                        if key not in manifest:
                            manifest[key] = item_data
                        elif isinstance(manifest[key], dict):
                            manifest[key].update(item_data)
                except Exception:
                    continue
    return manifest


def prune_history_for_groq(messages: List[Any]) -> List[Any]:
    """
    Compresses history to avoid exceeding Groq token limits:
    1. Keeps the system prompt intact.
    2. Takes a sliding window of the last 6 messages.
    3. Truncates older bulky ToolMessage outputs.
    """
    if len(messages) <= 4:
        return messages

    pruned = [messages[0]]
    recent = messages[-6:]

    for msg in recent:
        if isinstance(msg, ToolMessage) and len(str(msg.content)) > 400:
            short_content = str(msg.content)[:200] + "... [data preserved in SESSION_STATE & disk]"
            pruned.append(ToolMessage(content=short_content, tool_call_id=msg.tool_call_id))
        else:
            pruned.append(msg)

    return pruned


@app.post("/api/upload-sow")
async def upload_sow(file: UploadFile = File(...), session_id: Optional[str] = Form("default")):
    """Uploads SOW PDF, parses into memory, and resets the chat session context."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF documents are allowed.")

    if os.path.exists(DIAGRAMS_DIR):
        shutil.rmtree(DIAGRAMS_DIR)
    os.makedirs(DIAGRAMS_DIR, exist_ok=True)

    file_path = os.path.join(UPLOAD_DIR, file.filename)
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    parse_sow_pdf.invoke({"pdf_path": file_path})

    CHAT_SESSIONS[session_id] = [
        SystemMessage(content=SYSTEM_PROMPT),
        HumanMessage(content=f"System Notice: SOW Document '{file.filename}' parsed into session memory. Only invoke tools for items requested.")
    ]

    return {"filename": file.filename, "message": "SOW PDF uploaded and parsed successfully."}


@app.post("/api/chat")
async def chat_with_agent(req: ChatRequest):
    """Handles multi-turn conversational tool execution with token protection."""
    session_id = req.session_id or "default"
    if session_id not in CHAT_SESSIONS:
        CHAT_SESSIONS[session_id] = [SystemMessage(content=SYSTEM_PROMPT)]

    history = CHAT_SESSIONS[session_id]
    history.append(HumanMessage(content=req.message))

    llm = ChatGroq(
        model="openai/gpt-oss-120b",
        temperature=0.0,
        api_key=os.getenv("GROQ_API_KEY")
    ).bind_tools(list(TOOLS_MAP.values()))

    while True:
        safe_history = prune_history_for_groq(history)
        response = llm.invoke(safe_history)
        history.append(response)

        if not response.tool_calls:
            manifest = get_current_manifest()
            return {"reply": response.content, "manifest": manifest}

        for tool_call in response.tool_calls:
            tool_name = tool_call["name"]
            tool_args = tool_call["args"]
            selected_tool = TOOLS_MAP.get(tool_name)
            if selected_tool:
                tool_output = selected_tool.invoke(tool_args)
                history.append(ToolMessage(content=str(tool_output), tool_call_id=tool_call["id"]))
            else:
                history.append(ToolMessage(content=f"Error: Tool '{tool_name}' not found.", tool_call_id=tool_call["id"]))


@app.get("/api/diagrams")
async def get_diagrams():
    return get_current_manifest()


@app.get("/api/diagram-image/{filename}")
async def get_diagram_image(filename: str):
    clean_name = os.path.basename(filename)
    path = os.path.join(DIAGRAMS_DIR, clean_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found.")
    media_type = "image/svg+xml" if clean_name.endswith(".svg") else "image/png"
    return FileResponse(path, media_type=media_type)


@app.get("/api/download/{file_type}")
async def download_deliverable(file_type: str):
    file_map = {
        "docx": os.path.join(DELIVERABLES_DIR, "HLD_Specification.docx"),
        "pptx": os.path.join(DELIVERABLES_DIR, "HLD_Presentation.pptx")
    }
    target = file_map.get(file_type.lower())
    if not target or not os.path.exists(target):
        raise HTTPException(status_code=404, detail="Deliverable not found. Ask the agent to compile it first.")
    return FileResponse(target, filename=os.path.basename(target))