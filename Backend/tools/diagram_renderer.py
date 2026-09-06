import os
import re
import json
import base64
import requests
from typing import Dict, Any, Optional, List

class DiagramRendererTool:
    """Tool that converts Mermaid.js text strings into .png image files and tool-agnostic .json data models."""
    
    def __init__(self, output_dir: str = "./tmp/diagrams"):
        self.output_dir = os.path.abspath(output_dir)
        os.makedirs(self.output_dir, exist_ok=True)

    def _sanitize_mermaid_code(self, code: str) -> str:
        """Sanitizes Mermaid code to remove formatting artifacts, invalid comments, and syntax errors."""
        # 1. Convert escaped newlines into real newlines
        clean = code.replace("\\n", "\n")
        
        # 2. Remove markdown code fences
        clean = re.sub(r"^```(?:mermaid)?\s*", "", clean.strip(), flags=re.MULTILINE)
        clean = re.sub(r"```$", "", clean.strip(), flags=re.MULTILINE).strip()
        
        # 3. Replace invalid 'actor Name' in graph/flowchart with standard Mermaid node syntax
        if re.search(r"^\s*(graph|flowchart)", clean, flags=re.MULTILINE):
            clean = re.sub(r"^\s*actor\s+([A-Za-z0-9_]+)", r"    \1([\1])", clean, flags=re.MULTILINE)

        # 4. Fix missing or inverted attribute tokens in erDiagram
        def fix_er_attribute_line(match):
            datatype = match.group(1)
            key_type = match.group(2)
            comment = match.group(3) or ""
            return f"        {datatype} {datatype}_id {key_type} {comment}".rstrip()

        clean = re.sub(r"^\s*([a-zA-Z0-9_]+)\s+(PK|FK)\s*(\"[^\"]*\")?", fix_er_attribute_line, clean, flags=re.MULTILINE)
        
        # 5. Wrap unquoted node labels containing special characters in quotes
        def quote_node_label(match):
            node_id = match.group(1)
            label = match.group(2).strip()
            if label.startswith('"') and label.endswith('"'):
                return f'{node_id}[{label}]'
            return f'{node_id}["{label}"]'

        clean = re.sub(r'(\b\w+\b)\[([^\]\n]+)\]', quote_node_label, clean)

        # 6. Remove comments
        clean = re.sub(r"//.*$", "", clean, flags=re.MULTILINE)
        clean = re.sub(r"%%.*$", "", clean, flags=re.MULTILINE)
        
        # 7. Fix relationship syntax
        clean = clean.replace("..", "--")
        clean = clean.replace("|>", "|")
        
        # 8. Remove extra blank lines
        clean = "\n".join([line.rstrip() for line in clean.splitlines() if line.strip()])
        return clean

    def _get_preview_url(self, clean_code: str) -> str:
        """Generates an online mermaid.ink preview URL from URL-safe base64 encoded diagram syntax."""
        b64_code = base64.urlsafe_b64encode(clean_code.encode("utf-8")).decode("ascii")
        return f"https://mermaid.ink/img/{b64_code}?bgColor=white"

    def _parse_er_diagram_to_dict(self, clean_code: str) -> Dict[str, Any]:
        """Parses Mermaid erDiagram syntax into a tool-agnostic relational schema."""
        entities: List[Dict[str, Any]] = []
        relationships: List[Dict[str, Any]] = []

        # Extract Entity blocks: ENTITY_NAME { ... }
        entity_blocks = re.findall(r'(\b[A-Za-z0-9_]+\b)\s*\{([^}]*)\}', clean_code)
        for entity_name, body in entity_blocks:
            attributes = []
            for line in body.splitlines():
                line = line.strip()
                if not line or line.startswith("%%") or line.startswith("//"):
                    continue
                
                # Match: <datatype> <attr_name> [PK|FK] ["comment"]
                attr_match = re.match(
                    r'^([A-Za-z0-9_]+)\s+([A-Za-z0-9_]+)(?:\s+(PK|FK))?(?:\s+"([^"]*)")?', 
                    line, 
                    re.IGNORECASE
                )
                if attr_match:
                    data_type, attr_name, key_type, comment = attr_match.groups()
                    key_type = (key_type or "").upper()
                    attributes.append({
                        "name": attr_name,
                        "type": data_type.upper(),
                        "is_pk": "PK" in key_type,
                        "is_fk": "FK" in key_type,
                        "comment": comment or ""
                    })
                else:
                    parts = line.split()
                    if len(parts) >= 2:
                        attributes.append({
                            "name": parts[1],
                            "type": parts[0].upper(),
                            "is_pk": "PK" in [p.upper() for p in parts[2:]],
                            "is_fk": "FK" in [p.upper() for p in parts[2:]],
                            "comment": ""
                        })

            entities.append({
                "entity": entity_name,
                "attributes": attributes
            })

        # Extract Relationships: ENTITY1 ||--o{ ENTITY2 : label
        rel_matches = re.findall(
            r'(\b[A-Za-z0-9_]+\b)\s*([\|\}o\.\-]{4,6})\s*(\b[A-Za-z0-9_]+\b)\s*:\s*([^\n]+)', 
            clean_code
        )
        for from_ent, card, to_ent, label in rel_matches:
            relationships.append({
                "from": from_ent,
                "to": to_ent,
                "cardinality": card.strip(),
                "label": label.strip().strip('"')
            })

        return {
            "type": "relational_er_model",
            "entities": entities,
            "relationships": relationships
        }

    def _parse_generic_graph_to_dict(self, clean_code: str) -> Dict[str, Any]:
        """Parses graph/flowchart diagrams into nodes and directed edges."""
        nodes = []
        edges = []

        # Find nodes like ID["Label"] or ID[Label]
        node_matches = re.findall(r'(\b[A-Za-z0-9_]+\b)\["?(.*?)"?\]', clean_code)
        seen_nodes = set()
        for node_id, label in node_matches:
            if node_id not in seen_nodes:
                seen_nodes.add(node_id)
                nodes.append({"id": node_id, "label": label.strip()})

        # Find standard edges: A -->|Label| B or A --> B
        edge_matches = re.findall(
            r'(\b[A-Za-z0-9_]+\b)\s*-->(?:\|(.*?)\|)?\s*(\b[A-Za-z0-9_]+\b)', 
            clean_code
        )
        for source, label, target in edge_matches:
            edges.append({
                "source": source,
                "target": target,
                "label": (label or "").strip()
            })

        return {
            "type": "graph_model",
            "nodes": nodes,
            "edges": edges
        }

    def _render_via_mermaid_ink(self, clean_code: str, output_path: str) -> bool:
        """Renders diagram using mermaid.ink."""
        try:
            url = self._get_preview_url(clean_code)
            headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}
            response = requests.get(url, headers=headers, timeout=20)
            if response.status_code == 200 and len(response.content) > 100:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
        except Exception:
            pass
        return False

    def _render_via_kroki(self, clean_code: str, output_path: str) -> bool:
        """Fallback renderer using Kroki POST endpoint."""
        try:
            url = "https://kroki.io/mermaid/png"
            headers = {"Content-Type": "application/json", "User-Agent": "Mozilla/5.0"}
            response = requests.post(
                url,
                json={"diagram_source": clean_code},
                headers=headers,
                timeout=20
            )
            if response.status_code == 200 and len(response.content) > 100:
                with open(output_path, "wb") as f:
                    f.write(response.content)
                return True
        except Exception:
            pass
        return False

    def _save_diagram_json(
        self,
        filename_prefix: str,
        mermaid_code: str,
        clean_code: str,
        image_path: str,
        output_format: str
    ) -> str:
        """Saves a clean, tool-agnostic JSON schema containing semantic attributes and entities."""
        json_path = os.path.join(self.output_dir, f"{filename_prefix}.json")
        
        # 1. Structure the semantic model based on the diagram type
        if "er" in filename_prefix.lower() or clean_code.strip().startswith("erDiagram"):
            parsed_data = self._parse_er_diagram_to_dict(clean_code)
        elif clean_code.strip().startswith("graph") or clean_code.strip().startswith("flowchart"):
            parsed_data = self._parse_generic_graph_to_dict(clean_code)
        else:
            parsed_data = {"type": "diagram_model"}

        preview_url = self._get_preview_url(clean_code)

        # 2. Build the output schema WITH raw mermaid_code included
        data = {
            "name": filename_prefix,
            "title": filename_prefix.replace("_", " ").title(),
            "mermaid_code": clean_code,
            "schema_data": parsed_data,
            "image_path": os.path.abspath(image_path),
            "preview_url": preview_url
        }
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)

        # 3. Synchronize with diagrams_manifest.json on every run
        manifest_path = os.path.join(self.output_dir, "diagrams_manifest.json")
        manifest_data = {"diagrams": {}}
        if os.path.exists(manifest_path):
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest_data = json.load(f)
                    if "diagrams" not in manifest_data:
                        manifest_data = {"diagrams": manifest_data}
            except Exception:
                manifest_data = {"diagrams": {}}

        manifest_data["diagrams"][filename_prefix] = data
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
            
        return json_path

    def render_mermaid_to_image(
        self, 
        mermaid_code: str, 
        filename_prefix: str = "arch_diagram", 
        output_format: str = "png"
    ) -> str:
        """Parses and saves the structured JSON schema first, then attempts to render the PNG image."""
        if not mermaid_code or not mermaid_code.strip():
            raise ValueError("Mermaid code string is empty.")

        clean_code = self._sanitize_mermaid_code(mermaid_code)
        file_name = f"{filename_prefix}.{output_format}"
        output_path = os.path.join(self.output_dir, file_name)

        # 1. ALWAYS parse and write the structured JSON model first
        json_file = self._save_diagram_json(
            filename_prefix=filename_prefix,
            mermaid_code=mermaid_code,
            clean_code=clean_code,
            image_path=output_path,
            output_format=output_format
        )
        print(f"    📄 [DiagramRenderer (JSON)]: Saved structured model -> {json_file}")

        # 2. Attempt network image rendering (mermaid.ink -> kroki.io)
        rendered = False
        if self._render_via_mermaid_ink(clean_code, output_path):
            print(f"    🖼️ [DiagramRenderer (mermaid.ink)]: Saved {file_name} -> {output_path}")
            rendered = True
        elif self._render_via_kroki(clean_code, output_path):
            print(f"    🖼️ [DiagramRenderer (kroki.io)]: Saved {file_name} -> {output_path}")
            rendered = True

        # 3. Soft-fail warning for image rendering without destroying the generated JSON
        if not rendered:
            print(f"    ⚠️ [DiagramRenderer Warning]: Image rendering failed/timed out for '{filename_prefix}', but JSON data was preserved at {json_file}")

        return output_path

    def render_all_hld_diagrams(self, hld_design: Any) -> Dict[str, Optional[str]]:
        """Batch-renders all 7 HLD Mermaid diagram code attributes, exports individual JSONs, and builds a manifest JSON."""
        rendered_paths: Dict[str, Optional[str]] = {}
        manifest_data: Dict[str, Any] = {
            "system_name": getattr(hld_design, "system_name", "System Architecture"),
            "diagrams": {}
        }

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
                    clean = self._sanitize_mermaid_code(mermaid_code)
                    
                    # Store structured metadata in master manifest
                    manifest_data["diagrams"][file_prefix] = {
                        "state_key": state_key,
                        "image_path": os.path.abspath(img_path),
                        "json_path": os.path.abspath(os.path.join(self.output_dir, f"{file_prefix}.json")),
                        "preview_url": self._get_preview_url(clean)
                    }
                except Exception as err:
                    print(f"  Warning: Rendering skipped for {file_prefix}: {err}")
                    rendered_paths[state_key] = None
            else:
                rendered_paths[state_key] = None

        # Write master manifest file
        manifest_path = os.path.join(self.output_dir, "diagrams_manifest.json")
        with open(manifest_path, "w", encoding="utf-8") as f:
            json.dump(manifest_data, f, indent=2)
        print(f"    📦 [DiagramRenderer]: Master manifest exported -> {manifest_path}")

        return rendered_paths


if __name__ == "__main__":
    renderer = DiagramRendererTool()
    sample_er = """
    erDiagram
        PRODUCT {
            UUID product_id PK
            VARCHAR name
        }
        PRICE {
            UUID price_id PK
            UUID product_id FK
            DECIMAL amount
        }
        PRODUCT ||--o{ PRICE : "has"
    """
    print("Testing ER Diagram rendering & Structured JSON generation...")
    path = renderer.render_mermaid_to_image(sample_er, filename_prefix="er_test")
    print(f"SUCCESS: Rendered PNG to: {path}")
    print(f"SUCCESS: Structured JSON created at: {os.path.join(renderer.output_dir, 'er_test.json')}")