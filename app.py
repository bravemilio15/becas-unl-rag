import os
import sys
import time
import shutil
from dotenv import load_dotenv
from fastapi import FastAPI, BackgroundTasks, UploadFile, File, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, JSONResponse
from pydantic import BaseModel

# Agregar el directorio raíz al path
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(BASE_DIR)

# Importar lógica modular de backend
from backend.database import cargar_db, obtener_registro_archivos
from backend.rag import ejecutar_consulta

# Cargar variables de entorno
load_dotenv()

# Inicializar FastAPI
app = FastAPI(title="API RAG Becas UNL", version="2.0.0")

# Rutas de directorios
CHROMA_DIR = os.path.join(BASE_DIR, "chroma_db")
DATA_DIR = os.path.join(BASE_DIR, "data")
REGISTRY_PATH = os.path.join(DATA_DIR, "indexed_files.json")

# Estado global del recuperador
global_retriever = None

def refrescar_recuperador():
    """Recarga el objeto retriever de la base vectorial ChromaDB global."""
    global global_retriever
    db = cargar_db(CHROMA_DIR)
    if db is not None:
        global_retriever = db.as_retriever(search_kwargs={"k": 8})
        print("-> Recuperador de ChromaDB cargado correctamente.")
    else:
        global_retriever = None
        print("-> Advertencia: No se pudo cargar ChromaDB. Inicialice el indice primero.")

# Carga inicial al levantar la app
refrescar_recuperador()

# Modelos Pydantic para APIs
class MensajeHistorial(BaseModel):
    role: str
    content: str

class ConsultaRequest(BaseModel):
    prompt: str
    historial: list[MensajeHistorial] = []

# Endpoints de API

@app.post("/api/chat")
async def chat_endpoint(request: ConsultaRequest):
    """
    Endpoint conversacional. Ejecuta el RAG, priorizando Nvidia NIM con fallback a Groq y enviando historial.
    """
    global global_retriever
    groq_api_key = os.getenv("GROQ_API_KEY")
    nvidia_api_key = os.getenv("NVIDIA_API_KEY")

    # Validar que al menos una clave esté disponible
    tiene_groq = groq_api_key and groq_api_key != "tu_api_key_aqui"
    tiene_nvidia = nvidia_api_key and nvidia_api_key != "tu_api_key_aqui"

    if not tiene_groq and not tiene_nvidia:
        raise HTTPException(
            status_code=400, 
            detail="Claves de API no configuradas. Configure NVIDIA_API_KEY o GROQ_API_KEY en .env"
        )

    # Validar inicializacion de BD
    if global_retriever is None:
        refrescar_recuperador()
        if global_retriever is None:
            raise HTTPException(
                status_code=500, 
                detail="Base de datos vectorial no inicializada. Ejecute la ingesta primero."
            )

    try:
        t_inicio = time.time()
        # Pasar el historial a ejecutar_consulta
        respuesta, fuentes, contexto, prompt_final, latencia_retrieval, latencia_inference, modelo_activo = ejecutar_consulta(
            request.prompt, global_retriever, nvidia_api_key, groq_api_key, request.historial
        )
        latencia_total = time.time() - t_inicio
        
        return {
            "respuesta": respuesta,
            "fuentes": fuentes,
            "contexto": contexto,
            "prompt_final": prompt_final,
            "latencia_retrieval": latencia_retrieval,
            "latencia_inference": latencia_inference,
            "latencia_total": round(latencia_total, 3),
            "modelo_activo": modelo_activo
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en RAG pipeline: {str(e)}")

@app.post("/api/search")
async def search_endpoint(request: ConsultaRequest):
    """
    Realiza una búsqueda semántica directa en ChromaDB sin pasar por el LLM.
    Retorna la lista de fragmentos y sus distancias coseno (scores).
    """
    try:
        db = cargar_db(CHROMA_DIR)
        if db is None:
            raise HTTPException(status_code=500, detail="Base de datos vectorial no inicializada.")
        
        # similarity_search_with_score retorna una lista de tuplas (Document, score)
        resultados = db.similarity_search_with_score(request.prompt, k=8)
        
        salida = []
        for doc, score in resultados:
            salida.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source", "Desconocido"),
                "file_name": doc.metadata.get("file_name", "Desconocido"),
                "page": doc.metadata.get("page", 0),
                "score": round(float(score), 4)
            })
        return salida
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en búsqueda vectorial: {str(e)}")


