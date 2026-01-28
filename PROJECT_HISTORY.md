# Historia del Proyecto: DeepSeek OCR Platform

Este documento narra la evolución del desarrollo de la plataforma de OCR local, detallando los requerimientos, desafíos técnicos y soluciones implementadas en orden cronológico.

## 1. Fase Inicial: Concepción y Estructura Base
**Objetivo:** Crear una plataforma web local para realizar OCR en archivos PDF grandes utilizando el modelo `DeepSeek-OCR` (1.3b), optimizado para una GPU NVIDIA RTX 3060 (12GB).

### Requerimientos
- Frontend en **Vue 3**.
- Backend en **Python (FastAPI)**.
- Inferencia local (sin APIs externas).
- Soporte para exportación a Excel/CSV.

### Desafío Técnico
- Integrar un modelo de lenguaje multimodal (DeepSeek-VL) en un flujo de trabajo de OCR estructurado.

---

## 2. El Problema de la Memoria (OOM)
**Problema:** Al intentar procesar PDFs grandes (incluso de pocos MBs pero muchas páginas), el servidor colapsaba por falta de memoria RAM (>28GB consumidos).
- **Causa Raíz:** La librería `pdf2image` cargaba *todas* las imágenes del PDF en memoria RAM antes de empezar a procesar la primera.

### Solución: Procesamiento en Streaming
Se reescribió el bucle de procesamiento en `ocr_service.py` para ser iterativo y perezoso:
1. Leer metadatos del PDF para obtener el número total de páginas.
2. Convertir **solo una página** a imagen (`first_page=i, last_page=i`).
3. Procesar esa imagen con el modelo.
4. Guardar resultado en DB y liberar memoria de la imagen.
5. Repetir.
**Resultado:** Uso de RAM estable (<2GB) sin importar el tamaño del PDF.

---

## 3. Integración Real de DeepSeek-VL
**Requerimiento:** Asegurar que se usara el modelo real y no un placeholder, respetando el formato de prompt oficial.

### Cambios Realizados
- **Carga del Modelo:** Se configuró `AutoModel` con `trust_remote_code=True` y `torch_dtype=torch.bfloat16`.
- **Prompt Engineering:** Se implementó el prompt específico de DeepSeek-OCR para "grounding":
  ```python
  prompt = "<image>\n<|grounding|>Convert the document to markdown."
  ```
  Esto instruye al modelo a transcribir el texto respetando la estructura visual, en lugar de describir la imagen.

---

## 4. Persistencia y Actualizaciones en Tiempo Real
**Problema:** El frontend mostraba estados "Unknown" y perdía el progreso si se recargaba la página.
**Causa:** El estado se guardaba en variables volátiles en memoria del servidor.

### Solución: SQLite + SSE (Server-Sent Events)
1. **Base de Datos:** Se implementó `sqlite3` para persistir trabajos (`jobs`) y páginas (`job_pages`).
2. **Endpoints:** Se creó `/api/status/{id}/stream` para enviar actualizaciones push al frontend.
3. **Flujo Atómico:** El backend actualiza la DB paso a paso; el frontend escucha y refleja el estado exacto (progreso, página actual).

---

## 5. Gestión del Trabajo: Cancelación y Borrado
**Requerimiento:** El usuario debe poder detener un proceso largo y borrar trabajos del historial.

### Desafíos Técnicos
- **Detener un Thread:** Los procesos de OCR corren en threads de fondo (`BackgroundTasks`). No se pueden "matar" desde fuera fácilmente.
- **Race Conditions:** ¿Qué pasa si borras un trabajo mientras se está procesando?

### Solución Implementada
1. **Flag en DB:** Se añadió la columna `cancelled` a la tabla `jobs`.
2. **Checkpoints en el Bucle:**
   En `ocr_service.py`, antes de procesar cada página, se consulta la DB:
   ```python
   job_info = get_job(job_id)
   if not job_info or job_info['cancelled']:
       return # Abortar inmediatamente
   ```
