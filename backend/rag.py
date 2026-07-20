from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
import os
import time
import json
import urllib.request
import re

PROMPT_TEMPLATE = """Eres un asistente de consulta e inteligencia documental sobre el Sistema de Becas de la Universidad Nacional de Loja (UNL).
Tu deber es responder preguntas basándote en el contexto de normativas y guías que se te proporciona a continuación.

CONTRATO DE RESPUESTA (ESTRICTO):
1. CASOS DE INTERACCIÓN GENERAL (SALUDOS, AGRADECIMIENTOS Y DESPEDIDAS):
   - Queda terminantemente prohibido saludar, dar la bienvenida o presentarse si la consulta del usuario es una pregunta o solicitud de información específica sobre reglamentos, requisitos o trámites. En esos casos, responde de forma directa, concisa y sin preámbulos ni introducciones de ningún tipo.
   - Solo debes dar la bienvenida y presentarte como el Asistente Virtual de Becas de la UNL si el mensaje del usuario consiste únicamente en un saludo simple (ej. "Hola", "Buenos días", "¿Qué tal?") y no contiene ninguna pregunta sobre la normativa.
   - Si el usuario agradece o se despide (ej. "Gracias", "Entendido, muchas gracias", "Adiós"), responde con amabilidad, cortesía y disposición a ayudar.
2. CASOS FUERA DE ÁMBITO (OUT-OF-SCOPE):
   - Si el usuario realiza una pregunta sobre temas completamente ajenos a los reglamentos de becas, incentivos estudiantiles o trámites de la UNL (como recetas de cocina, historia universal, programación, etc.), indícale de forma educada que tu rol se limita exclusivamente a asesorar sobre la normativa de becas e incentivos de la UNL y que no puedes responder consultas de otros ámbitos.
3. CASOS DE NORMATIVA SIN DATOS SUFICIENTES:
   - Solo si el usuario pregunta sobre la normativa de becas de la UNL pero el Contexto provisto no contiene información relacionada o suficiente para responderla, debes responder exactamente:
     "No dispongo de suficiente información en la normativa cargada para responder a esa consulta."
4. RIGOR DE INFORMACIÓN PARA PREGUNTAS VÁLIDAS:
   - Responde la pregunta del usuario utilizando la información provista en el Contexto. Queda prohibido añadir información externa o conocimiento previo que no esté soportado por los documentos.
   - Realiza deducciones lógicas y comparaciones matemáticas elementales basadas estrictamente en las reglas y números provistos en el contexto (por ejemplo, calcular porcentajes de asistencia).
   - Si la consulta pregunta por enlaces URL de descarga o requisitos técnicos (como el enlace del Ministerio de Trabajo https://calculadoras.trabajo.gob.ec/dependencia, el enlace de la plataforma del IESS o el peso de 2 MB para PDFs), es obligatorio que los cites textualmente.
5. No uses la palabra "contexto" o "normativa cargada" para iniciar o explicar tu respuesta. Responde directamente.
6. Al final de tu respuesta, añade una línea en blanco seguida de una única línea especial que liste las fuentes exactas que utilizaste para responder, delimitadas por corchetes angulares y separadas por comas. Sigue estrictamente este formato:
    - Si usaste información de la Guía de Becas MD, incluye: <Guia_MGT_MD>
    - Si usaste información de la Tabla de Requisitos MD, incluye: <Requisitos_Tramite_MD>
    - Si usaste información de una página del Reglamento PDF, incluye: <Reglamento_PDF_Pag_X> (donde X es el número de página física que aparece en el texto del fragmento, por ejemplo: <Reglamento_PDF_Pag_10>).
    - Pon todos los que correspondan en una sola línea. Ejemplo: [FUENTES_USADAS: <Guia_MGT_MD>, <Requisitos_Tramite_MD>, <Reglamento_PDF_Pag_10>]
   - Si no respondes la pregunta, saludas, agradeces o es fuera de ámbito, pon exactamente: [FUENTES_USADAS: Ninguna]

{chat_history}Contexto:
{context}

Pregunta del usuario:
{question}

Respuesta del asistente:"""

