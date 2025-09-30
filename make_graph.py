#!/usr/bin/env python3
"""
make_graph.py
Generador de grafo de red a partir de resultados de netmap.py (netmap_results.json).
Produce un archivo HTML interactivo con pyvis utilizando iconos personalizados (SVG).

Opciones CLI:
  --input FILE   Ruta al JSON de entrada (por defecto netmap_results.json)
  --output FILE  Ruta al HTML de salida (por defecto netmap_graph.html)
  --height PX    Altura del canvas (por defecto 900px)
"""

import json
import argparse
import os
import networkx as nx
import logging
from pyvis.network import Network

# ==========================
#  Logging con colores
# ==========================

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.INFO: "\033[36m",    # cian 
        logging.WARNING: "\033[33m", # naranja
        logging.ERROR: "\033[31m",   # rojo
        logging.CRITICAL: "\033[41m" # fondo rojo
    }
    RESET = "\033[0m"

    def format(self, record):
        base = super().format(record)
        if ": " in base:
            level, msg = base.split(": ", 1)
            color = self.COLORS.get(record.levelno, "")
            return f"{color}{level}{self.RESET}: {msg}"
        return base

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s"
)
for handler in logging.getLogger().handlers:
    handler.setFormatter(ColorFormatter("%(levelname)s: %(message)s"))

logger = logging.getLogger("make_graph")

# ==========================
#  Configuración de iconos
# ==========================
ICON_MAP = {
    "Router (gateway)": "/static/icons/router.svg",
    "Switch/AP":        "/static/icons/switch.svg",
    "Ordenador":        "/static/icons/pc.svg",
    "Móvil":            "/static/icons/mobile.svg",
    "TV / Consola":     "/static/icons/tv.svg",
    "Impresora":        "/static/icons/printer.svg",
    "IoT Device":       "/static/icons/iot.svg",
    "Desconocido":      "/static/icons/unknown.svg",
}

BROKEN_IMAGE = "/static/icons/unknown.svg"

# ==========================
#  Funciones auxiliares
# ==========================

def load_results(filename: str):
    """
    Carga el archivo JSON con los resultados de netmap.py.
    Si contiene metadatos, devuelve solo la lista de dispositivos.
    """
    with open(filename, "r", encoding="utf-8") as f:
        data = json.load(f)
    if isinstance(data, dict) and "devices" in data:
        return data["devices"]
    return data


def icon_for(node_class: str) -> str:
    """
    Devuelve la ruta del icono asociado a la clase de dispositivo.
    """
    return ICON_MAP.get(node_class or "Desconocido", ICON_MAP["Desconocido"])


# ==========================
#  Construcción del grafo
# ==========================

def build_graph(devices, output_html="netmap_graph.html", height="900px"):
    """
    Construye el grafo de la red utilizando NetworkX + PyVis.
    """
    if not devices:
        logger.error("No hay dispositivos para graficar.")
        return

    G = nx.Graph()

    # Detectar gateway (primer dispositivo clasificado como router)
    gateway_ip = None
    for d in devices:
        if "router" in (d.get("class") or "").lower():
            gateway_ip = d["ip"]
            break
    if not gateway_ip and devices:
        gateway_ip = devices[0]["ip"]

    # Añadir nodos
    for d in devices:
        ip = d["ip"]
        mac = d.get("mac", "")
        vendor = d.get("vendor", "Unknown")
        node_class = d.get("class") or "Desconocido"

        image_url = icon_for(node_class)

        title = (
            f"IP: {ip}\n"
            f"Clase: {node_class}\n"
            f"MAC: {mac}\n"
            f"Vendor: {vendor}"
        )

        G.add_node(
            ip,
            label="",
            title=title,
            shape="image",
            image=image_url,
            size=40,
            brokenImage=BROKEN_IMAGE,
            borderWidth=0
        )

    # Conectar con gateway
    for d in devices:
        ip = d["ip"]
        if gateway_ip and ip != gateway_ip:
            G.add_edge(gateway_ip, ip)

    # PyVis
    net = Network(height=height, width="100%", bgcolor="#111111", font_color="white", cdn_resources="remote")
    net.from_nx(G)

    net.repulsion(
        node_distance=320,
        central_gravity=0.18,
        spring_length=210,
        spring_strength=0.02
    )

    net.write_html(output_html, open_browser=False)
    logger.info(f"Grafo generado en {output_html}")


# ==========================
#  Main (CLI)
# ==========================

def main():
    p = argparse.ArgumentParser(description="Generador de grafo desde netmap_results.json")
    p.add_argument("--input", "-i", default="netmap_results.json", help="Archivo JSON con resultados de netmap")
    p.add_argument("--output", "-o", default="netmap_graph.html", help="Archivo HTML de salida")
    p.add_argument("--height", default="900px", help="Alto del canvas HTML (ej: 600px, 100%)")
    args = p.parse_args()

    if not os.path.exists(args.input):
        logger.error(f"Archivo {args.input} no encontrado. Ejecuta netmap.py primero.")
        return

    devices = load_results(args.input)
    build_graph(devices, output_html=args.output, height=args.height)


if __name__ == "__main__":
    main()
