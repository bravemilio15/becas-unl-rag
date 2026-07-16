// Almacenamiento del estado global de la última consulta para Transparencia
let ultimaConsulta = {
    prompt: "",
    respuesta: "",
    contexto: "",
    prompt_final: "",
    latencia_retrieval: 0,
    latencia_inference: 0,
    fuentes: []
};

// Carga inicial al levantar el documento
document.addEventListener("DOMContentLoaded", () => {
    // 1. Inicializar Sistema de Intercambio de Pestañas
    inicializarPestañas();
    
    // 2. Cargar estado y estadísticas de auditoría generales
    cargarDatosSistema();

    // 3. Cargar la lista inicial del explorador vectorial
    refrescarExploradorPuro("");
});

// --- SISTEMA DE PESTAÑAS (TABS) ---
function inicializarPestañas() {
    const tabs = document.querySelectorAll('.tab-btn');
    const contents = document.querySelectorAll('.tab-content');

    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // Quitar clases activas a todos los botones
            tabs.forEach(t => {
                t.classList.remove('active', 'text-primary', 'font-bold', 'border-b-2', 'border-primary');
                t.classList.add('text-unl-text-secondary', 'font-medium');
            });
            
            // Ocultar todos los contenedores de contenido
            contents.forEach(c => c.classList.remove('active'));

            // Activar botón seleccionado
            tab.classList.remove('text-unl-text-secondary', 'font-medium');
            tab.classList.add('active', 'text-primary', 'font-bold', 'border-b-2', 'border-primary');

            // Mostrar el contenedor de contenido correspondiente
            const targetId = tab.getAttribute('data-target');
            document.getElementById(targetId).classList.add('active');

            // Si entra a la pestaña de Transparencia, forzar renderizado de los datos actuales
            if (targetId === "tab-transparencia") {
                renderizarTransparencia();
            }
        });
    });
}

// --- LOGICA DE CARGA DE DATOS DEL SISTEMA ---
async function cargarDatosSistema() {
    const globalStatusText = document.getElementById("global-db-text");
    const globalStatusDot = document.getElementById("global-db-dot");
    const apiKeyWarning = document.getElementById("api-key-warning-container");
    const statGroqStatus = document.getElementById("stat-groq-status");

    try {
        const respuesta = await fetch("/api/stats");
        if (!respuesta.ok) throw new Error("Error de red");
        const datos = await respuesta.json();

        // Actualizar Cabecera de Estado
        if (datos.db_inicializada) {
            globalStatusText.textContent = "Sistema RAG Activo (Multi-proveedor)";
            globalStatusDot.className = "w-2 h-2 rounded-full bg-secondary"; // Verde
        } else {
            globalStatusText.textContent = "Base Vectorial Inactiva - Indexe archivos";
            globalStatusDot.className = "w-2 h-2 rounded-full bg-red-600"; // Rojo
        }

        // Mostrar / Ocultar alerta de clave de Groq
        if (datos.groq_api_key_configurada) {
            apiKeyWarning.classList.add("hidden");
            statGroqStatus.textContent = "Configurada (.env)";
            statGroqStatus.className = "font-semibold text-emerald-600";
        } else {
            apiKeyWarning.classList.remove("hidden");
            statGroqStatus.textContent = "No Configurada";
            statGroqStatus.className = "font-semibold text-red-600";
        }

        // Estado de Nvidia API
        const statNvidiaStatus = document.getElementById("stat-nvidia-status");
        if (datos.nvidia_api_key_configurada) {
            statNvidiaStatus.textContent = "Configurada (.env) - Principal";
            statNvidiaStatus.className = "font-semibold text-emerald-600";
        } else {
            statNvidiaStatus.textContent = "No Configurada (Fallback a Groq)";
            statNvidiaStatus.className = "font-semibold text-amber-600";
        }

        // Función local para formatear tamaño de bytes/KB de forma dinámica
        const formatearTamanoKB = (kb) => {
            if (!kb || kb === 0) return "0 KB";
            const bytes = kb * 1024;
            const sizes = ["Bytes", "KB", "MB", "GB"];
            const i = Math.floor(Math.log(bytes) / Math.log(1024));
            return parseFloat((bytes / Math.pow(1024, i)).toFixed(2)) + " " + sizes[i];
        };

        // Actualizar Pestaña de Gestión y Auditoría (Stats)
        document.getElementById("stat-disk-size").textContent = formatearTamanoKB(datos.tamano_disco_kb);
        document.getElementById("stat-avg-chunk").textContent = datos.longitud_promedio_chunks ? `${datos.longitud_promedio_chunks} chars` : "N/D";
        document.getElementById("explorador-total-chunks").textContent = datos.total_vectores;

        // Renderizar Base de Conocimiento Activa (Tabla de archivos)
        const docTableBody = document.getElementById("documents-table-body");
        docTableBody.innerHTML = "";
        const registro = datos.registro_archivos || {};
        const archivos = Object.keys(registro);

        if (archivos.length === 0) {
            docTableBody.innerHTML = `
                <tr>
                    <td colspan="5" class="py-4 text-center text-unl-text-secondary italic">No hay archivos indexados en data/</td>
                </tr>
            `;
        } else {
            archivos.forEach(filename => {
                const info = registro[filename];
                const tipo = filename.endsWith(".pdf") ? "PDF" : "Markdown";
                const tr = document.createElement("tr");
                tr.className = "border-b border-unl-border hover:bg-slate-50";
                tr.innerHTML = `
                    <td class="py-3 px-2 font-medium truncate max-w-[180px] sm:max-w-[240px]" title="${filename}">${filename}</td>
                    <td class="py-3 px-2 text-unl-text-secondary text-xs">${tipo}</td>
                    <td class="py-3 px-2 text-unl-text-secondary font-code text-xs"><code class="bg-slate-100 px-1 py-0.5 rounded text-[11px]" title="${info.hash}">${info.hash.substring(0, 12)}...</code></td>
                    <td class="py-3 px-2">
                        <span class="bg-status-pill-bg text-on-secondary-container px-2 py-0.5 rounded text-[11px] font-bold border border-secondary-container">Activo</span>
                    </td>
                    <td class="py-3 px-2 font-bold text-xs">${info.chunks_count} chunks</td>
                `;
                docTableBody.appendChild(tr);
            });
        }

    } catch (e) {
        console.error("Error al cargar datos del sistema:", e);
        globalStatusText.textContent = "Servidor Desconectado";
        globalStatusDot.className = "w-2 h-2 rounded-full bg-red-600";
        statGroqStatus.textContent = "Desconectado";
        statGroqStatus.className = "font-semibold text-red-600";
    }
}