MODELOS_GROQ_FALLBACK = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama-3.2-3b-preview"
]

def llamar_nvidia_api(prompt_text: str, model_name: str, api_key: str, max_tokens: int = 1024) -> str:
    """
    Invocación directa HTTP nativa a Nvidia NIM compatible con OpenAI.
    Evita instalar librerías propietarias adicionales en el entorno virtual.
    """
    url = "https://integrate.api.nvidia.com/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    # Separar en system y user messages para evitar simulaciones de diálogo por parte del modelo
    parts = prompt_text.split("Contexto:")
    if len(parts) >= 2:
        system_content = parts[0].strip()
        user_content = "Contexto:" + "Contexto:".join(parts[1:]).replace("Respuesta del asistente:", "").strip()
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]
    else:
        messages = [
            {"role": "user", "content": prompt_text}
        ]

    print(f"-> Nvidia API Payload - Messages count: {len(messages)}")
    for idx_msg, msg in enumerate(messages):
        snippet_msg = msg['content'][:120].replace('\n', ' ').strip()
        print(f"   [{idx_msg}] Role: {msg['role']} | Content length: {len(msg['content'])} | Snippet: {snippet_msg}...")

    data = {
        "model": model_name,
        "messages": messages,
        "temperature": 0.0,
        "max_tokens": max_tokens
    }
    
    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers=headers,
        method="POST"
    )
    
    with urllib.request.urlopen(req, timeout=12) as response:
        res_data = json.loads(response.read().decode("utf-8"))
        return res_data["choices"][0]["message"]["content"].strip()

def reescribir_consulta(query: str, nvidia_key: str, groq_key: str) -> tuple[str, str]:
    """
    Simplifica la consulta del usuario extrayendo estrictamente palabras clave (keywords)
    de alta densidad informativa, eliminando conectores, artículos y palabras genéricas obvias
    (ej. 'becas', 'universidad', 'estudiante') para maximizar la precisión en ChromaDB.
    """
    prompt = f"""Extrae de la siguiente consulta de un estudiante únicamente las 3 o 5 palabras clave (keywords) de alta densidad informativa que sirvan para buscar en un reglamento.
REGLAS ESTRICTAS:
1. Devuelve únicamente los términos de búsqueda separados por espacios, sin comillas, sin preposiciones, sin artículos y sin conectores.
2. Queda prohibido incluir palabras genéricas obvias como: 'beca', 'becas', 'universidad', 'estudiante', 'estudiantes', 'información', 'requisito', 'requisitos'.
3. No des explicaciones, introducciones ni respondas la pregunta. Solo los términos.

Consulta: {query}
Términos de búsqueda:"""

    # 1. Intentar con Nvidia NIM (Principal)
    if nvidia_key:
        try:
            consulta_opt = llamar_nvidia_api(prompt, "meta/llama-3.1-8b-instruct", nvidia_key, max_tokens=30)
            consulta_opt = consulta_opt.replace('"', '').replace("'", "").strip()
            print(f"-> Consulta original: '{query}'")
            print(f"-> Palabras clave extraídas por Nvidia: '{consulta_opt}'")
            return consulta_opt, "Nvidia (meta/llama-3.1-8b-instruct)"
        except Exception as e:
            print(f"-> Advertencia: Falló extracción con Nvidia. Error: {e}. Intentando fallback con Groq...")

    # 2. Fallback secuencial con modelos de Groq
    if groq_key:
        for modelo in MODELOS_GROQ_FALLBACK:
            try:
                llm_rewrite = ChatGroq(
                    model=modelo,
                    temperature=0.0,
                    groq_api_key=groq_key,
                    max_tokens=30
                )
                res = llm_rewrite.invoke(prompt)
                consulta_opt = res.content.strip().replace('"', '').replace("'", "").strip()
                print(f"-> Palabras clave extraídas por Groq ({modelo}): '{consulta_opt}'")
                return consulta_opt, f"Groq ({modelo})"
            except Exception as e:
                print(f"-> Advertencia: Falló extracción con Groq ({modelo}): {e}. Intentando siguiente fallback...")
                
    print("-> Error: Todos los modelos fallaron en la extracción. Usando consulta original.")
    return query, "Ninguno (Uso de Consulta Original)"