@app.get("/api/stats")
async def stats_endpoint():
    """
    Endpoint de auditoria. Retorna el conteo de vectores, distribucion de fuentes y hashes.
    """
    db = cargar_db(CHROMA_DIR)
    
    # Calcular tamaño de la base de datos en disco
    tamano_disco = 0
    if os.path.exists(CHROMA_DIR):
        for dirpath, _, filenames in os.walk(CHROMA_DIR):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                tamano_disco += os.path.getsize(fp)

    # Cargar registro de hashes indexados
    registro_archivos = obtener_registro_archivos(REGISTRY_PATH)

    if db is None:
        return {
            "db_inicializada": False,
            "total_vectores": 0,
            "distribucion_fuentes": {},
            "tamano_disco_kb": round(tamano_disco / 1024, 2),
            "registro_archivos": registro_archivos,
            "groq_api_key_configurada": bool(os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "tu_api_key_aqui"),
            "nvidia_api_key_configurada": bool(os.getenv("NVIDIA_API_KEY") and os.getenv("NVIDIA_API_KEY") != "tu_api_key_aqui")
        }

    try:
        resultado = db._collection.get()
        documentos = resultado.get("documents", [])
        metadatas = resultado.get("metadatas", [])
        total_vectores = len(documentos)

        # Distribucion por fuente
        distribucion = {}
        for meta in metadatas:
            fuente = meta.get("source", "Desconocido")
            distribucion[fuente] = distribucion.get(fuente, 0) + 1

        # Metadatos del tamaño de fragmentos
        longitudes = [len(doc) for doc in documentos]
        longitud_promedio = sum(longitudes) / len(longitudes) if longitudes else 0

        return {
            "db_inicializada": True,
            "total_vectores": total_vectores,
            "distribucion_fuentes": distribucion,
            "tamano_disco_kb": round(tamano_disco / 1024, 2),
            "longitud_promedio_chunks": round(longitud_promedio, 2),
            "registro_archivos": registro_archivos,
            "groq_api_key_configurada": bool(os.getenv("GROQ_API_KEY") and os.getenv("GROQ_API_KEY") != "tu_api_key_aqui"),
            "nvidia_api_key_configurada": bool(os.getenv("NVIDIA_API_KEY") and os.getenv("NVIDIA_API_KEY") != "tu_api_key_aqui")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al leer ChromaDB: {str(e)}")

@app.post("/api/upload")
async def upload_endpoint(file: UploadFile = File(...)):
    """
    Sube un nuevo archivo al directorio de data/ de forma preventiva.
    """
    # Validar extensiones soportadas
    extension = os.path.splitext(file.filename)[1].lower()
    if extension not in [".pdf", ".md"]:
        raise HTTPException(status_code=400, detail="Formato no soportado. Suba archivos .pdf o .md")

    os.makedirs(DATA_DIR, exist_ok=True)
    destination_path = os.path.join(DATA_DIR, file.filename)

    try:
        with open(destination_path, "wb") as f:
            shutil.copyfileobj(file.file, f)
        return {"mensaje": f"Archivo '{file.filename}' subido y guardado exitosamente."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"No se pudo guardar el archivo: {str(e)}")

def ejecutar_ingesta_asincrona():
    """Llamada a ingesta.py de forma programada."""
    import ingesta
    print("Iniciando tarea asincrona de indexacion...")
    ingesta.main()
    refrescar_recuperador()

@app.post("/api/reindex")
async def reindex_endpoint(background_tasks: BackgroundTasks):
    """
    Inicia la ingesta y re-indexacion de documentos de forma asincrona sin bloquear la API.
    """
    background_tasks.add_task(ejecutar_ingesta_asincrona)
    return {"mensaje": "Proceso de re-indexacion iniciado en segundo plano. Esto tomara unos segundos."}

# Servir archivos estáticos del frontend (HTML, CSS, JS)
# Si no existe la carpeta static de forma inicial, se creara
os.makedirs(os.path.join(BASE_DIR, "static"), exist_ok=True)
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/")
async def read_index():
    """Redirecciona y sirve el index.html principal."""
    index_path = os.path.join(BASE_DIR, "static", "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return JSONResponse(content={"mensaje": "Servidor backend FastAPI levantado con exito. Ponga su frontend index.html en static/"})

if __name__ == "__main__":
    import uvicorn
    # Levantamos en el puerto 8002 para evitar colisiones detectadas con Docker
    uvicorn.run("app:app", host="0.0.0.0", port=8002, reload=True)