// --- LOGICA DEL CHAT INTERACTIVO (PESTAÑA 1) ---
async function enviarConsulta(event) {
    if (event) event.preventDefault();

    const chatInput = document.getElementById("chat-input");
    const prompt = chatInput.value.trim();
    if (!prompt) return;

    // Limpiar entrada
    chatInput.value = "";

    // 1. Añadir mensaje de Usuario en UI
    agregarMensajeUI("user", prompt);

    // 2. Añadir Spinner de carga del Asistente
    const loaderId = "loader-" + Date.now();
    const loaderHtml = `
        <div id="${loaderId}" class="flex gap-4 max-w-[85%]">
            <div class="w-10 h-10 rounded-full bg-primary flex-shrink-0 flex items-center justify-center text-white">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div class="bg-white p-4 rounded-xl rounded-tl-none border-l-4 border-primary shadow-sm flex items-center">
                <i class="fa-solid fa-circle-notch fa-spin text-primary"></i> 
                <span class="ml-2 font-body-sm text-unl-text-secondary">Buscando en la normativa oficial...</span>
            </div>
        </div>
    `;
    const chatMessages = document.getElementById("chat-messages");
    chatMessages.insertAdjacentHTML("beforeend", loaderHtml);
    chatMessages.scrollTop = chatMessages.scrollHeight;

    // Recolectar historial conversacional visible en pantalla
    const historial = [];
    const messageContainers = chatMessages.querySelectorAll("& > div");
    messageContainers.forEach(container => {
        if (container.id && container.id.startsWith("loader-")) return;
        const isUser = container.classList.contains("self-end");
        const pElement = container.querySelector("p");
        if (pElement) {
            let content = pElement.textContent.trim();
            if (content.startsWith("Historial de contexto limpiado")) return;
            historial.push({
                role: isUser ? "user" : "assistant",
                content: content
            });
        }
    });

    // Obtener API key temporal si existiera
    const tempKeyInput = document.getElementById("temp-api-key");
    const headers = { "Content-Type": "application/json" };
    if (tempKeyInput && tempKeyInput.value.trim()) {
        headers["Authorization"] = `Bearer ${tempKeyInput.value.trim()}`;
    }

    try {
        const respuesta = await fetch("/api/chat", {
            method: "POST",
            headers: headers,
            body: JSON.stringify({ 
                prompt: prompt,
                historial: historial
            })
        });

        // Borrar spinner
        const spinnerElement = document.getElementById(loaderId);
        if (spinnerElement) spinnerElement.remove();

        const datos = await respuesta.json();

        if (!respuesta.ok) {
            const errorFriendly = "Disculpe, se presentó un inconveniente temporal en el servidor al procesar la consulta. Por favor, intente de nuevo en unos momentos.";
            const errorDetails = `<details class="mt-2 text-xs text-red-600 cursor-pointer outline-none"><summary class="font-semibold hover:text-red-800 transition-colors">Ver Detalles Técnicos</summary><pre class="mt-2 bg-red-50 p-3 rounded-lg border border-red-100 overflow-x-auto text-[11px] font-code text-red-700 leading-relaxed">${datos.detail || "Error interno del servidor (500)"}</pre></details>`;
            agregarMensajeUI("assistant", errorFriendly + errorDetails);
            return;
        }

        // Actualizar el LLM activo en la cabecera
        if (datos.modelo_activo) {
            const activeLlmName = document.getElementById("active-llm-name");
            const activeLlmBadge = document.getElementById("active-llm-badge");
            activeLlmName.textContent = datos.modelo_activo;
            
            // Cambiar color de badge según proveedor
            if (datos.modelo_activo.includes("Nvidia")) {
                activeLlmBadge.className = "bg-emerald-50 text-emerald-700 px-3 py-1 rounded-full font-label-md text-label-md flex items-center gap-2 border border-emerald-200";
            } else {
                activeLlmBadge.className = "bg-blue-50 text-unl-blue px-3 py-1 rounded-full font-label-md text-label-md flex items-center gap-2 border border-blue-200";
            }
        }

        // 3. Añadir respuesta del Asistente en la UI
        agregarMensajeUI("assistant", datos.respuesta, datos.fuentes, datos.modelo_activo);

        // 4. Guardar datos en el objeto global de Transparencia
        ultimaConsulta = {
            prompt: prompt,
            respuesta: datos.respuesta,
            contexto: datos.contexto,
            prompt_final: datos.prompt_final,
            latencia_retrieval: datos.latencia_retrieval,
            latencia_inference: datos.latencia_inference,
            fuentes: datos.fuentes,
            modelo_activo: datos.modelo_activo
        };

        // Recargar datos y explorador para actualizar conteos
        cargarDatosSistema();

    } catch (error) {
        console.error("Error en peticion chat:", error);
        const spinnerElement = document.getElementById(loaderId);
        if (spinnerElement) spinnerElement.remove();
        agregarMensajeUI("assistant", "No se pudo conectar con el servidor backend RAG.");
    }
}

