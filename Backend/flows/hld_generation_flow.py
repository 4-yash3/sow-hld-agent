import os
import logging
from typing import Dict, Any
from langgraph.graph import StateGraph, END

# Import shared state model
from flows.state import HLDGraphState

# Import Agents & Tools
from tools.sow_extractor import SOWExtractorTool
from agents.sow_parser import SOWParserAgent
from agents.architect import ArchitectAgent
from agents.implementation_agent import ImplementationArchitectAgent  # <--- NEW IMPORT
from tools.diagram_renderer import DiagramRendererTool
from tools.doc_compiler import DocumentCompilerTool

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("HLDGenerationFlow")

# =====================================================================
# 1. Node Definitions
# =====================================================================

def extract_sow_text_node(state: HLDGraphState) -> Dict[str, Any]:
    """Node 1: Extract raw text and tables from SOW PDF."""
    logger.info("--- NODE: Extracting raw text from SOW PDF ---")
    pdf_path = state.get("sow_pdf_path")
         
    if not pdf_path or not os.path.exists(pdf_path):
        return {"error": f"Invalid or non-existent PDF path: {pdf_path}", "status": "FAILED"}
    try:
        extractor = SOWExtractorTool()
        extraction_result = extractor.extract_all(pdf_path)
        return {"raw_sow_text": extraction_result["combined_content"], "status": "TEXT_EXTRACTED"}
    except Exception as e:
        return {"error": f"Failed during SOW text extraction: {str(e)}", "status": "FAILED"}

def parse_sow_requirements_node(state: HLDGraphState) -> Dict[str, Any]:
    """Node 2: Parse raw text into structured SOW requirements JSON using Groq LLM."""
    logger.info("--- NODE: Parsing SOW requirements with SOWParserAgent ---")
    raw_text = state.get("raw_sow_text", "")
    if not raw_text:
        return {"error": "No raw_sow_text found in state.", "status": "FAILED"}
    try:
        parser_agent = SOWParserAgent()
        parsed_sow_schema = parser_agent.parse(raw_text)
        return {"parsed_sow": parsed_sow_schema, "status": "SOW_PARSED"}
    except Exception as e:
        return {"error": f"Failed during SOW requirements parsing: {str(e)}", "status": "FAILED"}

def synthesize_hld_node(state: HLDGraphState) -> Dict[str, Any]:
    """Node 3: Synthesize High-Level Architecture (HLD) schema and Mermaid diagrams."""
    logger.info("--- NODE: Synthesizing architecture design with ArchitectAgent ---")
    parsed_sow = state.get("parsed_sow")
    if not parsed_sow:
        return {"error": "No parsed_sow found in state.", "status": "FAILED"}
    try:
        architect_agent = ArchitectAgent()
        hld_schema = architect_agent.generate_hld(parsed_sow)
        return {"hld_design": hld_schema, "status": "HLD_DESIGNED"}
    except Exception as e:
        return {"error": f"Failed during HLD architecture synthesis: {str(e)}", "status": "FAILED"}

def generate_implementation_guidance_node(state: HLDGraphState) -> Dict[str, Any]:
    """Node 4: Tag components with tech choices, rationale, OSS alternatives, and libraries."""
    logger.info("--- NODE: Generating implementation tech stack guidance ---")
    parsed_sow = state.get("parsed_sow")
    hld_design = state.get("hld_design")
    if not hld_design or not parsed_sow:
        return {"error": "Missing parsed_sow or hld_design for implementation guidance.", "status": "FAILED"}
    try:
        implementation_agent = ImplementationArchitectAgent()
        guidance = implementation_agent.generate_guidance(parsed_sow, hld_design)
        return {"implementation_guidance": guidance, "status": "GUIDANCE_GENERATED"}
    except Exception as e:
        return {"error": f"Failed during implementation guidance generation: {str(e)}", "status": "FAILED"}

def render_diagrams_node(state: HLDGraphState) -> Dict[str, Any]:
    """Node 5: Render all 7 Mermaid.js code strings into PNG image artifacts via Kroki."""
    logger.info("--- NODE: Rendering up to 7 Mermaid diagrams into PNG image files ---")
    hld_design = state.get("hld_design")
    if not hld_design:
        return {"error": "No hld_design found in state.", "status": "FAILED"}
    try:
        renderer = DiagramRendererTool()
        rendered_paths = renderer.render_all_hld_diagrams(hld_design)
        output_state = {"status": "DIAGRAMS_RENDERED"}
        output_state.update(rendered_paths)
        return output_state
    except Exception as e:
        return {"error": f"Failed during diagram rendering: {str(e)}", "status": "FAILED"}

