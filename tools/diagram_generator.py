import os
import re
from typing import Any
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

class DynamicDiagramGenerator:
    """Generates valid Mermaid.js diagram syntax dynamically for any requested diagram type."""

    def __init__(self, model_name: str = "llama-3.3-70b-versatile"):
        self.llm = ChatGroq(
            model=os.getenv("GROQ_MODEL_NAME", model_name),
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert Enterprise Solutions Architect and Mermaid.js specialist.\n"
                "Your objective is to generate clean, syntactically valid Mermaid.js diagram code for ANY requested diagram type "
                "based strictly on the synthesized system architecture and SOW specification.\n\n"
                "CRITICAL SYNTAX & ARCHITECTURAL RULES:\n"
                "1. Output ONLY the raw Mermaid diagram text. Do not wrap in markdown code fences (```) and provide no conversational text.\n"
                "2. COMPONENT DIAGRAM ('component'):\n"
                "   - Start with 'graph LR'. Do NOT generate a duplicate generic architecture view.\n"
                "   - Group into logical subgraphs (e.g., Ingress, Service Tier, Storage & Messaging).\n"
                "   - Every node MUST include its runtime framework and libraries: e.g. ID[\"Service Name<br/><b>Framework/Tech</b><br/><i>Libraries</i>\"].\n"
                "   - In THIS diagram ONLY, connecting edges MUST specify protocol & port: e.g. -->|\"HTTPS / REST (Port 443)\"| or -->|\"TCP 9092 (Kafka)\"|.\n"
                "3. DATA FLOW DIAGRAM ('dfd'):\n"
                "   - ALWAYS start with 'flowchart TD' or 'flowchart LR'. Never use non-standard keywords like 'dataflowDiagram'.\n"
                "   - DO NOT write transport protocols like 'HTTPS / REST' or 'Port 443' on DFD edges!\n"
                "   - EVERY edge label MUST state the EXACT DATA or BUSINESS PAYLOAD moving between stages: "
                "e.g. -->|\"Caller Phone & Language Selection\"|, -->|\"JWT Session Token\"|, -->|\"Encrypted EHR FHIR Bundle\"|, -->|\"WebRTC Room ID & Tokens\"|.\n"
                "   - Must be a comprehensive Level 1/2 flow with NO isolated or disconnected nodes.\n"
                "   - Explicitly model: (a) External Entities, (b) Numbered processes (1.0, 2.0, 3.0), and (c) Datastores labeled as D1, D2, D3: e.g. D1[(\"D1: PostgreSQL Master\")].\n"
                "   - Show complete bi-directional request/response and persistence cycles.\n"
                "4. DEPLOYMENT DIAGRAM ('deployment'):\n"
                "   - Start with 'graph TB'. Model VPC boundaries, Public Subnets, Private Application Subnets, and Private Database Subnets.\n"
                "   - Every compute pod, node, VM, and database MUST display exact hardware allocations: vCPU count, RAM (GB), and Hard Disk specifications (e.g., '500 GB gp3 SSD, 12,000 IOPS' or 'EBS 1 TB').\n"
                "5. GENERAL SYNTAX INTEGRITY:\n"
                "   - Never use the 'actor' keyword in graph/flowchart diagrams.\n"
                "   - Wrap ALL node labels containing special characters, brackets, colons, or parentheses in double quotes."
            )),
            ("user", (
                "System Name: {system_name}\n"
                "Architectural Pattern: {architectural_pattern}\n"
                "System Summary: {summary}\n"
                "Core Components: {components_summary}\n\n"
                "Requested Diagram Type: '{diagram_type}'\n\n"
                "Generate raw Mermaid.js code for this diagram type:"
            ))
        ])
        self.chain = self.prompt | self.llm

    def generate_diagram(self, hld_design: Any, diagram_type: str) -> str:
        """Generates raw Mermaid.js syntax for any arbitrary diagram type on the fly."""
        components = getattr(hld_design, "components", [])
        comp_summary = "\n".join([
            f"- {c.name} ({c.type}, {c.tech_stack}): {c.description}"
            for c in components[:8]
        ])

        response = self.chain.invoke({
            "system_name": getattr(hld_design, "system_name", "System Architecture"),
            "architectural_pattern": getattr(hld_design, "architectural_pattern", "Microservices"),
            "summary": getattr(hld_design, "summary", ""),
            "components_summary": comp_summary,
            "diagram_type": diagram_type
        })

        raw = response.content.strip()
        clean = re.sub(r"^```(?:mermaid)?\s*", "", raw, flags=re.MULTILINE)
        clean = re.sub(r"```$", "", clean, flags=re.MULTILINE).strip()
        return clean