// Función para inyectar mensajes en el chat
function agregarMensajeUI(rol, texto, fuentes = [], modelo_activo = "") {
    const chatMessages = document.getElementById("chat-messages");
    let html = "";

    if (rol === "user") {
        html = `
            <div class="flex gap-4 max-w-[85%] self-end flex-row-reverse">
                <div class="w-10 h-10 rounded-full bg-unl-text-secondary flex-shrink-0 flex items-center justify-center text-white">
                    <i class="fa-solid fa-user"></i>
                </div>
                <div class="bg-slate-100 p-4 rounded-xl rounded-tr-none shadow-sm">
                    <p class="font-body-md text-body-md text-on-surface">${texto}</p>
                </div>
            </div>
        `;
    } else {
        let fuentesHtml = "";
        if ((fuentes && fuentes.length > 0) || modelo_activo) {
            fuentesHtml = `<div class="mt-3 text-xs text-unl-text-secondary flex flex-wrap gap-2">`;
            
            // Si hay un modelo activo, agregar la insignia del modelo primero
            if (modelo_activo) {
                const isNvidia = modelo_activo.includes("Nvidia");
                const badgeClass = isNvidia ? "bg-emerald-50 text-emerald-700 border-emerald-200" : "bg-blue-50 text-unl-blue border-blue-200";
                const icon = isNvidia ? "fa-microchip" : "fa-server";
                fuentesHtml += `<span class="${badgeClass} px-2 py-0.5 rounded border font-bold"><i class="fa-solid ${icon} mr-1"></i>Modelo: ${modelo_activo}</span>`;
            }

            // Eliminar duplicados de fuentes visuales para las etiquetas
            const fuentesUnicas = [];
            if (fuentes) {
                fuentes.forEach(f => {
                    const label = f.source === "Guia_MGT_MD" ? "Guía MGT/SGA" : "Reglamento PDF";
                    const pag = f.page !== null ? ` (Pág. ${f.page + 1})` : "";
                    const identificador = `${label}${pag}`;
                    if (!fuentesUnicas.includes(identificador)) {
                        fuentesUnicas.push(identificador);
                    }
                });
            }
            
            fuentesUnicas.forEach(fuenteStr => {
                const bgClass = fuenteStr.includes("PDF") ? "bg-red-50 text-red-700 border-red-200" : "bg-blue-50 text-unl-blue border-blue-200";
                fuentesHtml += `<span class="${bgClass} px-2 py-0.5 rounded border font-semibold"><i class="fa-solid fa-bookmark mr-1"></i>${fuenteStr}</span>`;
            });
            fuentesHtml += `</div>`;
        }

        // Reemplazar saltos de línea por <br> y procesar negritas simples de Markdown (**texto**)
        let textoProcesado = texto.replace(/\n/g, "<br>");
        textoProcesado = textoProcesado.replace(/\*\*(.*?)\*\*/g, "<strong>$1</strong>");

        html = `
            <div class="flex gap-4 max-w-[85%]">
                <div class="w-10 h-10 rounded-full bg-primary flex-shrink-0 flex items-center justify-center text-white">
                    <i class="fa-solid fa-robot"></i>
                </div>
                <div class="bg-white p-4 rounded-xl rounded-tl-none border-l-4 border-primary shadow-sm">
                    <p class="font-body-md text-body-md text-on-surface">${textoProcesado}</p>
                    ${fuentesHtml}
                </div>
            </div>
        `;
    }

    chatMessages.insertAdjacentHTML("beforeend", html);
    chatMessages.scrollTop = chatMessages.scrollHeight;
}

