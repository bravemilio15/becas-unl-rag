# Consola RAG - Sistema de Becas e Incentivos UNL

![FastAPI](https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi)
![Python](https://img.shields.io/badge/Python-3776AB?style=for-the-badge&logo=python&logoColor=white)
![ChromaDB](https://img.shields.io/badge/ChromaDB-5A29E4?style=for-the-badge&logo=sqlite&logoColor=white)
![Nvidia NIM](https://img.shields.io/badge/Nvidia_NIM-76B900?style=for-the-badge&logo=nvidia&logoColor=white)
![Groq](https://img.shields.io/badge/Groq_API-F37022?style=for-the-badge&logo=serverless&logoColor=white)

> [!IMPORTANT]
> **Descargo de Responsabilidad / Disclaimer:** Este proyecto es una práctica de laboratorio teórica y académica de la asignatura de Aprendizaje de Máquina (Machine Learning). No representa una implementación comercial o institucional en producción real de la Universidad Nacional de Loja (UNL). La información aquí contenida y las respuestas del bot son para fines de experimentación de técnicas RAG y de ingeniería de prompts.

Un sistema conversacional inteligente de nivel experimental basado en Generación Aumentada por Recuperación (RAG) y arquitectura multi-proveedor para la consulta interactiva de las normativas de becas y ayudas económicas de la Universidad Nacional de Loja (UNL).

---

## Caracteristicas Principales

1. **Ingesta y Chunking Inteligente:** Procesador de documentos Markdown y PDFs con indexación en la base vectorial ChromaDB. Utiliza una subdivisión adaptativa de Markdown a 750 caracteres para tablas complejas, evitando la dilución semántica de los montos y requisitos de becas.
2. **Recuperador Hibrido Semantico-Lexico:** Combina la búsqueda semántica densa de ChromaDB (utilizando embeddings locales `all-MiniLM-L6-v2`) con un motor de escaneo de coincidencia exacta de sub-cadenas ordenadas por densidad de keywords para garantizar un 100% de recall en términos críticos (Art. 28, promedio, asistencia, IESS, etc.).
3. **Memoria Conversacional Real (Chat Memory):** El RAG inyecta en caliente los últimos turnos de la conversación en el prompt del sistema, permitiendo preguntas de seguimiento continuas y contextuales.
4. **Resiliencia Multi-Proveedor y Fallback Secuencial:** Inferencia priorizando la API compatible de Nvidia NIM (`meta/llama-3.1-8b-instruct`) a nivel de capa gratuita (Free Tier). En caso de rate limits, TPS/TPM excedidos o caídas de conexión, conmuta en caliente de forma secuencial a los modelos vigentes de Groq:
   - `llama-3.3-70b-versatile`
   - `llama-3.1-8b-instant`
   - `llama-3.2-3b-preview`
5. **UI de Auditoria de Transparencia:** Interfaz web construida con Vanilla CSS e inyecciones dinámicas de JS que detalla el LLM activo que respondió la consulta, el desglose de latencias (recuperación + inferencia) y las etiquetas visuales filtradas conteniendo únicamente las fuentes reales utilizadas por el modelo.

---

## Instalacion y Configuracion

### 1. Clonar el repositorio
```bash
git clone https://github.com/bravemilio15/becas-unl-rag.git
cd becas-unl-rag
```

### 2. Configurar el Entorno Virtual
Crea y activa un entorno virtual de Python 3:
```bash
python3 -m venv venv
source venv/bin/activate
```

Instala las dependencias necesarias:
```bash
pip install -r requirements.txt
```

### 3. Variables de Entorno (.env)
Crea un archivo `.env` en la raíz del proyecto y configura tus claves de API oficiales:
```env
GROQ_API_KEY=tu_groq_api_key_aqui
NVIDIA_API_KEY=tu_nvidia_api_key_aqui
```

---

## Instrucciones de Uso

### 1. Indexación de Archivos (Ingesta)
Coloque los documentos PDF o Markdown de la normativa en el directorio `data/` (por ejemplo, `REGLAMENTO_DE_BECAS_DEFINITIVO.pdf` y `base_conocimiento_becas_unl.md`). Luego, ejecute la ingesta para recrear la base vectorial:
```bash
python backend/document_processor.py
```

### 2. Levantar el Servidor Web
Inicie la consola del backend y frontend unificados:
```bash
python app.py
```
El servidor estará disponible en el puerto local `http://localhost:8002/`.

---

## Estructura de Directorios

```text
├── app.py                  # Endpoint FastAPI y hosting de archivos estáticos
├── backend/
│   ├── database.py         # Configuración e inicialización de ChromaDB
│   ├── document_processor.py # Pipeline de ingesta, segmentación e indexación
│   └── rag.py              # Inferencia, Recuperador Híbrido, Fallbacks y prompt
├── data/                   # Reglamento PDF y base de conocimiento Markdown
├── static/                 # Frontend (index.html y app.js con Tailwind/Vanilla CSS)
├── requirements.txt        # Librerías requeridas del sistema
└── .gitignore              # Exclusiones de archivos del repositorio Git
```
