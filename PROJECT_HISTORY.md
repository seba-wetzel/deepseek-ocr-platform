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

---

# V2: Migración a DeepSeek-OCR-2 y Sistema de Prompts Personalizados

**Fecha de Desarrollo:** 27-28 de Enero 2026  
**Rama Git:** `v2`

## 1. Requerimientos de la V2

### Objetivos Principales
1. **Migrar a DeepSeek-OCR-2** - El nuevo modelo especializado en OCR con arquitectura "Visual Causal Flow".
2. **Sistema de Prompts Personalizables** - Permitir que el usuario cree, edite y seleccione prompts personalizados desde la UI.
3. **Refactorizar UI/UX** - Crear componentes dedicados para selección de archivos (`FileSelector`) y gestión de prompts (`PromptManager`).
4. **Exportación de Resultados** - Agregar botones para descargar resultados como Excel o CSV.

### Funcionalidad Añadida
- **CRUD de Prompts**: API endpoints para crear, leer, actualizar y eliminar prompts persistentes en SQLite.
- **UI de Gestión de Prompts**: Panel lateral con selector, formulario de edición, y marcación de prompt por defecto.
- **Botones de Exportación**: Descarga directa a `.xlsx` y `.csv`.
- **Subida de Archivos Mejorada**: Indicador de progreso visual durante el upload.

---

## 2. Desafíos Técnicos y Soluciones

### 2.1 Cambio de Modelo: DeepSeek-VL → DeepSeek-OCR-2

**Problema:** El modelo anterior (DeepSeek-VL 1.3B Chat) no era el modelo OCR especializado. Los resultados eran descripciones genéricas de las imágenes.

**Descubrimiento:** Al investigar el repositorio oficial de DeepSeek, se encontró que existe un modelo dedicado `deepseek-ai/DeepSeek-OCR-2` con método `.infer()` nativo.

**Solución:**
```python
# Antes (incorrecto):
from deepseek_vl.models import VLChatProcessor
# Ahora (correcto):
model = AutoModel.from_pretrained("deepseek-ai/DeepSeek-OCR-2", trust_remote_code=True)
result = model.infer(tokenizer, prompt=prompt, image_file=path, ...)
```

### 2.2 El Misterio del Prompt: `<|grounding|>` vs HTML Output

**Problema:** El usuario quería obtener datos en formato CSV, pero el modelo siempre devolvía tablas HTML complejas sin importar las instrucciones del prompt.

**Investigación:**
1. Se revisó el repositorio oficial de DeepSeek-OCR.
2. Se consultó la documentación de vLLM para DeepSeek-OCR.
3. Se encontró el archivo `config.py` con los prompts oficiales.

**Hallazgos Críticos:**
- El token `<|grounding|>` activa el modo de **reconstrucción de layout visual** → siempre genera HTML/Markdown.
- El modelo está **entrenado para HTML/Markdown**, no puede generar CSV directamente.
- En vLLM, los tokens `<td>` y `</td>` están explícitamente en whitelist.

**Prompts Oficiales Soportados:**

| Prompt | Resultado |
|--------|-----------|
| `<image>\n<|grounding|>Convert the document to markdown.` | Tablas en Markdown ✅ |
| `<image>\nFree OCR.` | Texto plano (sin tablas) |
| `<image>\nParse the figure.` | Para gráficos |

**Resolución Final:** Se recomendó usar el prompt de Markdown (mejor resultado) y confiar en los botones de exportación para conversión a CSV/Excel.

### 2.3 Parámetros de Inferencia Incorrectos

**Problema:** Con ciertos prompts, el modelo devolvía salida completamente vacía.

**Causa:** El parámetro `image_size=640` no coincidía con la documentación oficial que usa `image_size=768`.

**Solución:**
```python
text_result = model.infer(
    tokenizer,
    prompt=prompt,
    image_file=temp_image_path,
    base_size=1024,
    image_size=768,  # Corregido de 640 a 768
    crop_mode=True,
    save_results=True
)
```

### 2.4 Arquitectura de Componentes: Props vs API Calls

**Problema:** El componente `PromptManager` hacía sus propias llamadas API, creando duplicación de lógica y problemas de sincronización con `App.vue`.