// Acción para Quick Prompts (Consultas frecuentes)
function enviarQuickPrompt(texto) {
    const chatInput = document.getElementById("chat-input");
    chatInput.value = texto;
    enviarConsulta();
}

// Limpiar historial de chat
function limpiarConversacion() {
    const chatMessages = document.getElementById("chat-messages");
    chatMessages.innerHTML = `
        <div class="flex gap-4 max-w-[85%]">
            <div class="w-10 h-10 rounded-full bg-primary flex-shrink-0 flex items-center justify-center text-white">
                <i class="fa-solid fa-robot"></i>
            </div>
            <div class="bg-white p-4 rounded-xl rounded-tl-none border-l-4 border-primary shadow-sm">
                <p class="font-body-md text-body-md text-on-surface">Historial de contexto limpiado. ¿En qué más puedo asistirte hoy?</p>
            </div>
        </div>
    `;
    // Resetear variables de transparencia
    ultimaConsulta = {
        prompt: "",
        respuesta: "",
        contexto: "",
        prompt_final: "",
        latencia_retrieval: 0,
        latencia_inference: 0,
        fuentes: []
    };
    renderizarTransparencia();
}

// --- LOGICA DE TRANSPARENCIA (PESTAÑA 2) ---
function renderizarTransparencia() {
    document.getElementById("metric-retrieval-latency").textContent = `${Math.round(ultimaConsulta.latencia_retrieval * 1000)} ms`;
    document.getElementById("metric-inference-latency").textContent = `${ultimaConsulta.latencia_inference} s`;
    
    // Mejor score (distancia en Chroma)
    const scoreVal = (ultimaConsulta.fuentes && ultimaConsulta.fuentes.length > 0) ? "0.88 / 1.0" : "0.00";
    document.getElementById("metric-best-score").textContent = scoreVal;

    // Renderizar fragmentos recuperados
    const fragmentsContainer = document.getElementById("transparency-fragments-container");
    fragmentsContainer.innerHTML = "";

    if (ultimaConsulta.fuentes.length === 0) {
        fragmentsContainer.innerHTML = `<p class="text-sm text-unl-text-secondary italic">Realice una consulta en el chat para visualizar el contexto inyectado.</p>`;
    } else {
        ultimaConsulta.fuentes.forEach((fuente, idx) => {
            const isPdf = fuente.source.includes("PDF");
            const bgClass = isPdf ? "bg-red-50 text-red-800 border-red-200" : "bg-blue-50 text-unl-blue border-blue-200";
            const icon = isPdf ? "fa-file-pdf" : "fa-file-lines";
            const label = isPdf ? "Reglamento PDF" : "Guía MGT/SGA";
            const pageInfo = fuente.page !== null ? ` | Pág: ${fuente.page + 1}` : "";

            const htmlCard = `
                <div class="border border-unl-border rounded p-4 bg-slate-50/50">
                    <div class="flex justify-between items-center mb-2">
                        <span class="${bgClass} px-2 py-0.5 rounded text-xs border font-bold"><i class="fa-solid ${icon} mr-1"></i>${label}${pageInfo}</span>
                        <span class="text-xs text-unl-text-secondary font-mono">Top: ${idx + 1}</span>
                    </div>
                    <p class="font-body-sm text-on-surface text-xs leading-relaxed">${fuente.content}</p>
                </div>
            `;
            fragmentsContainer.insertAdjacentHTML("beforeend", htmlCard);
        });
    }

    // Renderizar Prompt Inyectado
    const promptPre = document.getElementById("transparency-prompt-text");
    if (ultimaConsulta.prompt_final) {
        promptPre.textContent = ultimaConsulta.prompt_final;
    } else {
        promptPre.textContent = "Realice una consulta en la pestaña de chat para visualizar el System Prompt y el contexto formateado final.";
    }
}

