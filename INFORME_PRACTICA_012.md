# Guía de Actividades Práctico-Experimentales Nro. 012

## Datos Generales
* **Asignatura:** Machine Learning
* **Ciclo:** 8 A
* **Unidad:** 1
* **Nombre del estudiante(s):** [Nombre del Estudiante]
* **Resultado de aprendizaje de la unidad:** Proporciona una explicación del papel del aprendizaje automático en la ingeniería informática, bajo los principios de solidaridad, transparencia, responsabilidad y honestidad.
* **Título de la práctica:** Implementación de una arquitectura RAG (Retrieval-Augmented Generation) para consulta inteligente de documentos.
* **Nombre del docente:** Genoveva Jackelinne Suing Albito
* **Nombre del técnico docente:** Ramiro Rene Rivera Guamán
* **Fecha de inicio:** Lunes 13 de julio de 2026
* **Horario:** 09h30 – 11h30
* **Fecha de fin:** Jueves 17 de julio de 2026
* **Horario:** 11h30 – 13h30
* **Lugar:** Aula virtual de la asignatura
* **Tiempo planificado en el Sílabo:** 4 horas

---

## Objetivo(s) de la Práctica
Implementa una arquitectura RAG mediante Python, utilizando documentos como base de conocimiento, modelos de embeddings y un modelo de lenguaje, con el propósito de desarrollar un sistema capaz de recuperar información relevante y generar respuestas contextualizadas.

---

## Materiales y reactivos
### Software:
* Python 3.10+
* Google Colab o Jupyter Notebook
* Navegador web

### Librerías:
* LangChain, ChromaDB, Sentence Transformers, Hugging Face Transformers, Pypdf.

