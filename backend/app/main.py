import tempfile
import sys
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from Prueba_1 import analizar_archivo

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/analizar")
async def analizar_endpoint(file: UploadFile = File(...)):
    filename = file.filename or "archivo"
    suffix = Path(filename).suffix.lower()
    allowed_suffixes = {".krn", ".xml", ".musicxml", ".mxl"}

    if suffix not in allowed_suffixes:
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Usa un archivo .krn, .xml, .musicxml o .mxl.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as temp_file:
        temp_file.write(await file.read())
        temp_path = Path(temp_file.name)

    try:
        resultados = analizar_archivo(str(temp_path))
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"No se pudo analizar el archivo: {exc}"
        ) from exc
    finally:
        temp_path.unlink(missing_ok=True)

    if "error" in resultados:
        raise HTTPException(status_code=400, detail=resultados["error"])

    return {"filename": filename, **resultados}