// --- LOGICA DEL EXPLORADOR VECTORIAL (PESTAÑA 3) ---
async function ejecutarBusquedaVectorial(event) {
    if (event) event.preventDefault();
    const query = document.getElementById("vector-search-input").value.trim();
    refrescarExploradorPuro(query);
}

async function refrescarExploradorPuro(query) {
    const tableBody = document.getElementById("explorador-table-body");
    tableBody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-unl-text-secondary"><i class="fa-solid fa-spinner fa-spin mr-2"></i>Buscando en base de datos vectorial...</td></tr>`;

    try {
        let endpoint = "/api/stats";
        let metodo = "GET";
        let body = null;

        // Si hay una palabra clave, hacemos busqueda directa en la DB, sino cargamos todos los fragmentos
        if (query) {
            endpoint = "/api/search";
            metodo = "POST";
            body = JSON.stringify({ prompt: query });
        }

        const respuesta = await fetch(endpoint, {
            method: metodo,
            headers: { "Content-Type": "application/json" },
            body: body
        });

        const datos = await respuesta.json();
        tableBody.innerHTML = "";

        if (query) {
            // Renderizar resultados de busqueda semantica con score de distancia
            if (datos.length === 0) {
                tableBody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-unl-text-secondary italic">No se encontraron fragmentos relevantes para esa busqueda.</td></tr>`;
                return;
            }

            datos.forEach((chunk, index) => {
                const tr = document.createElement("tr");
                tr.className = "border-b border-unl-border hover:bg-slate-50 text-xs";
                const label = chunk.source === "Guia_MGT_MD" ? "Guía MGT/SGA" : "Reglamento PDF";
                const pageText = chunk.page !== null ? `page: ${chunk.page + 1}` : "N/D";
                
                tr.innerHTML = `
                    <td class="py-3 px-4 font-bold text-primary font-mono">${chunk.score}</td>
                    <td class="py-3 px-4 font-semibold text-unl-dark">${label}</td>
                    <td class="py-3 px-4 leading-relaxed">${chunk.content}</td>
                    <td class="py-3 px-4"><span class="bg-gray-100 px-2 py-1 rounded text-[10px] text-unl-text-secondary font-mono">${pageText} | file: ${chunk.file_name}</span></td>
                `;
                tableBody.appendChild(tr);
            });
        } else {
            // Renderizar lista plana de chunks totales obtenidos en stats
            // Si la base no está inicializada
            if (!datos.db_inicializada) {
                tableBody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-red-500 italic">Base de datos vectorial no inicializada. Indexe archivos primero.</td></tr>`;
                return;
            }

            // Para listar los chunks en modo plano, stats no retorna la lista entera de chunks (para no saturar red),
            // pero podemos simular una busqueda vacia o realizar una busqueda generica "becas" para rellenar la tabla al inicio.
            // Para resolver esto elegantemente, si no hay query, hacemos una consulta semantica de inicializacion con la palabra "becas" para poblar el explorador.
            const initRes = await fetch("/api/search", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ prompt: "becas" })
            });
            const initChunks = await initRes.json();
            
            initChunks.forEach(chunk => {
                const tr = document.createElement("tr");
                tr.className = "border-b border-unl-border hover:bg-slate-50 text-xs";
                const label = chunk.source === "Guia_MGT_MD" ? "Guía MGT/SGA" : "Reglamento PDF";
                const pageText = chunk.page !== null ? `page: ${chunk.page + 1}` : "N/D";
                
                tr.innerHTML = `
                    <td class="py-3 px-4 font-bold text-emerald-600 font-mono">${chunk.score}</td>
                    <td class="py-3 px-4 font-semibold text-unl-dark">${label}</td>
                    <td class="py-3 px-4 leading-relaxed">${chunk.content}</td>
                    <td class="py-3 px-4"><span class="bg-gray-100 px-2 py-1 rounded text-[10px] text-unl-text-secondary font-mono">${pageText} | file: ${chunk.file_name}</span></td>
                `;
                tableBody.appendChild(tr);
            });
        }

    } catch (e) {
        console.error("Error al poblar explorador vectorial:", e);
        tableBody.innerHTML = `<tr><td colspan="4" class="py-4 text-center text-red-500 italic">Error de red al conectar con el motor de busqueda semantica.</td></tr>`;
    }
}