def procesar_respuesta_y_filtrar_fuentes(respuesta_cruda: str, fuentes_contexto: list) -> tuple[str, list]:
    """
    Parsea la respuesta del LLM para extraer las fuentes declaradas en la línea [FUENTES_USADAS: ...],
    limpia esa línea del texto final de la respuesta y devuelve una lista filtrada conteniendo
    exclusivamente los metadatos de las fuentes que el modelo declaró haber utilizado.
    """
    patron = r'\[FUENTES_USADAS:\s*(.*?)\]'
    coincidencia = re.search(patron, respuesta_cruda, re.DOTALL)
    
    if not coincidencia:
        return respuesta_cruda, fuentes_contexto
        
    fuentes_texto_crudo = coincidencia.group(1).strip()
    respuesta_limpia = re.sub(patron, "", respuesta_cruda).strip()
    
    if "Ninguna" in fuentes_texto_crudo or fuentes_texto_crudo.lower() == "ninguna":
        return respuesta_limpia, []
        
    tags_encontrados = re.findall(r'<(.*?)>', fuentes_texto_crudo)
    
    fuentes_filtradas = []
    for tag in tags_encontrados:
        tag = tag.strip()
        if tag == "Guia_MGT_MD":
            for f in fuentes_contexto:
                if f["source"] == "Guia_MGT_MD":
                    if f not in fuentes_filtradas:
                        fuentes_filtradas.append(f)
        elif tag == "Requisitos_Tramite_MD":
            for f in fuentes_contexto:
                if f["source"] == "Requisitos_Tramite_MD":
                    if f not in fuentes_filtradas:
                        fuentes_filtradas.append(f)
        elif tag.startswith("Reglamento_PDF_Pag_"):
            try:
                num_pag_fisica = int(tag.replace("Reglamento_PDF_Pag_", ""))
                page_idx = num_pag_fisica - 1
                for f in fuentes_contexto:
                    if f["source"] == "Reglamento_PDF" and f["page"] == page_idx:
                        if f not in fuentes_filtradas:
                            fuentes_filtradas.append(f)
            except Exception:
                pass
                
    if not fuentes_filtradas and tags_encontrados:
        return respuesta_limpia, fuentes_contexto
        
    return respuesta_limpia, fuentes_filtradas

