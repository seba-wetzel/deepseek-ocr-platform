# DeepSeek OCR Platform v2.0 🔮

Plataforma de OCR local de alto rendimiento diseñada para procesar archivos PDF grandes utilizando el modelo **DeepSeek-OCR-2 (3B)** con aceleración GPU.

## 🚀 Características v2.0

- **Motor Actualizado**: Integra el nuevo modelo **DeepSeek-OCR-2** con "Visual Causal Flow" para una comprensión superior de documentos.
- **Interfaz en Español**: UI totalmente localizada.
- **Privacidad Local**: Todo el procesamiento se realiza en tu máquina; nada sube a la nube.
- **Gestión Inteligente de Memoria**: Procesamiento en streaming página por página.
- **Gestión de Trabajos**: Cola de procesos, cancelación en tiempo real, historial persistente (SQLite) y borrado de trabajos.
- **Resultados en Vivo**: Actualizaciones de progreso en tiempo real mediante Server-Sent Events (SSE).
- **Exportación**: Descarga de resultados en formatos Excel (.xlsx) y CSV.

## 🛠️ Requisitos Previos

- **OS**: Linux (recomendado) o Windows con WSL2.
- **GPU**: NVIDIA con soporte CUDA (mínimo 6GB VRAM, recomendado 12GB para modelo completo en bfloat16).
- **Software**:
  - Python 3.10+
  - Node.js 16+ & npm
  - `poppler-utils` (para procesar PDFs)

## 📦 Instalación

### 1. Clonar el repositorio
```bash
git clone <url-del-repo>
cd ocr
```

### 2. Configurar Backend (Python)
```bash
# Instalar utilidades de sistema
sudo apt-get install poppler-utils

# Crear entorno virtual
python3 -m venv venv
source venv/bin/activate

# Instalar dependencias
pip install -r requirements.txt
```

### 3. Configurar Frontend (Vue 3)
```bash
cd frontend
npm install
cd ..
```

### 4. Configurar Modelos
El sistema intentará descargar automáticamente `deepseek-ai/DeepSeek-OCR` (o el modelo configurado) desde HuggingFace en la primera ejecución.
Si deseas usar una ruta local, configura la variable de entorno:
```bash
export OCR_MODEL_PATH="/ruta/a/tu/modelo"
```

## ▶️ Ejecución

Hemos incluido un script de inicio rápido:

```bash
# Dar permisos de ejecución
chmod +x start.sh

# Iniciar (Backend + Frontend)
./start.sh
```

El sistema estará disponible en:
- **Frontend (UI)**: `http://localhost:5173`
- **Backend (API)**: `http://localhost:8000`

### Ejecución Manual
**Terminal 1 (Backend):**
```bash
source venv/bin/activate
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
```

**Terminal 2 (Frontend):**
```bash
cd frontend
npm run dev
```

## 🖥️ Uso

1. **Subir PDF**: Arrastra tu archivo a la zona de carga.
2. **Monitorear**: Verás una tarjeta con el progreso página por página.
3. **Cancelar**: Si te equivocaste, pulsa la "X" para detener el proceso inmediatamente.
4. **Ver Resultados**: Al finalizar, la tarjeta se expandirá. Puedes previsualizar el texto y descargar el reporte.
5. **Limpieza**: Usa el icono de papelera para borrar trabajos antiguos del historial.

## 🔧 Solución de Problemas Comunes

- **Error de Memoria (CUDA OOM)**:
  - Intenta reducir el tamaño de imagen en `ocr_service.py` (`dpi=150`).
  - Asegúrate de no tener otros procesos usando la GPU.
- **Estado "Unknown"**:
  - Reinicia el servidor para asegurar que la base de datos se inicializó correctamente.
- **No procesa PDFs**:
  - Verifica que `poppler-utils` esté instalado (`pdfinfo -v`).

---
Desarrollado con ❤️ y DeepSeek.
