import os
import json
from typing import List, Optional
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Import the schema produced by SOWParserAgent
from agents.sow_parser import ParsedSOWSchema

load_dotenv()


# =====================================================================
# HLD Intermediate Representation Schemas
# =====================================================================

class ComponentSpec(BaseModel):
    name: str = Field(description="Name of the service/component (e.g., Auth Microservice, Search Worker)")
    type: str = Field(description="Type: API Service, Worker, Database, Cache, Queue, Frontend, Gateway")
    tech_stack: str = Field(description="Specific technology recommended (e.g., Python FastAPI, PostgreSQL, Redis)")
    description: str = Field(description="Role and responsibility of this component in the system")


class DataFlowSpec(BaseModel):
    step_number: int = Field(description="Sequence step number (1, 2, 3...)")
    source_component: str = Field(description="Component sending data")
    destination_component: str = Field(description="Component receiving data")
    protocol_payload: str = Field(description="Protocol & data description (e.g., HTTP POST /api/search with JWT)")


class InfrastructureSpec(BaseModel):
    cloud_provider: str = Field(description="Primary hosting environment (e.g., AWS, GCP, Azure, On-Premise)")
    core_services: List[str] = Field(description="List of specific infrastructure services (e.g., AWS ECS, Amazon ElastiCache)")
    security_controls: List[str] = Field(description="Security measures (e.g., TLS 1.3, IAM Roles, VPC Private Subnets)")
    scaling_strategy: str = Field(description="Auto-scaling policy or high-availability design details")


class HLDArchitectureSchema(BaseModel):
    system_name: str = Field(description="Overall system architecture title")
    architectural_pattern: str = Field(description="e.g., Microservices, Event-Driven, Serverless, Modular Monolith")
    summary: str = Field(description="Executive summary of the technical design solution")
    components: List[ComponentSpec] = Field(default_factory=list, description="System components and modules")
    data_flows: List[DataFlowSpec] = Field(default_factory=list, description="Step-by-step data flow sequence")
    infrastructure: InfrastructureSpec = Field(description="Cloud infrastructure and security specs")
    
    # -----------------------------------------------------------------
    # 7 Detailed Mermaid Diagram Fields
    # -----------------------------------------------------------------
    mermaid_architecture_code: str = Field(
        description="Detailed Mermaid.js 'graph TD' showing API gateways, microservices, databases, caches, queues, and protocols"
    )
    mermaid_usecase_code: str = Field(
        description="Detailed Mermaid.js 'graph LR' mapping distinct actors/user roles to subgraphs of functional use cases"
    )
    mermaid_dfd_code: str = Field(
        description="Detailed Mermaid.js 'graph LR' data flow diagram showing data ingestion pipelines, workers, streams, and storage"
    )
    mermaid_er_code: str = Field(
        description="Detailed Mermaid.js 'erDiagram' showing primary entities, attributes, data types, primary/foreign keys (PK/FK), and cardinality"
    )
    mermaid_deployment_code: str = Field(
        description="Detailed Mermaid.js 'graph TB' showing cloud infrastructure topography (VPC, Public/Private Subnets, Load Balancers, Multi-AZ DBs)"
    )
    mermaid_sequence_code: str = Field(
        description="Detailed Mermaid.js 'sequenceDiagram' rendering step-by-step interaction flows with auth headers and API endpoints"
    )
    mermaid_state_code: Optional[str] = Field(
        default="",
        description="Detailed Mermaid.js 'stateDiagram-v2' syntax illustrating granular state transitions and trigger events for complex lifecycles"
    )


# =====================================================================
# Architect Agent Implementation
# =====================================================================