**Solución:** Refactorización al patrón "Smart Parent / Dumb Child":
- `App.vue`: Centraliza todas las llamadas API (`fetchPrompts`, `handleSavePrompt`).
- `PromptManager`: Recibe `prompts` como prop, emite eventos (`@save-prompt`).

---

## 3. Registro de Errores V2

| Error / Problema | Detalle Técnico | Solución |
| :--- | :--- | :--- |
| **Modelo Describía en vez de OCR** | Se cargaba DeepSeek-VL Chat en lugar del modelo OCR especializado. | Migración a `deepseek-ai/DeepSeek-OCR-2` con método `.infer()`. |
| **HTML en lugar de CSV** | El usuario quería CSV pero obtenía `<table>` HTML. | Explicación: El modelo está entrenado para HTML/Markdown. Usar exportación para conversión. |
| **Salida Vacía** | Con `image_size=640`, ciertos prompts no devolvían nada. | Corrección a `image_size=768` según documentación oficial. |
| **Prompt sin `<image>`** | El prompt del usuario no incluía el token de imagen requerido. | Educación sobre formato obligatorio: `<image>\n<|grounding|>...` |
| **result.mmd no encontrado** | `model.infer()` devolvía `None` y el archivo no se creaba. | Depuración intensiva; el problema era el formato de prompt. |
| **PromptManager duplicaba lógica** | Componente hacía API calls propias, desincronizando estado. | Refactor a patrón props/events con estado centralizado en `App.vue`. |

---

## 4. Fuentes de Investigación

1. **GitHub DeepSeek-OCR-2**: [https://github.com/deepseek-ai/DeepSeek-OCR-2](https://github.com/deepseek-ai/DeepSeek-OCR-2)
2. **HuggingFace Model Card**: [https://huggingface.co/deepseek-ai/DeepSeek-OCR-2](https://huggingface.co/deepseek-ai/DeepSeek-OCR-2)
3. **vLLM Recipes - DeepSeek-OCR**: [https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-OCR.html](https://docs.vllm.ai/projects/recipes/en/latest/DeepSeek/DeepSeek-OCR.html)
4. **Config.py Oficial (Prompts)**: [config.py en GitHub](https://github.com/deepseek-ai/DeepSeek-OCR/blob/main/DeepSeek-OCR-master/DeepSeek-OCR-vllm/config.py)

---

## 5. Métricas del Desarrollo V2

| Métrica | Valor |
|---------|-------|
| **Tiempo de Desarrollo** | ~6 horas |
| **Iteraciones Mayores** | ~20 |
| **Prompts de Usuario** | ~35 interacciones |
| **Complejidad** | Media-Alta (Nuevo modelo, debugging de prompts, refactor UI) |

---

## 6. Opiniones y Sugerencias para V3

> **Nota del Desarrollador (AI):** Las siguientes son observaciones personales basadas en el desarrollo de esta versión.

### Mejoras Sugeridas

1. **Migración a vLLM**: El uso de vLLM en lugar de Transformers directos podría mejorar significativamente el rendimiento (batching, KV cache, etc.). Esto requeriría refactorizar `ocr_service.py` para usar el cliente vLLM.

2. **Post-Procesamiento Inteligente**: Si el usuario necesita CSV, implementar una capa de parsing que detecte tablas HTML/Markdown y las convierta automáticamente al formato deseado (deshabilitado en V2 por preferencia del usuario, pero útil como opción).

3. **Preview de Imagen**: Mostrar una miniatura de cada página del PDF junto al resultado OCR para verificación visual.

4. **Sistema de Templates de Prompt**: En lugar de prompts libres, ofrecer templates predefinidos con variables (ej: "Extraer tablas de {tipo_documento}").

5. **Pruebas Automatizadas**: Implementar tests unitarios para la API y tests E2E para el flujo completo de OCR.

6. **Manejo de Errores de GPU**: Actualmente si la GPU se queda sin memoria, el proceso falla silenciosamente. Sería útil tener recovery automático o mensajes más claros.

### Correcciones Pendientes

- **Warnings de Transformers**: El modelo genera warnings sobre `attention_mask` y `pad_token_id`. Estos son inofensivos pero podrían silenciarse explícitamente.
- **Logs de Debug**: Algunos logs de debug (`--- Raw Model Output ---`) quedaron activos; considerar hacerlos configurables.

---

*Última actualización: 28 de Enero 2026*
