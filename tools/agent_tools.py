import os
from typing import List, Optional, Union
from langchain_core.tools import tool

# Global session memory shared across agent tool executions
SESSION_STATE = {
    "parsed_sow": None,
    "hld_design": None,
    "implementation_guidance": None,
    "diagrams": {}
}

# Mapping of requested diagram keys to (HLD attribute name, file prefix, state key)
DIAGRAM_MAP = {
    "er": ("mermaid_er_code", "er_data_model", "er_diagram_path"),
    "sequence": ("mermaid_sequence_code", "sequence_critical", "sequence_diagram_path"),
    "usecase": ("mermaid_usecase_code", "usecase_scope", "usecase_diagram_path"),
    "architecture": ("mermaid_architecture_code", "arch_component", "architecture_diagram_path"),
    "dfd": ("mermaid_dfd_code", "data_flow", "dfd_diagram_path"),
    "deployment": ("mermaid_deployment_code", "deployment_infra", "deployment_diagram_path"),
    "state": ("mermaid_state_code", "state_lifecycle", "state_diagram_path"),
}

@tool
def parse_sow_pdf(pdf_path: str) -> str:
    """Extracts and parses software requirement specification text from a local SOW PDF file path."""
    clean_path = pdf_path.strip('"\'')
    if not os.path.exists(clean_path):
        return f"Error: SOW PDF path '{clean_path}' does not exist on disk."
         
    try:
        from tools.sow_extractor import SOWExtractorTool
        from agents.sow_parser import SOWParserAgent
                 
        extractor = SOWExtractorTool()
        parser = SOWParserAgent()
                 
        raw_text = extractor.extract_all(clean_path)["combined_content"]
        
        # Hard limit to prevent Groq API rate limits
        if len(raw_text) > 12000:
            raw_text = raw_text[:12000]

        SESSION_STATE["parsed_sow"] = parser.parse(raw_text)
                 
        project_title = getattr(SESSION_STATE["parsed_sow"], "project_title", "SOW Requirements")
        return f"SUCCESS: Parsed SOW PDF. Project Title: '{project_title}'. You can now synthesize the HLD."
    except Exception as e:
        print(f"\n❌ [DEBUG PARSE ERROR]: {str(e)}\n")
        return f"Error occurred while parsing SOW PDF: {str(e)}"

@tool
def synthesize_hld_architecture() -> str:
    """Generates a High-Level Design (HLD) architecture spec from the parsed SOW in memory.
    DO NOT pass any arguments or parameters to this tool.
    """
    if not SESSION_STATE.get("parsed_sow"):
        return "Error: No parsed SOW in memory. Please call parse_sow_pdf first."

    try:
        from agents.architect import ArchitectAgent
        architect = ArchitectAgent()
                 
        SESSION_STATE["hld_design"] = architect.generate_hld(SESSION_STATE["parsed_sow"])
                 
        sys_name = getattr(SESSION_STATE["hld_design"], "system_name", "System Architecture")
        pattern = getattr(SESSION_STATE["hld_design"], "architectural_pattern", "Microservices")
                 
        return f"SUCCESS: HLD synthesized successfully for '{sys_name}' using pattern '{pattern}'. You can now generate implementation guidance or render diagrams."
    except Exception as e:
        # DO NOT return the full error 'e' to the LLM. It is too big!
        print(f"\n❌ [DEBUG SYNTHESIZE ERROR]: {str(e)}\n")
        return "ERROR: ArchitectAgent failed. Please try again or ask the user for clarification."

@tool
def generate_implementation_guidance() -> str:
    """Generates detailed implementation tech stack spec tagging every component with best technology choices.
    DO NOT pass any arguments or parameters to this tool.
    """
    if not SESSION_STATE.get("hld_design"):
        return "Error: Cannot generate implementation guidance without an HLD architecture in memory. Please synthesize an HLD first."

    try:
        from agents.implementation_agent import ImplementationArchitectAgent
        
        agent = ImplementationArchitectAgent()
        guidance = agent.generate_guidance(SESSION_STATE["parsed_sow"], SESSION_STATE["hld_design"])
        
        # Silently save to RAM for the document compiler
        SESSION_STATE["implementation_guidance"] = guidance

        return "SUCCESS: Implementation guidance generated and saved to memory. You can now compile the deliverables."
    except Exception as e:
        print(f"\n❌ [DEBUG GUIDANCE ERROR]: {str(e)}\n")
        return f"Error generating implementation guidance: {str(e)}"