class ArchitectAgent:
    """Agent responsible for designing the High-Level Architecture (HLD) schema from parsed SOW requirements."""

    def __init__(
        self, 
        model_name: str = "openai/gpt-oss-120b", 
        temperature: float = 0.1
    ):
        self.llm = ChatGroq(
            model=model_name,
            temperature=temperature,
            max_tokens=6000,
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.structured_llm = self.llm.with_structured_output(HLDArchitectureSchema)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an Enterprise Principal Cloud Solutions Architect.\n"
                "Your objective is to design a comprehensive, highly detailed High-Level Architecture (HLD)\n "
                "Keep descriptions concise and limit components and data flows to a maximum of 8 items to ensure fast processing.\n"
                "strictly based on the provided SOW requirements.\n\n"

                "STRICT GROUNDING RULE (NO HALLUCINATIONS):\n"
                "- ONLY include entities, services, components, and data flows explicitly stated or strictly implied by the SOW requirements.\n"
                "- DO NOT invent arbitrary tables, relations, or microservices that are irrelevant to the provided scope.\n\n"

                "STRICT NON-LINEAR & MULTI-LAYERED DIAGRAM LAYOUT RULES:\n"
                "1. DO NOT create single-line flat chains (A -> B -> C -> D).\n"
                "2. COMPONENT & DEPLOYMENT DIAGRAMS MUST USE MULTI-TIER SUBGRAPHS:\n"
                "   - Use subgraphs to define distinct architectural tiers:\n"
                "     subgraph Ingress Layer [API Gateway & Load Balancers]\n"
                "     subgraph Service Tier [Core Microservices]\n"
                "     subgraph Messaging & Queue [Kafka / RabbitMQ / Event Bus]\n"
                "     subgraph Persistence Tier [PostgreSQL / Redis / Vector DB]\n"
                "   - Show parallel branching (e.g., API Gateway routing concurrently to Service A, Service B, and Service C).\n"
                "   - Show cross-layer interactions (e.g., Service A reads Cache AND writes to DB AND emits Queue events).\n\n"

                "3. DETAILED ER DIAGRAM (erDiagram):\n"
                "   - Extract ALL entities strictly present in the scope.\n"
                "   - List exact attributes, data types, and primary/foreign keys (PK/FK).\n"
                "   - Map ONLY verified relationships with cardinalities (||--o{{}}, ||--|{{}}).\n\n"

                "4. USE CASE DIAGRAM (graph LR):\n"
                "   - Group use cases into functional module subgraphs (e.g., subgraph Consultation Module).\n"
                "   - Show actors connecting to multiple use cases across different modules.\n\n"

                "SYNTAX RULES:\n"
                "- Standard arrow format: A[Source] -->|Label| B[Target]\n"
                "- Do not use special characters or quotes inside node IDs.\n"
                "- Ensure valid Mermaid.js syntax."
            )),
            ("user", "Here is the parsed SOW requirements JSON:\n\n{parsed_sow_json}")
        ])

        self.chain = self.prompt | self.structured_llm

    def generate_hld(self, parsed_sow: ParsedSOWSchema) -> HLDArchitectureSchema:
        """Generates complete HLD architecture schema with a streamlined token footprint."""
        # Trim input context to fit comfortably inside the 8,000 TPM limit
        minimal_sow = {
            "project_title": parsed_sow.project_title,
            "overview": parsed_sow.overview,
            "functional_requirements": [
                {"id": fr.id, "module": fr.module, "description": fr.description}
                for fr in parsed_sow.functional_requirements[:8]
            ],
            "tech_stack_constraints": parsed_sow.tech_stack_constraints
        }
        
        sow_json_str = json.dumps(minimal_sow, indent=2)
        try:
            hld_result: HLDArchitectureSchema = self.chain.invoke({"parsed_sow_json": sow_json_str})
            return hld_result
        except Exception as e:
            raise RuntimeError(f"ArchitectAgent failed to synthesize design: {str(e)}") from e


# =====================================================================
# Standalone Execution / Test Routine
# =====================================================================

if __name__ == "__main__":
    from agents.sow_parser import FunctionalRequirement, NonFunctionalRequirement

    mock_sow = ParsedSOWSchema(
        project_title="E-Commerce Search Vectorization",
        overview="Replacing legacy SQL search with hybrid semantic vector search API.",
        functional_requirements=[
            FunctionalRequirement(id="FR-01", module="Search", description="Hybrid vector search across 500k products"),
            FunctionalRequirement(id="FR-02", module="Auth", description="Integrate with existing User Auth service")
        ],
        non_functional_requirements=[
            NonFunctionalRequirement(category="Performance", target_metric="< 150ms API latency under peak traffic")
        ],
        tech_stack_constraints=["AWS", "ECS", "OpenSearch"],
        deliverables=["Deployed API", "HLD Document"]
    )

    print("Synthesizing HLD architecture using ArchitectAgent (Groq)...")
    architect = ArchitectAgent()
    hld_design = architect.generate_hld(mock_sow)

    print("\n--- Generated HLD System Name ---")
    print(hld_design.system_name)
    print("\n--- Component Count ---")
    print(f"Total Components Designed: {len(hld_design.components)}")
    print("\n--- Generated ER Diagram Code ---")
    print(hld_design.mermaid_er_code)
    print("\n--- Generated Deployment Diagram Code ---")
    print(hld_design.mermaid_deployment_code)