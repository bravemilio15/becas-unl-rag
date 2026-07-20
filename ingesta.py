import os
import sys
from dotenv import load_dotenv

# Importar lógica modularizada y helpers de base de datos
from backend.document_processor import procesar_markdown, procesar_pdf
from backend.database import (
    cargar_db, inicializar_db, calcular_hash_archivo,
    eliminar_documento_de_db, obtener_registro_archivos, guardar_registro_archivos
)

# Cargar variables de entorno
load_dotenv()

# Configuración de rutas del proyecto
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
PATH_MD = os.path.join(DATA_DIR, "base_conocimiento_becas_unl.md")
PATH_PDF = os.path.join(DATA_DIR, "REGLAMENTO_DE_BECAS_DEFINITIVO.pdf")
PATH_REQUISITOS = os.path.join(DATA_DIR, "requisitos_tramite_becas.md")
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
REGISTRY_PATH = os.path.join(DATA_DIR, "indexed_files.json")

def main():
    print("Iniciando pipeline de ingesta modular con desduplicación inteligente...")
    
    # 1. Obtener registro persistente de hashes
    registro = obtener_registro_archivos(REGISTRY_PATH)
    
    # Definición de documentos a auditar y procesar
    archivos_a_procesar = [
        {"path": PATH_MD, "tipo": "md", "source": "Guia_MGT_MD"},
        {"path": PATH_PDF, "tipo": "pdf", "source": "Reglamento_PDF"},
        {"path": PATH_REQUISITOS, "tipo": "md", "source": "Requisitos_Tramite_MD"}
    ]
    
    # Intentar cargar base de datos existente
    db = cargar_db(CHROMA_DIR)
    
    chunks_totales_nuevos = []
    registro_modificado = False
    
    for item in archivos_a_procesar:
        path = item["path"]
        tipo = item["tipo"]
        source = item["source"]
        
        if not os.path.exists(path):
            print(f"Advertencia: El archivo en '{path}' no existe. Omitiendo.")
            continue
            
        filename = os.path.basename(path)
        hash_actual = calcular_hash_archivo(path)
        
        # Estrategia 1: Registro de Hashes (Verificar si el archivo cambió)
        info_anterior = registro.get(filename, {})
        hash_anterior = info_anterior.get("hash")
        
        if hash_anterior == hash_actual and db is not None:
            print(f"-> El archivo '{filename}' ya está indexado sin modificaciones. Omitiendo.")
            continue
            
        print(f"-> Procesando '{filename}' (se detectó cambio o archivo nuevo)...")
        
        # Estrategia 2: Borrado y Reemplazo (Eliminar fragmentos previos del mismo archivo en Chroma)
        if db is not None and hash_anterior is not None:
            print(f"   Eliminando fragmentos previos de '{filename}' de la base vectorial...")
            eliminado = eliminar_documento_de_db(filename, db)
            if eliminado:
                print("   -> Fragmentos anteriores eliminados correctamente de ChromaDB.")
        
        # Fragmentado y segmentación
        if tipo == "md":
            chunks = procesar_markdown(path, source)
        else:
            chunks = procesar_pdf(path)
            
        print(f"   Generados {len(chunks)} fragmentos.")
        chunks_totales_nuevos.extend(chunks)
        
        # Registrar metadatos e información de hash
        registro[filename] = {
            "hash": hash_actual,
            "source": source,
            "chunks_count": len(chunks)
        }
        registro_modificado = True

    # 2. Guardar e indexar en ChromaDB
    if chunks_totales_nuevos:
        if db is None:
            print("Inicializando base de datos ChromaDB desde cero...")
            db = inicializar_db(chunks_totales_nuevos, CHROMA_DIR)
        else:
            print(f"Indexando {len(chunks_totales_nuevos)} fragmentos nuevos/actualizados en ChromaDB...")
            db.add_documents(chunks_totales_nuevos)
            try:
                db.persist()
            except AttributeError:
                pass
        print("Persistencia de datos en ChromaDB completada.")
    else:
        print("No se detectaron cambios en los archivos base. No se requirió indexar vectores.")
        
    # 3. Guardar registro de hashes actualizado
    if registro_modificado:
        guardar_registro_archivos(REGISTRY_PATH, registro)
        print("Registro de hashes indexed_files.json guardado.")

if __name__ == "__main__":
    main()
