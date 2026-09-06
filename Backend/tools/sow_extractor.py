import os
import fitz  # PyMuPDF
import pdfplumber
from typing import Dict, Any


class SOWExtractorTool:
    # Tool for extracting raw text, layout structures, and tables from SOW PDF documents.

    def __init__(self, use_pdfplumber_for_tables: bool = True):
        self.use_pdfplumber_for_tables = use_pdfplumber_for_tables

    def extract_text_pymupdf(self, pdf_path: str) -> str:
        """Fast text extraction using PyMuPDF (Fitz)."""
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")

        extracted_text = []
        try:
            doc = fitz.open(pdf_path)
            for page_num in range(len(doc)):
                page = doc[page_num]
                # "text" mode extracts standard text preserving line breaks
                text = page.get_text("text")
                if text.strip():
                    extracted_text.append(f"--- Page {page_num + 1} ---\n{text}")
            doc.close()
        except Exception as e:
            raise RuntimeError(f"PyMuPDF failed to extract text: {str(e)}") from e

        return "\n\n".join(extracted_text)

    def extract_tables_pdfplumber(self, pdf_path: str) -> str:
        # Extracts structured tables using pdfplumber and converts them to formatted text
        if not os.path.exists(pdf_path):
            raise FileNotFoundError(f"PDF file not found at path: {pdf_path}")

        table_text = []
        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page_idx, page in enumerate(pdf.pages):
                    tables = page.extract_tables()
                    for table_idx, table in enumerate(tables):
                        table_text.append(f"\n--- Table (Page {page_idx + 1}, Table {table_idx + 1}) ---")
                        for row in table:
                            # Filter out None values and clean string spaces
                            clean_row = [str(cell).strip() if cell is not None else "" for cell in row]
                            table_text.append(" | ".join(clean_row))
        except Exception as e:
            raise RuntimeError(f"pdfplumber failed to extract tables: {str(e)}") from e

        return "\n".join(table_text)

    def extract_all(self, pdf_path: str) -> Dict[str, Any]:
        """Combines fast text extraction and table parsing into a single output object."""
        raw_text = self.extract_text_pymupdf(pdf_path)
        
        tables_summary = ""
        if self.use_pdfplumber_for_tables:
            tables_summary = self.extract_tables_pdfplumber(pdf_path)

        # Merge raw text with extracted table data
        combined_content = f"{raw_text}\n\n=== EXTRACTED TABLES ===\n{tables_summary}"

        return {
            "pdf_path": pdf_path,
            "raw_text": raw_text,
            "tables_text": tables_summary,
            "combined_content": combined_content
        }


# Standalone Execution / Testing


if __name__ == "__main__":
    import sys

    extractor = SOWExtractorTool()
    
    # Check if a file path was passed via command line
    if len(sys.argv) > 1:
        target_pdf = sys.argv[1]
        print(f"Extracting content from: {target_pdf} ...")
        try:
            results = extractor.extract_all(target_pdf)
            print("\n--- Extraction Preview (First 500 chars) ---")
            print(results["combined_content"][:500])
            print(f"\nTotal character count: {len(results['combined_content'])}")
        except Exception as err:
            print(f"Error: {err}")
    else:
        print("Usage: python tools/sow_extractor.py path/to/sample_sow.pdf")