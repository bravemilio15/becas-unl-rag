import os
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

def obtener_embeddings():
    """
    Inicializa y retorna el modelo de embeddings local y gratuito.
    """
    return HuggingFaceEmbeddings(
        model_name="sentence-transformers/all-MiniLM-L6-v2",
        model_kwargs={'device': 'cpu'}
    )

def inicializar_db(chunks: list, chroma_dir: str) -> Chroma:
    """
    Genera la base de datos Chroma persistente a partir de fragmentos e indexa con los embeddings.
    """
    embeddings = obtener_embeddings()
    db = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=chroma_dir
    )
    
    # Intento seguro de persistencia para mantener compatibilidad entre versiones de LangChain
    try:
        db.persist()
    except AttributeError:
        pass
        
    return db

def cargar_db(chroma_dir: str) -> Chroma | None:
    """
    Carga la base de datos persistida localmente.
    """
    if not os.path.exists(chroma_dir):
        return None
        
    embeddings = obtener_embeddings()
    return Chroma(
        persist_directory=chroma_dir,
        embedding_function=embeddings
    )

import hashlib
import json

def calcular_hash_archivo(filepath: str) -> str:
    """
    Calcula el hash SHA-256 de un archivo para validar integridad y evitar duplicados.
    """
    hasher = hashlib.sha256()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hasher.update(chunk)
    return hasher.hexdigest()

def eliminar_documento_de_db(file_name: str, db: Chroma) -> bool:
    """
    Elimina todos los vectores indexados que correspondan al nombre de archivo especificado.
    """
    try:
        db._collection.delete(where={"file_name": file_name})
        return True
    except Exception as e:
        print(f"Error al eliminar fragmentos de {file_name} en Chroma: {e}")
        return False

def obtener_registro_archivos(registry_path: str) -> dict:
    """
    Obtiene el registro JSON de hashes y archivos indexados en local.
    """
    if os.path.exists(registry_path):
        try:
            with open(registry_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def guardar_registro_archivos(registry_path: str, registro: dict) -> None:
    """
    Guarda de forma persistente el registro de control de hashes en un archivo JSON.
    """
    os.makedirs(os.path.dirname(registry_path), exist_ok=True)
    with open(registry_path, "w", encoding="utf-8") as f:
        json.dump(registro, f, indent=4, ensure_ascii=False)
