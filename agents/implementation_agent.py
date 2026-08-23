import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Import your existing schemas
from agents.sow_parser import ParsedSOWSchema
from agents.architect import HLDArchitectureSchema

load_dotenv()

# =====================================================================
# Implementation Tech Stack Guidance Schema
# =====================================================================
class ComponentTechGuidance(BaseModel):
    component_name: str = Field(description="Name of the component from the HLD")
    component_role: str = Field(description="Core technical role of this component")
    primary_best_tech: str = Field(description="The gold-standard tool/library/platform (e.g., AWS API Gateway, Redis Enterprise, Pinecone)")
    tech_category: str = Field(description="Category: Library / Tool / SaaS Platform / Managed Cloud Service")
    selection_rationale: str = Field(description="In-depth reasoning explaining why this is the best technology option")
    open_source_alternative: str = Field(description="Best 100% Free / Open-Source alternative (e.g., Kong OSS, KeyDB, Qdrant/Milvus)")
    alternative_rationale: str = Field(description="Comparison explaining trade-offs, deployment overhead, and feasibility of the open-source alternative")
    recommended_libraries_frameworks: List[str] = Field(default_factory=list, description="Specific SDKs, client drivers, or CLI tools needed (e.g., ['qdrant-client', 'asyncpg'])")

class ImplementationArchitectureGuidance(BaseModel):
    system_title: str = Field(description="Title of the overall implementation spec")
    architecture_summary: str = Field(description="High-level engineering overview summarizing the implementation decisions")
    tech_stack_matrix: List[ComponentTechGuidance] = Field(default_factory=list, description="Detailed technology recommendations and OSS alternatives for every component")
    implementation_roadmap_notes: List[str] = Field(default_factory=list, description="Key implementation guidance, pitfalls, and dependency order for developers")

# =====================================================================
# Implementation Architect Agent
# =====================================================================
class ImplementationArchitectAgent:
    """Agent that translates SOW requirements and HLD design into concrete, tagged tech stack specifications."""

    def __init__(self, model_name: str = "openai/gpt-oss-120b", temperature: float = 0.1):
        self.llm = ChatGroq(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.structured_llm = self.llm.with_structured_output(ImplementationArchitectureGuidance)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are a Principal Software Engineering Tech Lead & System Architect.\n"
                "Your objective is to produce an exhaustive, implementation-ready architecture guidance document "
                "by analyzing the provided SOW requirements and High-Level Design (HLD).\n\n"
                "CONSTRAINTS TO PREVENT JSON CUTOFF:\n"
                "1. Limit `tech_stack_matrix` to 5-6 core components.\n"
                "2. Limit `implementation_roadmap_notes` to 4-5 bullet points.\n"
                "3. Keep all rationale descriptions under 25 words."
                
            )),
            ("user", (
                "Parsed SOW Context:\n{sow_json}\n\n"
                "Synthesized HLD Design:\n{hld_json}\n\n"
                "Generate the comprehensive implementation architecture guidance."
            ))
        ])
        self.chain = self.prompt | self.structured_llm

    def generate_guidance(self, parsed_sow: ParsedSOWSchema, hld_design: HLDArchitectureSchema) -> ImplementationArchitectureGuidance:
        # Minimal payload to keep token footprint tiny and well below the 8,000 TPM limit
        minimal_sow = {
            "project_title": parsed_sow.project_title,
            "tech_stack_constraints": parsed_sow.tech_stack_constraints
        }
        minimal_hld = {
            "system_name": hld_design.system_name,
            "components": [
                {"name": c.name, "type": c.type, "tech_stack": c.tech_stack} 
                for c in hld_design.components
            ]
        }
        try:
            return self.chain.invoke({
                "sow_json": json.dumps(minimal_sow, indent=2), 
                "hld_json": json.dumps(minimal_hld, indent=2)
            })
        except Exception as e:
            raise RuntimeError(f"ImplementationArchitectAgent failed: {str(e)}") from e