import traceback
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Request, UploadFile, File
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from projects.modulo1.Modulo1 import process_modulo1


# ============================================================
# CONFIG DE PASTAS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
UPLOAD_DIR = BASE_DIR / "uploads"
OUTPUT_DIR = BASE_DIR / "output"
LOG_DIR = BASE_DIR / "logs"

for d in [UPLOAD_DIR, OUTPUT_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)


# ============================================================
# APP FASTAPI
# ============================================================

app = FastAPI(title="Rentus Analyzer", version="1.0")

app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


# ============================================================
# LOGGER
# ============================================================

def create_logger(prefix: str, run_id: str):
    """
    Cria funções logger() e warn_logger() que:
    - imprimem no console
    - salvam no arquivo /logs
    """
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_path = LOG_DIR / f"log-{date_str}-{prefix}-{run_id}.txt"

    def write(msg: str):
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(msg + "\n")

    def logger(msg: str):
        print(msg)
        write(msg)

    def warn(msg: str):
        text = "[WARN] " + msg
        print(text)
        write(text)

    return logger, warn


# ============================================================
# ROTAS HTML
# ============================================================

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/modulo1", response_class=HTMLResponse)
async def modulo1_page(request: Request):
    return templates.TemplateResponse("modulo1.html", {"request": request})

@app.get("/modulo2", response_class=HTMLResponse)
async def modulo2_page(request: Request):
    return templates.TemplateResponse("modulo2.html", {"request": request})


# ============================================================
# ROTA DE PROCESSAMENTO MODULO 1
# ============================================================

@app.post("/modulo1/process")
async def modulo1_process(
    request: Request,
    OPS: UploadFile = File(...),
    demitidos: UploadFile = File(...),
    AVISO_PREVIO: UploadFile = File(...),
    hk_avulso: UploadFile = File(...),
    fp: UploadFile = File(...),
    situacao: UploadFile = File(...)
):
    run_id = datetime.now().strftime("%H%M%S")
    logger, warn_logger = create_logger("modulo1", run_id)

    try:
        logger("[INFO] ======================================")
        logger("[INFO] Iniciando processamento MÓDULO 1")
        logger("[INFO] ======================================")

        def save_file(upload: UploadFile, name: str) -> Path:
            dest = UPLOAD_DIR / name
            logger(f"[INFO] Salvando {name} em {dest}...")
            with open(dest, "wb") as f:
                f.write(upload.file.read())
            return dest

        ops_path = save_file(OPS, "OPS.xlsx")
        dem_path = save_file(demitidos, "demitidos.xls")
        aviso_path = save_file(AVISO_PREVIO, "AVISO_PREVIO.xls")
        hk_path = save_file(hk_avulso, "hk_avulso.xls")
        fp_path = save_file(fp, "fp.xlsx")
        sit_path = save_file(situacao, "situacao.xlsx")

        output_file, process_logs = process_modulo1(
    ops_path=ops_path,
    hk_avulso_path=hk_path,
    demitidos_path=dem_path,
    aviso_previo_path=aviso_path,
    situacao_path=sit_path,
    fp_path=fp_path,
    output_dir=OUTPUT_DIR
)


        logger("[INFO] PROCESSO FINALIZADO COM SUCESSO.")

        download_url = f"/download/{output_file.name}"

        return JSONResponse({
    "success": True,
    "download_url": download_url,
    "logs": process_logs
})

    except Exception as e:
        tb = traceback.format_exc()
        logger("[ERROR] Erro inesperado no módulo 1:")
        logger(tb)

        return JSONResponse({
            "success": False,
            "error": str(e),
            "logs": [str(e)],
        })


# ============================================================
# ROTA DE DOWNLOAD
# ============================================================

@app.get("/download/{filename}")
async def download_result(filename: str):
    file_path = OUTPUT_DIR / filename
    if not file_path.exists():
        return JSONResponse({"error": "Arquivo não encontrado."}, status_code=404)

    return FileResponse(
        path=file_path,
        media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        filename=filename
    )