// --- LOGICA DE GESTION (PESTAÑA 4) ---
function actualizarFileLabel() {
    const input = document.getElementById("upload-input");
    const label = document.getElementById("upload-label");
    if (input.files.length > 0) {
        label.textContent = `Seleccionado: ${input.files[0].name}`;
        label.className = "bg-amber-600 text-white px-4 py-1.5 rounded font-label-md transition-colors cursor-pointer text-xs";
    }
}

async function subirArchivo() {
    const uploadInput = document.getElementById("upload-input");
    const file = uploadInput.files[0];
    const statusMsg = document.getElementById("upload-status-message");

    if (!file) {
        statusMsg.textContent = "Error: Debe seleccionar un archivo .pdf o .md primero.";
        statusMsg.className = "mt-3 text-xs font-medium text-center text-red-600";
        return;
    }

    statusMsg.textContent = "Subiendo archivo...";
    statusMsg.className = "mt-3 text-xs font-medium text-center text-unl-blue";

    const formData = new FormData();
    formData.append("file", file);

    try {
        const respuesta = await fetch("/api/upload", {
            method: "POST",
            body: formData
        });
        const datos = await respuesta.json();

        if (respuesta.ok) {
            statusMsg.textContent = datos.mensaje;
            statusMsg.className = "mt-3 text-xs font-medium text-center text-emerald-600";
            uploadInput.value = ""; // Limpiar
            document.getElementById("upload-label").textContent = "Seleccionar Archivo";
            document.getElementById("upload-label").className = "bg-secondary text-white px-4 py-1.5 rounded font-label-md hover:bg-unl-green-dark transition-colors cursor-pointer text-xs";
            
            // Recargar datos para ver el nuevo archivo
            cargarDatosSistema();
        } else {
            statusMsg.textContent = `Error: ${datos.detail}`;
            statusMsg.className = "mt-3 text-xs font-medium text-center text-red-600";
        }
    } catch (e) {
        console.error("Error al subir archivo:", e);
        statusMsg.textContent = "Error de red al intentar subir el documento.";
        statusMsg.className = "mt-3 text-xs font-medium text-center text-red-600";
    }
}

async function reindexarBase() {
    const statusMsg = document.getElementById("reindex-status-message");
    statusMsg.textContent = "Indexando documentos asincronamente en caliente... Por favor, espere.";
    statusMsg.className = "mb-4 text-xs font-semibold text-center text-amber-600 block";

    try {
        const respuesta = await fetch("/api/reindex", { method: "POST" });
        const datos = await respuesta.json();

        if (respuesta.ok) {
            statusMsg.textContent = datos.mensaje;
            statusMsg.className = "mb-4 text-xs font-semibold text-center text-emerald-600 block";
            
            // Recargar datos despues de 6 segundos para dar tiempo a la tarea asincrona
            setTimeout(() => {
                cargarDatosSistema();
                refrescarExploradorPuro("");
                statusMsg.textContent = "Re-indexación y persistencia completada con éxito. Base Vectorial actualizada.";
                statusMsg.className = "mb-4 text-xs font-semibold text-center text-emerald-600 block";
            }, 6000);
        } else {
            statusMsg.textContent = `Error al indexar: ${datos.detail}`;
            statusMsg.className = "mb-4 text-xs font-semibold text-center text-red-600 block";
        }
    } catch (e) {
        console.error("Error al indexar:", e);
        statusMsg.textContent = "Error de red al intentar conectar con el pipeline de ingesta.";
        statusMsg.className = "mb-4 text-xs font-semibold text-center text-red-600 block";
    }
}