### Documentos:
1. **Reglamento de Becas UNL (PDF):** [REGLAMENTO_DE_BECAS_DEFINITIVO.pdf](file:///home/bravandres/Escritorio/U/8vo/ML/BECAS/data/REGLAMENTO_DE_BECAS_DEFINITIVO.pdf)
2. **Guía de Ayudas Económicas SGA (MD):** [base_conocimiento_becas_unl.md](file:///home/bravandres/Escritorio/U/8vo/ML/BECAS/data/base_conocimiento_becas_unl.md)
3. **Tabla de Requisitos de Postulación (MD):** [requisitos_tramite_becas.md](file:///home/bravandres/Escritorio/U/8vo/ML/BECAS/data/requisitos_tramite_becas.md)

---

## Equipos y herramientas
* Aula de laboratorio, laptop con Pop!_OS (Linux), recursos de Google y acceso al EVA.

---

## Procedimiento / Metodología

### 1) Introducción
La arquitectura RAG (Retrieval-Augmented Generation) optimiza el uso de LLMs al indexar una base de conocimiento externa. Ante una consulta, el sistema recupera fragmentos de información relevante y los inyecta en el contexto del prompt para que el LLM genere respuestas precisas basadas en hechos, eliminando alucinaciones y limitaciones de actualización de datos.

---

### 2) Parte 1. Preparación del entorno
* **Aislamiento:** Creación del entorno virtual `venv` local.
* **Dependencias:** Instalación de librerías del backend especificadas en [requirements.txt](file:///home/bravandres/Escritorio/U/8vo/ML/BECAS/requirements.txt).
* **Credenciales:** Configuración del archivo `.env` con las API Keys de Nvidia NIM y Groq.

---

### 3) Parte 2. Construcción de la base documental
* **Estrategia de Chunking:**
  * **Markdown:** Segmentación jerárquica por encabezados con `MarkdownHeaderTextSplitter` y subdivisión recursiva de 750 caracteres (`chunk_overlap=120`) para no diluir el contenido semántico de tablas complejas.
  * **PDF:** Carga con `PyPDFLoader` y fragmentación recursiva de 1000 caracteres (`chunk_overlap=150`).
* **Métricas de Indexación:**
  * Guía SGA (MD): 14 fragmentos | Reglamento (PDF): 84 fragmentos | Requisitos (MD): 10 fragmentos.
  * **Total indexado:** 108 fragmentos provenientes de 3 documentos (cumple con el mínimo de 3 fuentes).

---

### 4) Parte 3. Generación de embeddings
* **Modelo:** Modelo local y open-source `sentence-transformers/all-MiniLM-L6-v2`.
* **Ejecución:** Cargado a través de la clase `HuggingFaceEmbeddings` de LangChain ejecutándose en CPU.

---

### 5) Parte 4. Construcción de la base vectorial
* **Base Vectorial:** ChromaDB con persistencia en el directorio [chroma_db/](file:///home/bravandres/Escritorio/U/8vo/ML/BECAS/chroma_db).
* **Desduplicación:** Implementación en [ingesta.py](file:///home/bravandres/Escritorio/U/8vo/ML/BECAS/ingesta.py) de control de cambios por hash SHA-256 para evitar indexación redundante.

---

### 6) Parte 5. Implementación del sistema RAG
El flujo en [backend/rag.py](file:///home/bravandres/Escritorio/U/8vo/ML/BECAS/backend/rag.py) integra:
1. **Reescritura:** Extracción de palabras clave con LLM para optimizar recall en ChromaDB.
2. **Recuperación Híbrida:** Búsqueda semántica (ChromaDB) y búsqueda léxica exacta de respaldo para términos técnicos y siglas críticas (IESS, SGA, Segunda Matrícula).
3. **Roles System/User:** Formateo y división del prompt en mensajes `"system"` (instrucciones y restricciones) y `"user"` (contexto y pregunta) para evitar preámbulos y saludos en Nvidia NIM.
4. **Inferencia y Fallback:** Inferencia en Nvidia NIM (`meta/llama-3.1-8b-instruct`) con fallback secuencial a Groq en caso de rate limits.
5. **Auditoría:** Filtrado dinámico de metadatos de las fuentes reales utilizadas.

![Figura 1: Arquitectura RAG](assets/figura_1_flujo_rag.png)

![Figura 2: Interfaz Web de Auditoría](assets/figura_2_interfaz_web.png)

---

### 7) Parte 6. Pruebas del sistema
Resultados obtenidos mediante la ejecución del notebook [evaluacion_rag.ipynb](file:///home/bravandres/Escritorio/U/8vo/ML/BECAS/evaluacion_rag.ipynb):

#### Consulta 1:
* **Pregunta:** ¿Cuáles son los requisitos obligatorios para la postulación en la Fase 1?
* **Respuesta:** Detalla la lista de 9 requisitos obligatorios de la Fase 1 (Tipo de beca, solicitud, cédula de estudiante y financiador, certificado de trabajo/ingresos, afiliación IESS, ficha socioeconómica, cartola y contrato de responsabilidad) recuperados de la tabla.
* **Observación:** Extracción correcta de la tabla de requisitos omitiendo los elementos no obligatorios.
* **Fuentes:** `<Requisitos_Tramite_MD>`

`![Figura 3: Ejecución Consulta 1](assets/figura_3_consulta_1.png)`

#### Consulta 2:
* **Pregunta:** ¿Cuál es la URL de descarga para el certificado de afiliación del IESS y qué formato de fecha de nacimiento solicita?
* **Respuesta:** URL oficial (`iess.gob.ec.../seleccionCertificadoDeAfiliacion.jsf`) y formato `"año-mes-día"` (ej. `"2019-07-17"`).
* **Observación:** Recuperación precisa de enlaces específicos y formatos de datos contenidos en las tablas de trámites.
* **Fuentes:** `<Requisitos_Tramite_MD>`

`![Figura 4: Ejecución Consulta 2](assets/figura_4_consulta_2.png)`

#### Consulta 3:
* **Pregunta:** ¿Puede un estudiante postular a una beca si tiene activo un proceso de segunda matrícula?
* **Respuesta:** No, el sistema bloquea el trámite si registra pérdida de gratuidad o si mantiene activo el proceso `'Segunda Matrícula'`.
* **Observación:** Aplicación correcta de las restricciones lógicas y de negocio descritas en la normativa.
* **Fuentes:** `<Requisitos_Tramite_MD>`

`![Figura 5: Ejecución Consulta 3](assets/figura_5_consulta_3.png)`

#### Consulta 4:
* **Pregunta:** ¿Cuál es el límite de peso y formato para subir el certificado del Ministerio de Trabajo?
* **Respuesta:** Formato PDF y tamaño máximo de archivo de 2 MB.
* **Observación:** Asociación directa de los parámetros de formato y peso para el archivo correspondiente.
* **Fuentes:** `<Requisitos_Tramite_MD>`

`![Figura 6: Ejecución Consulta 4](assets/figura_6_consulta_4.png)`

#### Consulta 5:
* **Pregunta:** ¿Me puedes dar una receta de cocina para preparar empanadas de viento?
* **Respuesta:** Negativa cortés: *"Mi rol se limita exclusivamente a asesorar sobre la normativa de becas e incentivos de la UNL..."*
* **Observación:** Funcionamiento correcto del filtro out-of-scope para impedir la alucinación de temas ajenos a la base documental.
* **Fuentes:** `Ninguna`

`![Figura 7: Ejecución Consulta 5](assets/figura_7_consulta_5.png)`

---

### 8) Parte 7. Análisis de resultados
* **Calidad de Respuestas:** Respuestas directas, deterministas y libres de alucinaciones gracias al prompt restrictivo, el parámetro `temperature: 0.0` y la separación de roles system/user.
* **Pertinencia y Recall:** Recall de 100% en términos clave y numéricos mediante el recuperador híbrido semántico-léxico de respaldo.
* **Latencias:** Tiempo de recuperación vectorial local eficiente (~0.01s) y velocidad de inferencia óptima en Nvidia NIM (~0.6s) con resiliencia por fallback multi-proveedor.

---

## Preguntas de Control

### 1. ¿Qué problema resuelve una arquitectura RAG?
Resuelve el problema de la falta de acceso de los LLMs a información privada, local o posterior a su entrenamiento, reduciendo drásticamente las alucinaciones al obligar al modelo a responder exclusivamente con el contexto recuperado de una base de conocimiento confiable.

### 2. ¿Cuál es la diferencia entre un LLM tradicional y un sistema RAG?
El LLM tradicional genera respuestas basándose únicamente en los datos generales aprendidos durante su entrenamiento (conocimiento paramétrico). El RAG busca primero documentos relevantes en un repositorio externo (conocimiento no paramétrico) y los inyecta en el prompt para guiar la inferencia en tiempo de ejecución.

### 3. ¿Qué función cumplen los embeddings?
Representan texto como vectores numéricos en un espacio multidimensional donde la distancia espacial (similitud de coseno) refleja similitud semántica, permitiendo la búsqueda conceptual en lugar de coincidencia exacta de texto.

### 4. ¿Por qué se utilizan bases de datos vectoriales?
Para almacenar y realizar consultas de similitud matemática en milisegundos sobre vectores de alta dimensión mediante índices espaciales optimizados (como HNSW), algo inviable en bases de datos relacionales o estructuradas tradicionales.

### 5. ¿Qué importancia tiene el proceso de *chunking*?
Determina el tamaño del fragmento de texto indexado. Si es muy grande, diluye el significado semántico y supera la ventana de contexto del LLM; si es muy pequeño, fragmenta la información y hace perder el contexto conceptual.

### 6. ¿Qué ocurriría si los documentos contienen información incorrecta o desactualizada?
El sistema recuperará datos incorrectos y el LLM propagará el error en la respuesta generada (principio GIGO: *Garbage In, Garbage Out*), ya que el modelo está limitado a responder únicamente con la información provista en el contexto.

### 7. ¿Qué ventajas ofrece RAG frente al *Fine-Tuning* para incorporar conocimiento específico?
RAG elimina el costo computacional de entrenar el modelo, permite la actualización o borrado de datos en tiempo real sin necesidad de reentrenamiento, y ofrece trazabilidad al poder auditar y citar las fuentes exactas del origen de la respuesta.

### 8. ¿En qué aplicaciones de ingeniería podría implementarse una arquitectura RAG?
En sistemas de soporte para la consulta inteligente de normativas de seguridad, asistentes conversacionales para la revisión y auditoría de manuales técnicos industriales complejos, motores de búsqueda semántica para documentación de APIs de desarrollo de software y auditorías automatizadas de cumplimiento normativo legal.

---

## Elaboración y Aprobación

| Elaborado por | Aplicado por | Aprobado por |
| :---: | :---: | :---: |
| **[Nombre del Estudiante]** <br> Estudiante de 8vo Ciclo | **Ing. Ramiro Rivera Guamán** <br> Técnico Docente | **Ing. Genoveva Suing Albito** <br> Docente de la Asignatura |
| | | **Ing. Edison Coronel Romero** <br> Director de Carrera |