@tool
def render_requested_diagrams(diagram_types: Optional[Union[List[str], str]] = None) -> str:
    """Renders specified Mermaid diagrams into PNG image files. Passing 'all' renders every diagram."""
    if not SESSION_STATE.get("hld_design"):
        return "Error: Cannot render diagrams because no HLD architecture exists in memory yet."
    
    try:
        from tools.diagram_renderer import DiagramRendererTool
        renderer = DiagramRendererTool()
        hld = SESSION_STATE["hld_design"]
        
        if isinstance(diagram_types, str):
            diagram_types = [diagram_types]
            
        # Clean and lowercase all inputs to prevent casing bugs ('ER' vs 'er')
        if not diagram_types or "all" in [str(d).lower() for d in diagram_types]:
            selected_keys = list(DIAGRAM_MAP.keys())
        else:
            selected_keys = [str(d).lower().strip() for d in diagram_types if str(d).lower().strip() in DIAGRAM_MAP]
            
        if not selected_keys:
            return f"Error: Invalid diagram type requested. Allowed types are: {list(DIAGRAM_MAP.keys())}"
            
        rendered_results = []
        
        for key in selected_keys:
            attr_name, file_prefix, state_key = DIAGRAM_MAP[key]
            mermaid_code = getattr(hld, attr_name, "")
            if mermaid_code and isinstance(mermaid_code, str) and mermaid_code.strip():
                try:
                    path = renderer.render_mermaid_to_image(
                        mermaid_code=mermaid_code,
                        filename_prefix=file_prefix,
                        output_format="png"
                    )
                    SESSION_STATE["diagrams"][state_key] = path
                    rendered_results.append(f"  {key.upper()} Diagram saved to: {path}")
                except Exception as err:
                    rendered_results.append(f"  Failed to render {key.upper()} Diagram: {str(err)}")
            else:
                rendered_results.append(f"  {key.upper()} Diagram code was empty in HLD spec.")
                
        return "SUCCESS: \n" + "\n".join(rendered_results)
    except Exception as e:
        print(f"\n❌ [DEBUG RENDER ERROR]: {str(e)}\n")
        return f"Error rendering diagrams: {str(e)}"

@tool
def compile_hld_deliverables() -> str:
    """Compiles PowerPoint (.pptx) presentation deck and Word (.docx) specification report with embedded diagrams.
    DO NOT pass any arguments or parameters to this tool.
    """
    if not SESSION_STATE.get("hld_design"):
        return "Error: Cannot compile deliverables because no HLD design exists in memory yet."
         
    try:
        from tools.diagram_renderer import DiagramRendererTool
        from tools.doc_compiler import DocumentCompilerTool
                 
        if not SESSION_STATE.get("diagrams"):
            renderer = DiagramRendererTool()
            SESSION_STATE["diagrams"] = renderer.render_all_hld_diagrams(SESSION_STATE["hld_design"])
                     
        compiler = DocumentCompilerTool()
        hld_dict = SESSION_STATE["hld_design"].model_dump()
        
        guidance = SESSION_STATE.get("implementation_guidance")
        guidance_dict = guidance.model_dump() if guidance else None
                 
        # Try passing implementation_guidance keyword if the compiler has been updated to accept it
        try:
            pptx = compiler.create_pptx_deck(hld_dict, diagram_paths=SESSION_STATE["diagrams"], implementation_guidance=guidance_dict)
            docx = compiler.create_docx_report(hld_dict, diagram_paths=SESSION_STATE["diagrams"], implementation_guidance=guidance_dict)
        except TypeError:
            # Clean fallback if tools/doc_compiler.py has not been updated with the 'implementation_guidance' argument yet
            pptx = compiler.create_pptx_deck(hld_dict, diagram_paths=SESSION_STATE["diagrams"])
            docx = compiler.create_docx_report(hld_dict, diagram_paths=SESSION_STATE["diagrams"])
                 
        return f"SUCCESS: Deliverables compiled successfully!\nPowerPoint: {os.path.abspath(pptx)}\nWord Spec: {os.path.abspath(docx)}"
    except Exception as e:
        print(f"\n❌ [DEBUG COMPILER ERROR]: {str(e)}\n")
        return f"Error occurred during deliverable compilation: {str(e)}"