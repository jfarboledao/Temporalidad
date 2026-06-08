import asyncio
import tempfile
import sys
from concurrent.futures import ThreadPoolExecutor
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

# Thread pool for CPU-bound music21 analysis.
# Each file is handled by a separate thread so multiple files run concurrently.
_pool = ThreadPoolExecutor(max_workers=8)


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


async def _analyze_one(filename: str, content: bytes, suffix: str) -> dict:
    """Write a temp file and run the vessel analysis in the thread pool."""
    with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
        tmp.write(content)
        tmp_path = Path(tmp.name)

    loop = asyncio.get_event_loop()
    try:
        result = await loop.run_in_executor(
            _pool, analyze_file_for_api, str(tmp_path), filename
        )
        return {"filename": filename, "ok": True, "result": result}
    except Exception as exc:
        return {"filename": filename, "ok": False, "reason": str(exc)}
    finally:
        tmp_path.unlink(missing_ok=True)


@app.post("/api/vessels")
async def vessels_endpoint(files: List[UploadFile] = File(...)):
    """
    Analyze one or more score files with the MailmansVessels temporal analysis pipeline.
    All valid files are processed concurrently in a thread pool.
    """
    if not files:
        raise HTTPException(status_code=400, detail="No se enviaron archivos.")

    # 1. Read all file contents first (async I/O, fast)
    tasks = []
    skipped: list[dict] = []

    for upload in files:
        filename = upload.filename or "archivo"
        suffix = Path(filename).suffix.lower()

        if suffix not in _ALLOWED_SUFFIXES:
            skipped.append({"filename": filename, "reason": "Formato no soportado"})
            continue

        content = await upload.read()
        tasks.append(_analyze_one(filename, content, suffix))

    # 2. Run all analyses concurrently
    outcomes = await asyncio.gather(*tasks)

    # 3. Collect results
    processed: list[dict] = []
    for outcome in outcomes:
        if not outcome["ok"]:
            skipped.append({"filename": outcome["filename"], "reason": outcome["reason"]})
            continue
        result = outcome["result"]
        if "error" in result:
            skipped.append({"filename": outcome["filename"], "reason": result["error"]})
        else:
            processed.append({"filename": outcome["filename"], **result})

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
