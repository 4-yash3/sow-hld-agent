import os
import re
import requests
from typing import Dict, Any, Optional

class DiagramRendererTool:
    """Tool that converts Mermaid.js text strings into .png or .svg image files using Kroki."""
    
    def __init__(self, output_dir: str = "./tmp/diagrams"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)
        self.kroki_base_url = "https://kroki.io/mermaid"

    def _sanitize_mermaid_code(self, code: str) -> str:
        """Sanitizes Mermaid code to remove formatting artifacts, invalid comments, and markdown backticks."""
        # 1. Remove markdown fences
        clean = re.sub(r"^```(?:mermaid)?\s*", "", code.strip(), flags=re.MULTILINE)
        clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()
        
        # 2. Remove standard JS/C-style inline comments (// comment) which crash Mermaid ER parsers
        clean = re.sub(r"//.*$", "", clean, flags=re.MULTILINE)
        
        # 3. Remove mermaid comments (%% comment) that might have bad formatting
        clean = re.sub(r"%%.*$", "", clean, flags=re.MULTILINE)
        
        # 4. Clean syntax oddities
        clean = clean.replace("|>", "|")
        
        # Remove extra blank lines
        clean = "\n".join([line.rstrip() for line in clean.splitlines() if line.strip()])
        return clean

    def render_mermaid_to_image(
        self, 
        mermaid_code: str, 
        filename_prefix: str = "arch_diagram", 
        output_format: str = "png"
    ) -> str:
        """Renders Mermaid code into an image file and saves it locally.
        
        Returns:
            str: Local file path to the saved image.
        """
        if not mermaid_code or not mermaid_code.strip():
            raise ValueError("Mermaid code string is empty.")

        clean_code = self._sanitize_mermaid_code(mermaid_code)
        
        file_name = f"{filename_prefix}.{output_format}"
        output_path = os.path.join(self.output_dir, file_name)

        # POST payload to Kroki
        url = f"{self.kroki_base_url}/{output_format}"
        
        response = requests.post(
            url, 
            json={"diagram_source": clean_code},
            headers={"Content-Type": "application/json"},
            timeout=25
        )
        
        if response.status_code == 200:
            with open(output_path, "wb") as f:
                f.write(response.content)
            print(f"    💾 [DiagramRenderer]: Saved {file_name} -> {output_path}")
            return output_path
        else:
            error_msg = f"Kroki API error (Status {response.status_code}): {response.text}"
            print(f"\n❌ [KROKI ERROR]: {error_msg}\n")
            raise RuntimeError(error_msg)

    def render_all_hld_diagrams(self, hld_design: Any) -> Dict[str, Optional[str]]:
        """Batch-renders all 7 HLD Mermaid diagram code attributes from the HLD design object."""
        rendered_paths: Dict[str, Optional[str]] = {}
        diagram_mappings = [
            ("architecture_diagram_path", "mermaid_architecture_code", "arch_component"),
            ("usecase_diagram_path", "mermaid_usecase_code", "usecase_scope"),
            ("dfd_diagram_path", "mermaid_dfd_code", "data_flow"),
            ("er_diagram_path", "mermaid_er_code", "er_data_model"),
            ("deployment_diagram_path", "mermaid_deployment_code", "deployment_infra"),
            ("sequence_diagram_path", "mermaid_sequence_code", "sequence_critical"),
            ("state_diagram_path", "mermaid_state_code", "state_lifecycle"),
        ]

        for state_key, attr_name, file_prefix in diagram_mappings:
            mermaid_code = getattr(hld_design, attr_name, "")
            if mermaid_code and isinstance(mermaid_code, str) and mermaid_code.strip():
                try:
                    img_path = self.render_mermaid_to_image(
                        mermaid_code=mermaid_code,
                        filename_prefix=file_prefix,
                        output_format="png"
                    )
                    rendered_paths[state_key] = img_path
                except Exception as err:
                    print(f"  Warning: Rendering skipped for {file_prefix}: {err}")
                    rendered_paths[state_key] = None
            else:
                rendered_paths[state_key] = None

        return rendered_paths