3. **Validación Robusta:** Se añadió lógica para detectar si el trabajo fue *borrado* (`job_info is None`) para evitar errores de referencia nula y detener procesos "zombies".

---

## 6. Refactorización: Arquitectura Centralizada
**Requerimiento:** Optimizar las conexiones de red. Se detectó que se abrían múltiples conexiones SSE por trabajo.
**Instrucción:** Mover la lógica de "fetching" al componente padre (`App.vue`) y dejar a los hijos (`JobResult.vue`) solo como vista.

### Cambios (Patrón "Smart Parent / Dumb Child")
1. **App.vue (Cerebro):**
   - Mantiene un Mapa `activeConnections` para asegurar **una única** conexión SSE por trabajo activo.
   - Centraliza las llamadas a API (`fetchJobs`, `cancelJob`, `deleteJob`).
   - Pasa los datos (`results`, `status`) hacia abajo.
2. **JobResult.vue (Vista):**
   - Se eliminó toda lógica de `fetch` y `EventSource`.
   - Ahora recibe datos vía `props` y comunica intenciones (`@cancel`, `@delete`) vía eventos.

### 
---

## 7. Métricas y Retrospectiva

### Datos del Desarrollo
- **Tiempo Total Transcurrido:** ~22 horas (Desde el inicio del setup hasta el refactor final).
- **Iteraciones Mayores:** ~15 (Ciclos de implementación/feedback).
- **Prompts de Usuario:** ~50 interacciones clave.
- **Complejidad:** Alta (Integración de ML, Backend Asíncrono, Frontend Reactivo, Base de Datos, Streams).

### Registro de Errores y Soluciones
A continuación, una lista de los errores críticos encontrados durante el desarrollo y su diagnóstico:

| Error / Problema | Detalle Técnico | Solución |
| :--- | :--- | :--- |
| **OOM (Out Of Memory)** | El servidor crasheaba con PDFs grandes (>28GB RAM). `pdf2image` cargaba todo el PDF en memoria. | Implementación de **Lazy Streaming**: convertir y liberar página por página. |
| **Modelo Incorrecto** | El modelo "describía" la imagen (ej: "Es una factura...") en lugar de leer el texto. Se estaba cargando el modelo Chat genérico. | Cambio a **DeepSeek-OCR** específico e implementación del prompt oficial `<image>\n<|grounding|>`. |
| **Error de Configuración (HF)** | `ValueError: loading ... requires trust_remote_code=True`. | Activación de flags `trust_remote_code=True` y `use_safetensors=True` en `AutoModel`. |
| **Inferencia Vacía/Alucinaciones** | El modelo devolvía texto sin sentido o vacío. | Ajuste de parámetros de generación (`do_sample=True`, `temperature=0.1`) y corrección de `torch_dtype=bfloat16`. |
| **Bloqueo del Server** | El endpoint de status no respondía durante el OCR. `async def process_pdf` bloqueaba el Event Loop de Python. | Cambio a `def process_pdf` (síncrono) para que FastAPI lo ejecute en un Thread Pool separado. |
| **Estado "Unknown"** | Al recargar la página, se perdía el progreso. El estado residía en variables de memoria volátil. | Migración a **SQLite**. Persistencia total de trabajos y resultados. |
| **Jobs "Zombies"** | Al borrar un trabajo desde el UI, el backend seguía procesándolo e imprimiendo logs. | Inyección de verificaciones de existencia (`if not job_info`) en el bucle de OCR. |
| **Vue Warnings** | `Extraneous non-emits event listeners`. | Declaración explícita de `defineEmits(['delete-job', ...])` en los componentes. |
| **Conexiones SSE Múltiples** | Cada componente `JobResult` abría su propia conexión, saturando el navegador y el server. | **Refactor Arquitectónico**: Centralización de conexiones en `App.vue` (Singleton por JobID). |
| **NameError en Router** | `global name 'ocr_service' is not defined` tras mover funciones. | Corrección de imports y referencias directas en `router.py`. |

