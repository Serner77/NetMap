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
from pyvis.network import Network

# ==========================
#  Configuración de iconos
# ==========================
# Mapeo clase → icono (ruta absoluta servida por FastAPI en /static/icons).
# Cada dispositivo se representa con un icono específico y color diferenciado.
# NOTA: Los iconos deben existir en static/icons/ (ej: router.svg, switch.svg...).
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

# Imagen de fallback si algún icono no carga correctamente
BROKEN_IMAGE = "/static/icons/unknown.svg"


# ==========================
#  Funciones auxiliares
# ==========================

def load_results(filename: str):
    """
    Carga el archivo JSON con la lista de dispositivos descubiertos por netmap.py.

    :param filename: Ruta al JSON (por defecto netmap_results.json)
    :return: Lista de diccionarios con dispositivos
    """
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)


def icon_for(node_class: str) -> str:
    """
    Devuelve la ruta del icono asociado a la clase de dispositivo.

    :param node_class: Clase del dispositivo (ej: "Router (gateway)", "Móvil", etc.)
    :return: Ruta al icono (str)
    """
    return ICON_MAP.get(node_class or "Desconocido", ICON_MAP["Desconocido"])


# ==========================
#  Construcción del grafo
# ==========================

def build_graph(devices, output_html="netmap_graph.html", height="900px"):
    """
    Construye el grafo de la red utilizando NetworkX + PyVis.

    - Cada nodo corresponde a un dispositivo detectado.
    - Cada nodo se muestra con un icono (SVG/PNG) en función de su clase.
    - Se conecta cada dispositivo al gateway detectado (topología en estrella).
    - El HTML generado es interactivo: zoom, arrastre de nodos, tooltips.

    :param devices: Lista de dispositivos (dicts con keys ip, mac, vendor, class)
    :param output_html: Nombre del archivo HTML de salida
    :param height: Altura del canvas (ej: "900px")
    """
    if not devices:
        print("[!] No hay dispositivos para graficar.")
        return

    G = nx.Graph()

    # Detectar gateway (primer dispositivo clasificado como router)
    gateway_ip = None
    for d in devices:
        if "router" in (d.get("class") or "").lower():
            gateway_ip = d["ip"]
            break
    if not gateway_ip and devices:
        gateway_ip = devices[0]["ip"]  # fallback si no se detecta router

    # Añadir nodos al grafo
    for d in devices:
        ip = d["ip"]
        mac = d.get("mac", "")
        vendor = d.get("vendor", "Unknown")
        node_class = d.get("class") or "Desconocido"

        image_url = icon_for(node_class)

        # Tooltip mostrado al pasar el ratón por encima
        title = (
            f"IP: {ip}\n"
            f"Clase: {node_class}\n"
            f"MAC: {mac}\n"
            f"Vendor: {vendor}"
        )

        G.add_node(
            ip,
            label="",                 # dejamos solo icono (sin texto redundante)
            title=title,              # tooltip con saltos de línea \n
            shape="image",            # representación con imagen
            image=image_url,          # ruta al icono
            size = 40,
            brokenImage=BROKEN_IMAGE, # fallback si falla el icono
            borderWidth=0
        )

    # Conectar cada dispositivo al gateway (topología en estrella simple)
    for d in devices:
        ip = d["ip"]
        if gateway_ip and ip != gateway_ip:
            G.add_edge(gateway_ip, ip)

    # Crear visualización con PyVis
    net = Network(height=height, width="100%", bgcolor="#111111", font_color="white")
    net.from_nx(G)

    # Configurar física para que los nodos no se solapen
    net.repulsion(
        node_distance=320,
        central_gravity=0.18,
        spring_length=210,
        spring_strength=0.02
    )

    # Exportar HTML
    net.write_html(output_html, open_browser=False)
    print(f"[i] Grafo generado en {output_html}")


# ==========================
#  Main (CLI)
# ==========================

def main():
    """
    CLI del generador de grafo.
    Permite invocar desde terminal con parámetros.
    """
    p = argparse.ArgumentParser(description="Generador de grafo desde netmap_results.json")
    p.add_argument("--input", "-i", default="netmap_results.json", help="Archivo JSON con resultados de netmap")
    p.add_argument("--output", "-o", default="netmap_graph.html", help="Archivo HTML de salida")
    p.add_argument("--height", default="900px", help="Alto del canvas HTML (ej: 600px, 100%)")
    args = p.parse_args()

    if not os.path.exists(args.input):
        print(f"[!] Archivo {args.input} no encontrado. Ejecuta netmap.py primero.")
        return

    devices = load_results(args.input)
    build_graph(devices, output_html=args.output, height=args.height)


if __name__ == "__main__":
    main()
