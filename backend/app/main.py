import tempfile
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.append(str(ROOT_DIR))

from Prueba_1 import analizar_archivo
from vessels import analyze_file_for_api, compute_century_summary

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

_ALLOWED_SUFFIXES = {".krn", ".xml", ".musicxml", ".mxl"}


@app.get("/health")
def health_check():
    return {"status": "ok"}


@app.post("/api/analizar")
async def analizar_endpoint(file: UploadFile = File(...)):
    filename = file.filename or "archivo"
    suffix = Path(filename).suffix.lower()

    if suffix not in _ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400,
            detail="Formato no soportado. Usa un archivo .krn, .xml, .musicxml o .mxl.",
        )

    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(await file.read())
        tmp_path = Path(tmp.name)

    try:
        resultados = analizar_archivo(str(tmp_path))
    except Exception as exc:
        raise HTTPException(
            status_code=400, detail=f"No se pudo analizar el archivo: {exc}"
        ) from exc
    finally:
        tmp_path.unlink(missing_ok=True)

    if "error" in resultados:
        raise HTTPException(status_code=400, detail=resultados["error"])

    return {"filename": filename, **resultados}


@app.post("/api/vessels")
async def vessels_endpoint(files: List[UploadFile] = File(...)):
    """
    Analyze one or more score files with the MailmansVessels temporal analysis pipeline.
    Accepts .krn, .xml, .musicxml, and .mxl files.
    Unsupported files are skipped and reported in the 'skipped' list.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No se enviaron archivos.")

    processed: list[dict] = []
    skipped: list[dict] = []

    for upload in files:
        filename = upload.filename or "archivo"
        suffix = Path(filename).suffix.lower()

        if suffix not in _ALLOWED_SUFFIXES:
            skipped.append({"filename": filename, "reason": "Formato no soportado"})
            continue

        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await upload.read())
            tmp_path = Path(tmp.name)

        try:
            result = analyze_file_for_api(str(tmp_path), filename)
            if "error" in result:
                skipped.append({"filename": filename, "reason": result["error"]})
            else:
                processed.append({"filename": filename, **result})
        except Exception as exc:
            skipped.append({"filename": filename, "reason": str(exc)})
        finally:
            tmp_path.unlink(missing_ok=True)

    if not processed and skipped:
        first_reason = skipped[0]["reason"]
        detail = (
            first_reason
            if len(skipped) == 1
            else f"No se pudo analizar ningún archivo. Primer error: {first_reason}"
        )
        raise HTTPException(status_code=400, detail=detail)

    century_summary = (
        compute_century_summary(processed) if len(processed) >= 2 else None
    )

    return {
        "files": processed,
        "total_files_processed": len(processed),
        "total_files_skipped": len(skipped),
        "skipped": skipped,
        "century_summary": century_summary,
    }
