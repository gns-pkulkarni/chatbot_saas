from pathlib import Path
from typing import List
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    PyMuPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredExcelLoader,
    CSVLoader,
    TextLoader,
)
import os
import tempfile

async def extract_document_content(file_path: str, file_name: str) -> List[Document]:
    """
    Extract content from various document types
    """
    docs: List[Document] = []
    suf = Path(file_name).suffix.lower()
    
    try:
        if suf == ".pdf":
            docs.extend(PyMuPDFLoader(file_path).load())
        elif suf in {".docx", ".doc"}:
            docs.extend(UnstructuredWordDocumentLoader(file_path).load())
        elif suf in {".xlsx", ".xls"}:
            docs.extend(UnstructuredExcelLoader(file_path, mode="single").load())
        elif suf == ".csv":
            docs.extend(CSVLoader(file_path).load())
        elif suf == ".txt" or suf == ".md":
            docs.extend(TextLoader(file_path).load())
        else:
            # Try text loader as fallback
            docs.extend(TextLoader(file_path).load())
    except Exception as e:
        print(f"Error extracting content from {file_name}: {e}")
        return []
    
    return docs

async def process_uploaded_file(file_content: bytes, file_name: str) -> str:
    """
    Process uploaded file and return extracted text
    """
    # Create temporary file
    with tempfile.NamedTemporaryFile(delete=False, suffix=Path(file_name).suffix) as tmp_file:
        tmp_file.write(file_content)
        tmp_file_path = tmp_file.name
    
    try:
        # Extract content
        docs = await extract_document_content(tmp_file_path, file_name)
        
        # Combine all document contents
        text_content = "\n\n".join([doc.page_content for doc in docs])
        
        return text_content
    finally:
        # Clean up temporary file
        if os.path.exists(tmp_file_path):
            os.unlink(tmp_file_path)
