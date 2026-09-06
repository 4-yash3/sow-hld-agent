import os
from typing import Literal
from pydantic import BaseModel, Field
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from dotenv import load_dotenv

load_dotenv()

class IntentSchema(BaseModel):
    action: Literal[
        "parse_pdf", 
        "synthesize_hld", 
        "generate_implementation_guidance",
        "generate_sequence_diagram", 
        "generate_architecture_diagram", 
        "compile_deliverables", 
        "general_chat"
    ] = Field(description="The specific agent action required to fulfill the user prompt.")
    reasoning: str = Field(description="Short rationale for why this action was selected.")

class IntentRouterAgent:
    """Agent that analyzes user natural language and routes execution to the appropriate tool or graph node."""

    def __init__(self, model_name: str = "openai/gpt-oss-120b"):
        self.llm = ChatGroq(
            model=model_name,
            temperature=0.0,
            api_key=os.getenv("GROQ_API_KEY")
        )
        self.structured_llm = self.llm.with_structured_output(IntentSchema)

        self.prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "You are the Master Supervisor of an AI Software Architecture team.\n"
                "Your job is to read the user's request and classify their intent into exactly ONE action:\n\n"
                "- 'parse_pdf': User wants to extract/parse requirements from a PDF file path.\n"
                "- 'synthesize_hld': User wants to generate/design the high-level architecture or system spec.\n"
                "- 'generate_implementation_guidance': User asks for detailed implementation architecture, technology choices, library/tool/service tagging, tech stack matrix, or free/open-source alternatives.\n"
                "- 'generate_sequence_diagram': User specifically asks for a sequence diagram or data flow.\n"
                "- 'generate_architecture_diagram': User asks for a component diagram, system block diagram, or architecture graph.\n"
                "- 'compile_deliverables': User wants to export/download PowerPoint (.pptx) slides or Word (.docx) documents.\n"
                "- 'general_chat': General questions, greetings, or off-topic requests.\n"
            )),
            ("user", "{user_input}")
        ])

        self.chain = self.prompt | self.structured_llm

    def classify_intent(self, user_input: str) -> IntentSchema:
        return self.chain.invoke({"user_input": user_input})