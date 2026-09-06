from typing import TypedDict, List, Dict, Any, Optional
from agents.sow_parser import ParsedSOWSchema
from agents.architect import HLDArchitectureSchema
from agents.implementation_agent import ImplementationArchitectureGuidance  # <--- NEW IMPORT

class HLDGraphState(TypedDict, total=False):
    """The shared state object passed across nodes in the LangGraph workflow."""
    # 1. Inputs
    sow_pdf_path: str                 # Local path to incoming SOW PDF file
         
    # 2. Extracted & Intermediate Artifacts
    raw_sow_text: str                 # Text extracted by tools/sow_extractor.py
    parsed_sow: ParsedSOWSchema       # Structured SOW requirements JSON from sow_parser.py
    hld_design: HLDArchitectureSchema # System architecture JSON spec from architect.py
    implementation_guidance: Optional[ImplementationArchitectureGuidance] # <--- NEW STATE VARIABLE
         
    # 3. Diagram Rendering Outputs (All 7 HLD Diagram Views)
    architecture_diagram_path: Optional[str] # Component Architecture (graph TD)
    usecase_diagram_path: Optional[str]      # Use Case / Functional Scope (graph LR)
    dfd_diagram_path: Optional[str]          # Data Flow Diagram / Pipeline (graph LR)
    er_diagram_path: Optional[str]           # Entity-Relationship / Data Model (erDiagram)
    deployment_diagram_path: Optional[str]   # Cloud Infrastructure Topography (graph TB)
    sequence_diagram_path: Optional[str]     # Critical Scenarios Interaction (sequenceDiagram)
    state_diagram_path: Optional[str]        # Entity Lifecycle State Machine (stateDiagram-v2)
         
    # 4. Final Deliverables
    pptx_path: Optional[str]           # Path to compiled PowerPoint .pptx deck
    docx_path: Optional[str]           # Path to compiled Word .docx specification
         
    # 5. Execution Tracking & Control Flags
    error: Optional[str]               # Captures runtime errors if a node fails
    retry_count: int                   # Tracks execution retry attempts for self-correction loops
    status: str                        # Current workflow status (e.g., "PARSING", "DESIGNING", "GUIDANCE_GENERATED", "COMPLETE")