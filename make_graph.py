#!/usr/bin/env python3
"""
make_graph.py
Generador de grafo de red a partir de resultados de netmap.py (netmap_results.json).
Produce un archivo HTML interactivo con pyvis.

Opciones CLI:
  --input FILE   Ruta al JSON de entrada (por defecto netmap_results.json)
  --output FILE  Ruta al HTML de salida (por defecto netmap_graph.html)
  --fa5          Inyecta FontAwesome 5.15 en el HTML generado para iconos modernos
  --height PX    Altura del canvas (por defecto 900px)
"""

import json
import argparse
import networkx as nx
from pyvis.network import Network
import os

# ==========================
#  Configuración de iconos
# ==========================
# Cada clase de dispositivo se asocia a un icono FontAwesome (código unicode),
# tamaño y color. Esto permite representar routers, móviles, PCs, etc.
ICON_MAP = {
    "Router (gateway)": {"face": "FontAwesome", "code": "\uf0ac", "size": 60, "color": "blue"},   # globe
    "Switch/AP": {"face": "FontAwesome", "code": "\uf0ec", "size": 55, "color": "orange"},        # random
    "Ordenador": {"face": "FontAwesome", "code": "\uf108", "size": 50, "color": "cyan"},          # desktop
    "Móvil": {"face": "FontAwesome", "code": "\uf10b", "size": 50, "color": "green"},             # mobile
    "TV / Consola": {"face": "FontAwesome", "code": "\uf26c", "size": 50, "color": "purple"},     # tv
    "Impresora": {"face": "FontAwesome", "code": "\uf02f", "size": 45, "color": "brown"},         # print
    "IoT Device": {"face": "FontAwesome", "code": "\uf013", "size": 45, "color": "pink"},         # cog
    "Desconocido": {"face": "FontAwesome", "code": "\uf128", "size": 40, "color": "gray"}         # question-circle
}


# ==========================
#  Funciones auxiliares
# ==========================

def load_results(filename):
    """Carga resultados de netmap_results.json (listado de dispositivos)."""
    with open(filename, "r") as f:
        return json.load(f)


def choose_icon(node_class):
    """Devuelve el icono a usar para una clase de dispositivo."""
    return ICON_MAP.get(node_class, ICON_MAP["Desconocido"])


# ==========================
#  Construcción del grafo
# ==========================

def build_graph(devices, output_html="netmap_graph.html", height="900px"):
    """
    Construye el grafo de dispositivos con networkx + pyvis.
    - Cada nodo representa un dispositivo.
    - Se dibuja un edge entre cada dispositivo y el gateway (si se detecta).
    - El HTML generado es interactivo (zoom, arrastrar nodos, etc.)
    """
    if not devices:
        print("[!] No hay dispositivos para graficar.")
        return

    G = nx.Graph()

    # Detectar gateway buscando el nodo clasificado como router
    gateway_ip = None
    for d in devices:
        if "router" in d.get("class", "").lower():
            gateway_ip = d["ip"]
            break

    for d in devices:
        ip = d["ip"]
        mac = d.get("mac", "")
        node_class = d.get("class") or "Desconocido"
        icon = choose_icon(node_class)

        # Etiqueta visible y tooltip detallado
        label = f"{ip}\n{node_class}"
        title = (
            f"IP: {ip}\n"
            f"MAC: {mac}\n"
            f"Vendor: {d.get('vendor', 'Unknown')}\n"
            f"Clase: {node_class}"
        )

        # Añadir nodo con icono FA
        G.add_node(ip, label=label, title=title, shape="icon", icon=icon)

        # Conectar cada nodo al gateway (topología estrella)
        if gateway_ip and ip != gateway_ip:
            G.add_edge(gateway_ip, ip)

    # Crear visualización pyvis
    net = Network(height=height, width="100%", bgcolor="#222222", font_color="white")
    net.from_nx(G)

    # Física para evitar solapamiento
    net.repulsion(node_distance=300, central_gravity=0.2, spring_length=200)
    net.toggle_physics(True)

    # Guardar HTML
    net.write_html(output_html, open_browser=False)
    print(f"[i] Grafo generado en {output_html}")


def inject_fa5(html_file):
    """
    Inyecta FontAwesome 5.15 en el HTML generado por pyvis.
    Útil porque pyvis trae FA4 por defecto (limitado).
    """
    try:
        with open(html_file, "r", encoding="utf-8") as f:
            html = f.read()
        old = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/4.7.0/css/font-awesome.min.css'
        new = 'https://cdnjs.cloudflare.com/ajax/libs/font-awesome/5.15.4/css/all.min.css'
        if old in html:
            html = html.replace(old, new)
        elif "</head>" in html:
            insert_css = f'<link rel="stylesheet" href="{new}">\n'
            html = html.replace("</head>", insert_css + "</head>")
        with open(html_file, "w", encoding="utf-8") as f:
            f.write(html)
        print("[i] Inyectado FontAwesome 5.15 en el HTML.")
    except Exception as e:
        print(f"[!] No se pudo inyectar FA5: {e}")


# ==========================
#  Main
# ==========================

def main():
    p = argparse.ArgumentParser(description="Generador de grafo desde netmap_results.json")
    p.add_argument("--input", "-i", default="netmap_results.json")
    p.add_argument("--output", "-o", default="netmap_graph.html")
    p.add_argument("--fa5", action="store_true", help="Inyecta FontAwesome 5.15 en el HTML resultante")
    p.add_argument("--height", default="900px", help="Alto del canvas HTML")
    args = p.parse_args()

    if not os.path.exists(args.input):
        print(f"[!] Archivo {args.input} no encontrado. Ejecuta netmap.py primero.")
        return

    devices = load_results(args.input)
    build_graph(devices, output_html=args.output, height=args.height)

    if args.fa5:
        inject_fa5(args.output)
        print("[i] Usa códigos FA5 en ICON_MAP si quieres iconos modernos.")


if __name__ == "__main__":
    main()

