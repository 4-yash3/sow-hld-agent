import os
import json
from typing import List
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

# Load .env variables
load_dotenv()


# Structured Output Schemas

class FunctionalRequirement(BaseModel):
    id: str = Field(description="Unique ID, e.g., FR-01")
    module: str = Field(description="System module or domain name, e.g., Auth, Ingestion")
    description: str = Field(description="Detailed requirement description")

class NonFunctionalRequirement(BaseModel):
    category: str = Field(description="Category e.g., Security, Performance, Scalability, Compliance")
    target_metric: str = Field(description="Metric or requirement details, e.g., < 200ms latency")

class ParsedSOWSchema(BaseModel):
    project_title: str = Field(description="Title or project name extracted from SOW")
    overview: str = Field(description="High-level summary of the scope")
    functional_requirements: List[FunctionalRequirement] = Field(default_factory=list)
    non_functional_requirements: List[NonFunctionalRequirement] = Field(default_factory=list)
    tech_stack_constraints: List[str] = Field(
        default_factory=list, 
        description="Mandatory tech constraints mentioned in SOW (e.g., Must run on AWS, PostgreSQL)"
    )
    deliverables: List[str] = Field(default_factory=list, description="Explicit deliverables required")



# Agent Class Definition


class SOWParserAgent:
    """Agent responsible for parsing SOW text into structured JSON using free Groq models."""

    def __init__(
        self, 
        model_name: str = "openai/gpt-oss-120b", 
        temperature: float = 0.0
    ):
        # Initialize Groq Chat Model
        self.llm = ChatGroq(
            model=model_name,
            temperature=temperature,
            api_key=os.getenv("GROQ_API_KEY")
        )
        
        # Bind Pydantic Schema for Structured Output
        self.structured_llm = self.llm.with_structured_output(ParsedSOWSchema)
        
        # System Prompt
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are an expert Enterprise Solutions Architect.\n"
                "Your job is to read raw text extracted from a Scope of Work (SOW) document "
                "and structure it into an accurate, unambiguous architectural context schema.\n\n"
                "Rules:\n"
                "1. Strictly separate Functional Requirements from Non-Functional Requirements (NFRs).\n"
                "2. Extract explicit tech constraints (e.g., cloud provider preferences, regulatory rules, database requirements).\n"
                "3. Do not invent requirements; infer only what is reasonably implied by the SOW text."
            )),
            ("user", "Here is the raw text from the SOW PDF:\n\n{raw_sow_text}")
        ])

        # Chain construction
        self.chain = self.prompt | self.structured_llm

    def parse(self, raw_sow_text: str) -> ParsedSOWSchema:
        """Parses raw text into a structured Pydantic object."""
        if not raw_sow_text.strip():
            raise ValueError("Provided raw_sow_text is empty.")

        try:
            parsed_result: ParsedSOWSchema = self.chain.invoke({"raw_sow_text": raw_sow_text})
            return parsed_result
        except Exception as e:
            raise RuntimeError(f"SOWParserAgent failed with Groq LLM: {str(e)}") from e


# Local Test       

if __name__ == "__main__":
    sample_sow_text = """
    Scope of Work: E-Commerce Search Upgrade
    The client requires a new vector search API to replace their legacy SQL search.
    Requirements:
    1. System must support semantic hybrid search across 500k products (FR-01).
    2. Must integrate with existing User Auth microservice (FR-02).
    3. The solution must run entirely within AWS using ECS and OpenSearch.
    4. API latency must remain below 150ms at 10,000 RPM peak traffic.
    5. Deliverables: Deployed API endpoint, Terraform templates, and HLD documentation.
    """

    print("Testing SOWParserAgent using free Groq openai/gpt-oss-120b...")
    parser_agent = SOWParserAgent()
    result = parser_agent.parse(sample_sow_text)
    
    print("\n--- Output JSON ---")
    print(json.dumps(result.model_dump(), indent=2))