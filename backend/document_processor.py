import os
import sys
from langchain_text_splitters import MarkdownHeaderTextSplitter, RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader

def procesar_markdown(path: str) -> list:
    """
    Carga el archivo Markdown, lo segmenta jerárquicamente por encabezados (#, ##, ###)
    y luego subdivide de forma recursiva por caracteres para evitar bloques masivos.
    Conserva la estructura informativa sin dilución semántica.
    """
    if not os.path.exists(path):
        print(f"Error: No se encontró el archivo Markdown en {path}", file=sys.stderr)
        return []
    
    with open(path, "r", encoding="utf-8") as f:
        contenido = f.read()

    headers_to_split_on = [
        ("#", "Header 1"),
        ("##", "Header 2"),
        ("###", "Header 3"),
    ]

    splitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
    chunks_estructurados = splitter.split_text(contenido)

    # Dividir secuencialmente por longitud de caracteres conservando metadatos de encabezado
    caracter_splitter = RecursiveCharacterTextSplitter(
        chunk_size=750,
        chunk_overlap=120,
        length_function=len
    )
    chunks_finales = caracter_splitter.split_documents(chunks_estructurados)

    # Inyección de metadatos requeridos
    file_name = os.path.basename(path)
    for chunk in chunks_finales:
        chunk.metadata["source"] = "Guia_MGT_MD"
        chunk.metadata["file_name"] = file_name
        
    return chunks_finales

def procesar_pdf(path: str) -> list:
    """
    Carga y fragmenta recursivamente el archivo PDF reglamentario.
    """
    if not os.path.exists(path):
        print(f"Error: No se encontró el archivo PDF en {path}", file=sys.stderr)
        return []

    loader = PyPDFLoader(path)
    documentos = loader.load()

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=150,
        length_function=len
    )
    chunks = splitter.split_documents(documentos)

    # Inyección de metadatos requeridos y limpieza de campos extraños
    file_name = os.path.basename(path)
    for chunk in chunks:
        chunk.metadata = {
            "source": "Reglamento_PDF",
            "file_name": file_name,
            "page": chunk.metadata.get("page", 0)
        }

    return chunks