def compile_deliverables_node(state: HLDGraphState) -> Dict[str, Any]:
    """Node 6: Compile final PowerPoint (.pptx) and Word (.docx) deliverables with all diagrams & tech stack specs."""
    logger.info("--- NODE: Compiling final PPTX and DOCX deliverables ---")
    hld_design = state.get("hld_design")
    if not hld_design:
        return {"error": "Missing hld_design for document compilation.", "status": "FAILED"}
    try:
        compiler = DocumentCompilerTool()
        hld_dict = hld_design.model_dump()
        
        # Pull the guidance from state
        guidance = state.get("implementation_guidance")
        guidance_dict = guidance.model_dump() if guidance else None
        
        diagram_keys = [
            "architecture_diagram_path", "usecase_diagram_path", "dfd_diagram_path",
            "er_diagram_path", "deployment_diagram_path", "sequence_diagram_path", "state_diagram_path"
        ]
        diagram_paths = {key: state.get(key) for key in diagram_keys}
        
        pptx_file = compiler.create_pptx_deck(
            hld_data=hld_dict,
            diagram_paths=diagram_paths,
            implementation_guidance=guidance_dict # Pass guidance to compiler
        )
        docx_file = compiler.create_docx_report(
            hld_data=hld_dict,
            diagram_paths=diagram_paths,
            implementation_guidance=guidance_dict # Pass guidance to compiler
        )
        return {"pptx_path": pptx_file, "docx_path": docx_file, "status": "COMPLETE"}
    except Exception as e:
        return {"error": f"Failed during document compilation: {str(e)}", "status": "FAILED"}

# =====================================================================
# 2. Conditional Routing Logic & Graph Builder
# =====================================================================

def check_for_errors(state: HLDGraphState) -> str:
    """Conditional Edge: Route to END if an error occurs, else continue."""
    if state.get("error"):
        logger.error(f"Workflow terminated due to error: {state.get('error')}")
        return "error_end"
    return "continue"

def build_hld_pipeline():
    """Builds and compiles the full sequential LangGraph architecture generation pipeline."""
    graph = StateGraph(HLDGraphState)
    
    # Register Nodes
    graph.add_node("extract_text", extract_sow_text_node)
    graph.add_node("parse_sow", parse_sow_requirements_node)
    graph.add_node("synthesize_hld", synthesize_hld_node)
    graph.add_node("generate_guidance", generate_implementation_guidance_node) # <--- NEW NODE
    graph.add_node("render_diagrams", render_diagrams_node)
    graph.add_node("compile_deliverables", compile_deliverables_node)
    
    # Set Entry Point
    graph.set_entry_point("extract_text")
    
    # Wire Edges with Error Checking
    graph.add_conditional_edges("extract_text", check_for_errors, {"continue": "parse_sow", "error_end": END})
    graph.add_conditional_edges("parse_sow", check_for_errors, {"continue": "synthesize_hld", "error_end": END})
    graph.add_conditional_edges("synthesize_hld", check_for_errors, {"continue": "generate_guidance", "error_end": END}) # Edge adjusted
    graph.add_conditional_edges("generate_guidance", check_for_errors, {"continue": "render_diagrams", "error_end": END}) # New edge
    graph.add_conditional_edges("render_diagrams", check_for_errors, {"continue": "compile_deliverables", "error_end": END})
    graph.add_edge("compile_deliverables", END)
    
    return graph.compile()

# Standalone Pipeline Test
if __name__ == "__main__":
    import sys
    pipeline = build_hld_pipeline()
    sample_pdf = sys.argv[1] if len(sys.argv) > 1 else "sample_sow.pdf"
    print(f"Running automated pipeline on: {sample_pdf}")
         
    final_output = pipeline.invoke({"sow_pdf_path": sample_pdf})
    print("\n--- Pipeline Execution Result ---")
    print(f"Status: {final_output.get('status')}")
    if final_output.get("error"):
        print(f"Error: {final_output.get('error')}")
    else:
        print(f"Word Doc: {final_output.get('docx_path')}")
        print(f"PowerPoint: {final_output.get('pptx_path')}")