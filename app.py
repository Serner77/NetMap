#!/usr/bin/env python3
"""
app.py
FastAPI backend para NetMap con dashboard.
"""

import os
import json
import uuid
import subprocess
import time
from fastapi import FastAPI, BackgroundTasks, Request
from fastapi.responses import JSONResponse, HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from make_graph import build_graph, load_results

app = FastAPI(title="NetMap API", version="0.4")

# Configuración de plantillas y estáticos
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Permitir CORS (útil para pruebas locales con dashboard en otro puerto)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Memoria temporal para jobs
# Cada job = {"state":..., "process":..., "started_at":..., "finished_at":..., "message":...}
jobs = {}


def run_scan(job_id: str, deep: bool = False, workers: int = 12):
    """Ejecuta netmap.py como subproceso y actualiza estado en jobs dict."""
    jobs[job_id]["state"] = "running"
    jobs[job_id]["started_at"] = time.time()

    try:
        cmd = ["sudo", "venv/bin/python3", "netmap.py"]
        if deep:
            cmd.append("--deep")
            cmd.extend(["--workers", str(workers)])

        # Lanzamos el proceso en background (NO bloqueante)
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        jobs[job_id]["process"] = proc

        # Esperamos a que termine
        stdout, stderr = proc.communicate()
        jobs[job_id]["finished_at"] = time.time()

        if jobs[job_id]["state"] == "cancelled":
            jobs[job_id]["message"] = "Escaneo cancelado por el usuario"
            return

        if proc.returncode == 0:
            jobs[job_id]["state"] = "done"
            jobs[job_id]["message"] = stdout.strip()
        else:
            jobs[job_id]["state"] = "error"
            jobs[job_id]["message"] = stderr.strip()

    except Exception as e:
        jobs[job_id]["state"] = "error"
        jobs[job_id]["message"] = str(e)

@app.get("/")
async def root():
    return RedirectResponse(url="/dashboard")

@app.post("/api/scan")
async def api_scan(background_tasks: BackgroundTasks, deep: bool = False, workers: int = 12):
    """Lanza un escaneo en background."""
    job_id = str(uuid.uuid4())
    jobs[job_id] = {
        "state": "pending",
        "started_at": None,
        "finished_at": None,
        "message": None,
        "process": None,
    }
    background_tasks.add_task(run_scan, job_id, deep, workers)
    return {"status": "started", "job_id": job_id}


@app.post("/api/scan/cancel/{job_id}")
async def api_scan_cancel(job_id: str):
    """Cancela un escaneo en ejecución."""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "job not found"})

    proc = job.get("process")
    if proc and proc.poll() is None:  # proceso sigue vivo
        try:
            proc.terminate()
            time.sleep(0.5)
            if proc.poll() is None:
                proc.kill()
            job["state"] = "cancelled"
            job["finished_at"] = time.time()
            return {"status": "cancelled", "job_id": job_id}
        except Exception as e:
            return JSONResponse(status_code=500, content={"error": str(e)})
    elif job["state"] in ["done", "error", "cancelled"]:
        return {"status": "already_finished", "job_id": job_id}
    else:
        return {"status": "not_running", "job_id": job_id}


@app.get("/api/scan/status/{job_id}")
async def api_scan_status(job_id: str):
    """Consulta el estado de un escaneo."""
    job = jobs.get(job_id)
    if not job:
        return JSONResponse(status_code=404, content={"error": "job not found"})
    # no devolvemos el objeto process por seguridad
    safe_job = {k: v for k, v in job.items() if k != "process"}
    return safe_job


@app.get("/api/devices")
async def api_devices():
    """Devuelve el contenido de netmap_results.json (último escaneo)."""
    if not os.path.exists("netmap_results.json"):
        return {"devices": [], "deep": False}

    with open("netmap_results.json", "r") as f:
        data = json.load(f)

    devices = data.get("devices", [])
    deep = data.get("_meta", {}).get("deep", False)

    if not deep:
        # Solo devolver IP, MAC y Vendor
        devices = [
            {"ip": d.get("ip"), "mac": d.get("mac"), "vendor": d.get("vendor")}
            for d in devices
        ]

    return {"devices": devices, "deep": deep}


@app.get("/api/graph")
async def api_graph():
    """Genera y devuelve el grafo como HTMLResponse."""
    if not os.path.exists("netmap_results.json"):
        return HTMLResponse("<h3>No hay resultados, ejecuta un escaneo primero.</h3>", status_code=404)

    devices = load_results("netmap_results.json")
    output_html = "netmap_graph.html"
    build_graph(devices, output_html=output_html, height="800px")

    with open(output_html, "r", encoding="utf-8") as f:
        html = f.read()
    return HTMLResponse(content=html, status_code=200)


@app.get("/dashboard")
async def dashboard(request: Request):
    """Renderiza el dashboard web con tabla y grafo."""
    devices = []
    if os.path.exists("netmap_results.json"):
        with open("netmap_results.json", "r") as f:
            devices = json.load(f)
    return templates.TemplateResponse("dashboard.html", {"request": request, "devices": devices})