def ejecutar_consulta(query: str, retriever, nvidia_key: str, groq_key: str, historial: list = None) -> tuple[str, list, str, str, float, float, str]:
    """
    Ejecuta el flujo RAG midiendo latencias y capturando el prompt formateado final.
    Prioriza Nvidia NIM como principal y cae automáticamente a Groq (multi-modelo) en caso de TPM/RPM.
    Soporta historial conversacional en caliente para proveer memoria conversacional al LLM.
    Retorna: (respuesta, fuentes, contexto, prompt_final, latencia_retrieval, latencia_inference, modelo_activo)
    """
    # 1. Reformular la consulta para ChromaDB
    query_opt, modelo_reescritura = reescribir_consulta(query, nvidia_key, groq_key)

    # 2. Recuperar los documentos midiendo latencia con la consulta reformulada
    t0 = time.time()
    docs = retriever.invoke(query_opt)
    
    # --- RECUPERADOR HÍBRIDO (Búsqueda Léxica de Respaldo) ---
    try:
        import re
        from langchain_core.documents import Document
        
        # Extraer palabras de la consulta original
        palabras_consulta = re.findall(r'[a-zA-ZáéíóúüñÁÉÍÓÚÜÑ]{4,}', query.lower())
        palabras_excluir = {"para", "como", "esta", "este", "estos", "estas", "unos", "unas", "sino", "pero", "sobre", "entre", "tiene", "tienen", "será", "serán"}
        keywords_query = {p for p in palabras_consulta if p not in palabras_excluir}
        
        db_chroma = retriever.vectorstore
        todos_los_docs = db_chroma._collection.get()
        contents = todos_los_docs.get("documents", [])
        metadatas = todos_los_docs.get("metadatas", [])
        
        docs_lexicos = []
        # Evaluar coincidencia para palabras críticas específicas
        keywords_criticas = {
            "excelencia", "académica", "iess", "afiliado", "afiliacion", "afiliación", 
            "certificado", "trabajo", "rol", "pagos", "peso", "límite", "archivo",
            "artístico", "cultural", "deportivo", "deportivos",
            "asistencia", "clases", "faltar", "falta", "falté", "pérdida", "perder", "pierdo", "mantener", "mantenimiento",
            "requisito", "requisitos", "gratuidad", "matrícula", "matricula", "segunda", "fase"
        }
        hay_criticas = any(k in keywords_query for k in keywords_criticas)
        
        if hay_criticas:
            for content, meta in zip(contents, metadatas):
                content_lower = content.lower()
                coincide = False
                
                # Caso A: Excelencia Académica (Art. 28 y 30)
                if "excelencia" in keywords_query and ("excelencia" in content_lower or "art. 28" in content_lower or "art. 30" in content_lower):
                    coincide = True
                # Caso B: Certificados, IESS, Trabajo, Rol, Descargas (Ministerio de Trabajo y 2 MB)
                elif any(x in keywords_query for x in ["iess", "afiliado", "afiliacion", "afiliación", "certificado", "trabajo", "rol", "pagos", "peso", "límite", "archivo"]):
                    if "calculadoras.trabajo.gob.ec" in content_lower or "afiliado-web" in content_lower or "art. 25" in content_lower or "iess" in content_lower:
                        coincide = True
                # Caso C: Grupos Artísticos/Culturales (Art. 26-27)
                elif any(x in keywords_query for x in ["artístico", "cultural", "deportivo"]) and ("art. 26" in content_lower or "art. 27" in content_lower or "grupo" in content_lower):
                    coincide = True
                # Caso D: Asistencia, Mantenimiento y Pérdida (Art. 23 y 38)
                elif any(x in keywords_query for x in ["asistencia", "clases", "faltar", "falta", "falté", "pérdida", "perder", "pierdo", "mantener", "mantenimiento"]):
                    if "art. 23" in content_lower or "art. 38" in content_lower or "asistencia" in content_lower or "mantenimiento" in content_lower:
                        coincide = True
                # Caso E: Requisitos de trámite, gratuidad, segunda matrícula
                elif any(x in keywords_query for x in ["requisito", "requisitos", "gratuidad", "matrícula", "matricula", "segunda", "fase"]):
                    if "requisitos necesarios" in content_lower or "segunda matrícula" in content_lower or "gratuidad" in content_lower or "fase 1" in content_lower:
                        coincide = True
                    
                if coincide:
                    # Evitar duplicar si ya fue devuelto por el retriever vectorial
                    ya_existe = False
                    for d in docs:
                        if d.page_content.strip() == content.strip():
                            ya_existe = True
                            break
                    if not ya_existe:
                        docs_lexicos.append(Document(page_content=content, metadata=meta))
            
            if docs_lexicos:
                # Ordenar docs_lexicos por densidad de coincidencia de keywords del usuario
                docs_lexicos.sort(
                    key=lambda d: sum(1 for kw in keywords_query if kw in d.page_content.lower()),
                    reverse=True
                )
                print(f"-> Recuperador Híbrido: Se inyectaron {min(len(docs_lexicos), 5)} fragmentos de coincidencia léxica ordenados.")
                # Tomar los 5 más relevantes y unirlos a la búsqueda semántica
                docs = list(docs_lexicos[:5]) + list(docs)
    except Exception as ex_hybrid:
        print(f"-> Advertencia en Recuperador Híbrido: {ex_hybrid}")

    latencia_retrieval = time.time() - t0
    
    # 3. Estructurar la lista de fuentes para la UI
    fuentes = []
    for doc in docs:
        fuentes.append({
            "content": doc.page_content,
            "source": doc.metadata.get("source", "Desconocido"),
            "page": doc.metadata.get("page", None)
        })
    
    # 4. Construir el bloque de contexto
    contexto = "\n\n---\n\n".join([doc.page_content for doc in docs])
    
    # Formatear el historial reciente de chat
    chat_history_str = ""
    if historial:
        chat_history_str = "Historial reciente de la conversación:\n"
        for msg in historial[-4:]:
            role_label = "Estudiante" if (getattr(msg, 'role', '') == 'user' or (isinstance(msg, dict) and msg.get('role') == 'user')) else "Asistente"
            content_val = getattr(msg, 'content', '') if not isinstance(msg, dict) else msg.get('content', '')
            chat_history_str += f"- {role_label}: {content_val}\n"
        chat_history_str += "\n"

    # 5. Formatear el prompt final para auditoría
    prompt_template_obj = ChatPromptTemplate.from_template(PROMPT_TEMPLATE)
    prompt_final_val = prompt_template_obj.format(chat_history=chat_history_str, context=contexto, question=query)
    
    # 6. Intentar la inferencia priorizando Nvidia y con fallback a Groq
    t1 = time.time()
    ultimo_error = None
    
    # A. Intentar Nvidia NIM (Principal)
    if nvidia_key:
        try:
            respuesta = llamar_nvidia_api(prompt_final_val, "meta/llama-3.1-8b-instruct", nvidia_key, max_tokens=1024)
            latencia_inference = time.time() - t1
            respuesta_final, fuentes_finales = procesar_respuesta_y_filtrar_fuentes(respuesta, fuentes)
            print("-> Inferencia exitosa usando Nvidia NIM (meta/llama-3.1-8b-instruct)")
            return respuesta_final, fuentes_finales, contexto, prompt_final_val, round(latencia_retrieval, 4), round(latencia_inference, 4), "Nvidia (meta/llama-3.1-8b-instruct)"
        except Exception as e:
            ultimo_error = e
            print(f"-> Error en inferencia con Nvidia NIM: {e}. Activando fallback a Groq...")
            
    # B. Intentar Groq (Fallback)
    if groq_key:
        for modelo in MODELOS_GROQ_FALLBACK:
            try:
                llm = ChatGroq(
                    model=modelo,
                    temperature=0.0,
                    groq_api_key=groq_key
                )
                chain = prompt_template_obj | llm | StrOutputParser()
                respuesta = chain.invoke({
                    "chat_history": chat_history_str,
                    "context": contexto,
                    "question": query
                })
                latencia_inference = time.time() - t1
                respuesta_final, fuentes_finales = procesar_respuesta_y_filtrar_fuentes(respuesta, fuentes)
                print(f"-> Inferencia exitosa usando Groq ({modelo})")
                return respuesta_final, fuentes_finales, contexto, prompt_final_val, round(latencia_retrieval, 4), round(latencia_inference, 4), f"Groq ({modelo})"
            except Exception as e:
                ultimo_error = e
                print(f"-> Error en inferencia con Groq ({modelo}): {e}. Probando siguiente modelo de respaldo...")
                
    # Si todo falla, lanzamos la excepción final
    raise RuntimeError(f"Error crítico de RAG: Todos los proveedores (Nvidia y Groq) fallaron. Último error: {str(ultimo_error)}")
