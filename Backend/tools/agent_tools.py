import os
import re
import json
from typing import List, Optional, Union
from langchain_core.tools import tool

# Global session memory shared across agent tool executions
SESSION_STATE = {
    "parsed_sow": None,
    "hld_design": None,
    "implementation_guidance": None,
    "diagrams": {},
    "diagram_jsons": {},
    "generated_mermaid_code": {}  # In-memory dynamic diagram cache
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
        
        SESSION_STATE["implementation_guidance"] = guidance
        return "SUCCESS: Implementation guidance generated and saved to memory. You can now compile the deliverables."
    except Exception as e:
        print(f"\n❌ [DEBUG GUIDANCE ERROR]: {str(e)}\n")
        return f"Error generating implementation guidance: {str(e)}"

@tool
def render_requested_diagrams(diagram_types: Optional[Union[List[str], str]] = None) -> str:
    """Renders any requested Mermaid diagrams (e.g. Component, ER, Sequence, Class, DFD, Deployment, State, etc.)
    into PNG image files and structured JSON data models.
    """
    if not SESSION_STATE.get("hld_design"):
        return "Error: Cannot render diagrams because no HLD architecture exists in memory yet."
    
    try:
        from tools.diagram_renderer import DiagramRendererTool
        from tools.diagram_generator import DynamicDiagramGenerator
        
        renderer = DiagramRendererTool()
        generator = DynamicDiagramGenerator()
        hld = SESSION_STATE["hld_design"]
        
        if isinstance(diagram_types, str):
            diagram_types = [d.strip() for d in diagram_types.split(",") if d.strip()]
            
        if not diagram_types or "all" in [str(d).lower() for d in diagram_types]:
            requested_list = ["component", "dfd", "deployment", "er", "sequence", "usecase", "class", "state"]
        else:
            requested_list = [str(d).strip() for d in diagram_types if str(d).strip()]
            
        rendered_results = []
        
        diagram_aliases = {
            "dataflow": "dfd",
            "data_flow": "dfd",
            "flow": "dfd",
            "architecture": "component",
            "arch": "component",
            "erd": "er",
            "er_model": "er",
            "use_case": "usecase",
            "class_diagram": "class",
            "component_diagram": "component",
            "deployment_diagram": "deployment",
        }
        
        for raw_diag_type in requested_list:
            raw_slug = re.sub(r'[^a-zA-Z0-9_]', '_', raw_diag_type.lower()).strip('_')
            # Strip trailing '_diagram' to prevent double-suffixing like er_diagram_diagram
            if raw_slug.endswith("_diagram"):
                raw_slug = raw_slug[:-8]

            slug = diagram_aliases.get(raw_slug, raw_slug)
            file_prefix = f"{slug}_diagram"
            
            # 1. Check in-memory dynamic cache
            mermaid_code = SESSION_STATE["generated_mermaid_code"].get(slug)
            
            # 2. Check pre-computed static attributes
            if not mermaid_code:
                static_attr_map = {
                    "er": "mermaid_er_code",
                    "sequence": "mermaid_sequence_code",
                    "usecase": "mermaid_usecase_code",
                    "component": "mermaid_architecture_code",
                    "deployment": "mermaid_deployment_code",
                    "dfd": "mermaid_dfd_code",
                    "state": "mermaid_state_code"
                }
                if slug in static_attr_map:
                    mermaid_code = getattr(hld, static_attr_map[slug], "")

            # 3. On-demand generation for specialized diagrams
            if not mermaid_code or not str(mermaid_code).strip() or slug in ["component", "dfd", "deployment"]:
                print(f"    ⚡ [DynamicDiagram]: Generating detailed '{slug}' diagram on-demand...")
                mermaid_code = generator.generate_diagram(hld, slug)
                SESSION_STATE["generated_mermaid_code"][slug] = mermaid_code

            # 4. Render to PNG and Structured JSON
            try:
                img_path = renderer.render_mermaid_to_image(
                    mermaid_code=mermaid_code,
                    filename_prefix=file_prefix,
                    output_format="png"
                )
                json_path = os.path.join(renderer.output_dir, f"{file_prefix}.json")
                
                SESSION_STATE["diagrams"][file_prefix] = img_path
                SESSION_STATE["diagrams"][f"{slug}_diagram_path"] = img_path
                if slug == "component":
                    SESSION_STATE["diagrams"]["architecture_diagram_path"] = img_path

                SESSION_STATE["diagram_jsons"][file_prefix] = json_path
                
                rendered_results.append(
                    f"SUCCESS: {slug.title()} Diagram saved!\n"
                    f"  - Image: {img_path}\n"
                    f"  - JSON:  {json_path}"
                )
            except Exception as err:
                print(f"\n❌ [DEBUG RENDER ERROR FOR {slug}]: {err}\n")
                rendered_results.append(f"FAILED to render {slug} Diagram: {str(err)}")
                
        return "\n".join(rendered_results)
    except Exception as e:
        print(f"\n❌ [DEBUG TOOL ERROR]: {str(e)}\n")
        return f"Error rendering diagrams: {str(e)}"

@tool
def compile_hld_deliverables() -> str:
    """Compiles PowerPoint (.pptx) presentation deck and Word (.docx) specification report with embedded diagrams.
    DO NOT pass any arguments or parameters to this tool.
    """
    if not SESSION_STATE.get("hld_design"):
        return "Error: Cannot compile deliverables because no HLD design exists in memory yet. Please parse SOW and synthesize HLD first."
         
    try:
        from tools.diagram_renderer import DiagramRendererTool
        from tools.doc_compiler import DocumentCompilerTool
        from agents.implementation_agent import ImplementationArchitectAgent
        
        renderer = DiagramRendererTool()
        compiler = DocumentCompilerTool()
        hld = SESSION_STATE["hld_design"]
        hld_dict = hld.model_dump()
        
        # 1. Auto-generate implementation guidance if missing from session memory
        if not SESSION_STATE.get("implementation_guidance") and SESSION_STATE.get("parsed_sow"):
            print("    ⚡ [DocCompiler]: Auto-generating implementation guidance for deliverables...")
            agent = ImplementationArchitectAgent()
            SESSION_STATE["implementation_guidance"] = agent.generate_guidance(
                SESSION_STATE["parsed_sow"], 
                hld
            )

        guidance = SESSION_STATE.get("implementation_guidance")
        guidance_dict = guidance.model_dump() if guidance else None

        # 2. Match standard filenames created by render_requested_diagrams
        diagram_paths = {
            "architecture_diagram_path": os.path.join(renderer.output_dir, "component_diagram.png"),
            "component_diagram_path": os.path.join(renderer.output_dir, "component_diagram.png"),
            "usecase_diagram_path": os.path.join(renderer.output_dir, "usecase_diagram.png"),
            "dfd_diagram_path": os.path.join(renderer.output_dir, "dfd_diagram.png"),
            "er_diagram_path": os.path.join(renderer.output_dir, "er_diagram.png"),
            "deployment_diagram_path": os.path.join(renderer.output_dir, "deployment_diagram.png"),
            "sequence_diagram_path": os.path.join(renderer.output_dir, "sequence_diagram.png"),
            "state_diagram_path": os.path.join(renderer.output_dir, "state_diagram.png"),
        }

        # 3. Check in-memory generated diagrams
        for key, path in SESSION_STATE.get("diagrams", {}).items():
            if path and os.path.exists(path):
                normalized_key = key if key.endswith("_path") else f"{key}_path"
                diagram_paths[normalized_key] = path
                if "component" in normalized_key:
                    diagram_paths["architecture_diagram_path"] = path

        # 4. Compile documents
        pptx = compiler.create_pptx_deck(
            hld_data=hld_dict, 
            diagram_paths=diagram_paths, 
            implementation_guidance=guidance_dict
        )
        docx = compiler.create_docx_report(
            hld_data=hld_dict, 
            diagram_paths=diagram_paths, 
            implementation_guidance=guidance_dict
        )
                 
        return f"SUCCESS: Deliverables compiled successfully with all diagrams & tech stack specs!\nPowerPoint: {os.path.abspath(pptx)}\nWord Spec: {os.path.abspath(docx)}"
    except Exception as e:
        print(f"\n❌ [DEBUG COMPILER ERROR]: {str(e)}\n")
        return f"Error occurred during deliverable compilation: {str(e)}"