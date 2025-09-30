#!/usr/bin/env python3
"""
netmap.py v0.41
Escaneo de red basado en ARP + heurísticas para clasificar dispositivos.
Permite un modo simple (--deep off) o un modo profundo (--deep) con:
- Ping TTL
- Escaneo de puertos TCP
- Probes SSDP

Salida: netmap_results.json (con toda la info estructurada)
Autor: Serner77
"""

import sys
import ipaddress
import subprocess
import re
import json
import socket
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from argparse import ArgumentParser

from scapy.all import ARP, Ether, srp, conf
from tabulate import tabulate

# Vendor lookup opcional
try:
    from mac_vendor_lookup import MacLookup
    MACLOOKUP_AVAILABLE = True
except Exception:
    MACLOOKUP_AVAILABLE = False


# ==============================
#  Logging con colores
# ==============================

class ColorFormatter(logging.Formatter):
    COLORS = {
        logging.DEBUG: "\033[37m",    # gris
        logging.INFO: "\033[36m",     # cian
        logging.WARNING: "\033[33m",  # amarillo/naranja
        logging.ERROR: "\033[31m",    # rojo
        logging.CRITICAL: "\033[41m", # fondo rojo
    }
    RESET = "\033[0m"

    def format(self, record):
        base = super().format(record)
        # separa "LEVEL: mensaje"
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

logger = logging.getLogger("netmap")


# ==============================
#  Constantes y listas de puertos
# ==============================

PRINTER_PORTS = {515, 631, 9100}
NAS_PORTS     = {5000, 5001, 32400}
TV_PORTS      = {5500, 7000, 8008, 8009, 8443, 8200, 32469}

# Conjunto extendido de puertos comunes + específicos
COMMON_PORTS = sorted({22, 80, 443, 445} | PRINTER_PORTS | NAS_PORTS | TV_PORTS)


# ==============================
#  Funciones auxiliares de red
# ==============================

def get_default_iface():
    """
    Detecta la interfaz de red por defecto, la IP origen y el gateway.
    Usa el comando `ip route get 8.8.8.8`.
    """
    try:
        out = subprocess.check_output(["ip", "route", "get", "8.8.8.8"], text=True)
        m_if = re.search(r"dev (\S+)", out)
        m_ip = re.search(r"src (\S+)", out)
        m_gw = re.search(r"via (\d+\.\d+\.\d+\.\d+)", out)
        if m_if:
            return (
                m_if.group(1),
                m_ip.group(1) if m_ip else None,
                m_gw.group(1) if m_gw else None,
            )
    except Exception:
        return None, None, None
    return None, None, None


# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
#  NUEVO: Info de interfaz cuando se fuerza --iface
# >>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>>
def get_iface_info(iface: str):
    """
    Obtiene la IP asignada a la interfaz indicada y el gateway por defecto.
    - Intenta extraer la IP de la interfaz concreta.
    - Intenta extraer el gateway por defecto; si hay múltiples, usa el que
      esté asociado a la interfaz cuando sea posible.
    """
    ip_addr = None
    gateway_ip = None

    try:
        # Obtener IP v4 de la interfaz indicada
        out = subprocess.check_output(["ip", "-4", "addr", "show", "dev", iface], text=True)
        m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)", out)
        if m:
            ip_addr = m.group(1)
    except Exception:
        pass

    try:
        # Preferir ruta por defecto asociada a esa interfaz, si existe
        out = subprocess.check_output(["ip", "route", "show", "default", "dev", iface], text=True)
        m = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", out)
        if not m:
            # Fallback: ruta por defecto global
            out = subprocess.check_output(["ip", "route", "show", "default"], text=True)
            m = re.search(r"default via (\d+\.\d+\.\d+\.\d+)", out)
        if m:
            gateway_ip = m.group(1)
    except Exception:
        pass

    return ip_addr, gateway_ip


def iface_has_ip(iface):
    """Comprueba si una interfaz tiene IP v4 asignada."""
    try:
        out = subprocess.check_output(["ip", "-4", "addr", "show", "dev", iface], text=True)
        return "inet " in out
    except Exception:
        return False


def scan_network(network, iface, timeout=3, retry=1):
    """
    Realiza un escaneo ARP sobre toda la subred indicada.
    Devuelve lista de dicts con ip y mac.
    """
    conf.verb = 0
    conf.iface = iface
    arp = ARP(pdst=str(network))
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether / arp
    try:
        ans = srp(packet, timeout=timeout, retry=retry)[0]
    except Exception as e:
        logger.error(f"Error ARP (Scapy): {e}")
        return []
    devices = []
    for _, rcv in ans:
        devices.append({'ip': rcv.psrc, 'mac': rcv.hwsrc})
    return devices


def is_random_mac(mac):
    """
    Determina si una MAC es aleatoria (bit U/L activado).
    Muy típico en móviles modernos.
    """
    try:
        first_byte = int(mac.split(":")[0], 16)
        return bool(first_byte & 2)
    except Exception:
        return False


# ==============================
#  Vendor lookup (MAC → fabricante)
# ==============================

def update_mac_db(maclookup):
    """Fuerza actualización de base de datos local de vendors (si disponible)."""
    try:
        maclookup.update_vendors()
        return True
    except Exception:
        return False


def lookup_vendor_safe(maclookup, mac):
    """Consulta segura: devuelve vendor o 'Unknown' si falla."""
    try:
        return maclookup.lookup(mac)
    except Exception:
        return "Unknown"


# ==============================
#  Probes por host (TTL, puertos, SSDP)
# ==============================

def ping_ttl(ip, timeout=1):
    """Hace ping al host y devuelve el TTL del reply, si lo hay."""
    try:
        out = subprocess.check_output(
            ["ping", "-c", "1", "-W", str(timeout), ip],
            stderr=subprocess.DEVNULL, text=True, timeout=timeout + 1
        )
        m = re.search(r"ttl=(\d+)", out, re.IGNORECASE)
        if m:
            return int(m.group(1))
    except Exception:
        return None
    return None


def tcp_port_scan(ip, ports, conn_timeout=0.5):
    """Escanea una lista de puertos TCP (connect scan)."""
    open_ports = []
    for p in ports:
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(conn_timeout)
                res = s.connect_ex((ip, p))
                if res == 0:
                    open_ports.append(p)
        except Exception:
            pass
    return open_ports


def ssdp_probe(ip, timeout=0.9):
    """
    Envia un probe SSDP unicast al host (UDP/1900).
    Algunos dispositivos IoT/TV responden.
    """
    msg = '\r\n'.join([
        'M-SEARCH * HTTP/1.1',
        'HOST:239.255.255.250:1900',
        'MAN:"ssdp:discover"',
        'MX:1',
        'ST:ssdp:all',
        '', ''
    ]).encode('utf-8')

    resp_texts = []
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.settimeout(timeout)
            sock.sendto(msg, (ip, 1900))
            start = time.time()
            while True:
                if time.time() - start > timeout:
                    break
                try:
                    data, _ = sock.recvfrom(2048)
                    resp_texts.append(data.decode('utf-8', errors='ignore'))
                except socket.timeout:
                    break
                except Exception:
                    break
    except Exception:
        pass
    return resp_texts


# ==============================
#  Clasificación de dispositivos
# ==============================

def refine_classification(vendor, ip, gateway_ip, mac, ttl, open_ports, ssdp_responses):
    """
    Clasifica un dispositivo en categorías heurísticas basadas en:
    - vendor (MAC)
    - puertos abiertos
    - TTL de ping
    - respuestas SSDP
    """
    vlow = (vendor or "Unknown").lower()
    open_set = set(open_ports or [])

    INFRA_VENDORS = ["cisco", "ubiquiti", "tplink", "tp-link", "netgear",
                     "mikrotik", "aruba", "juniper", "d-link", "huawei", "zyxel"]
    IOT_VENDORS = ["espressif", "tuya", "sonoff", "shelly", "tapo", "hikvision", "ring", "dahua"]
    CHIP_VENDORS = ["realtek", "broadcom", "qualcomm", "mediatek", "intel"]
    MOBILE_BRANDS = ["apple", "samsung", "xiaomi", "huawei", "oppo",
                     "oneplus", "motorola", "sony", "google"]

    # 1) Router principal
    if ip == gateway_ip:
        return "Router (gateway)"

    # 2) Impresoras / TVs
    if open_set & PRINTER_PORTS:
        return "Impresora"
    if open_set & TV_PORTS:
        return "TV / Consola"

    # 3) Infraestructura de red
    if any(x in vlow for x in INFRA_VENDORS):
        if open_set & {80, 443} or ssdp_responses:
            return "Switch/AP"
        return "Infraestructura de red (posible switch/AP)"

    # 4) IoT
    if any(x in vlow for x in IOT_VENDORS):
        return "IoT Device"

    # 5) Móvil (MAC aleatoria o vendor)
    if is_random_mac(mac) or any(x in vlow for x in MOBILE_BRANDS):
        return "Móvil"

    # 6) Según TTL
    if ttl:
        if 120 <= ttl <= 130 or (445 in open_set or 22 in open_set) or any(x in vlow for x in CHIP_VENDORS):
            return "Ordenador"
        if 58 <= ttl <= 66:
            if open_set & {80, 443, 22}:
                return "Switch/AP"
            if any(x in vlow for x in MOBILE_BRANDS):
                return "Móvil"
            return "Ordenador"

    # 7) Fallback
    return "Desconocido"


def probe_device(entry, gateway_ip, ports=COMMON_PORTS):
    """
    Ejecuta todos los probes sobre un host:
    - Ping TTL
    - Escaneo de puertos
    - SSDP
    Y devuelve la clasificación.
    """
    ip = entry['ip']
    mac = entry.get('mac', '')
    vendor = entry.get('vendor', 'Unknown')

    ttl = ping_ttl(ip, timeout=1)
    open_ports = tcp_port_scan(ip, ports)
    ssdp_responses = ssdp_probe(ip, timeout=0.8)

    classification = refine_classification(vendor, ip, gateway_ip, mac, ttl, open_ports, ssdp_responses)

    return {
        'ip': ip,
        'mac': mac,
        'vendor': vendor,
        'ttl': ttl,
        'open_ports': open_ports,
        'ssdp': ssdp_responses,
        'class': classification
    }


# ==============================
#  Flujo de escaneo completo
# ==============================

def add_vendor_info_basic(devices):
    """
    Añade información de vendor a cada dispositivo según su MAC.
    Usa mac_vendor_lookup si está disponible.
    """
    enhanced = []
    maclookup = MacLookup() if MACLOOKUP_AVAILABLE else None
    if maclookup:
        try:
            update_mac_db(maclookup)
        except Exception:
            pass

    for d in devices:
        vendor = "Unknown"
        if maclookup:
            vendor = lookup_vendor_safe(maclookup, d['mac'])
        if vendor == "Unknown" and is_random_mac(d['mac']):
            vendor = "MAC Aleatoria (posible móvil)"
        enhanced.append({'ip': d['ip'], 'mac': d['mac'], 'vendor': vendor})
    return enhanced


def deep_scan_devices(devices, gateway_ip, workers=12):
    """
    Ejecuta probe_device en paralelo sobre todos los hosts encontrados.
    """
    workers = max(1, int(workers))
    results = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        future_to_ip = {ex.submit(probe_device, d, gateway_ip): d['ip'] for d in devices}
        for fu in as_completed(future_to_ip):
            try:
                res = fu.result()
                results.append(res)
            except Exception as e:
                ip = future_to_ip[fu]
                logger.warning(f"Error probando {ip}: {e}")
    results.sort(key=lambda x: tuple(int(p) for p in x['ip'].split('.')))
    return results


def save_results(devices, filename="netmap_results.json", deep=False):
    """Guarda resultados en JSON con metadata."""
    payload = {
        "_meta": {"deep": deep, "ts": time.time()},
        "devices": devices
    }
    with open(filename, "w") as f:
        json.dump(payload, f, indent=2)
    logger.info(f"Resultados guardados en {filename}")


# ==============================
#  Main
# ==============================

def main():
    parser = ArgumentParser(description="NetMap - ARP + heurísticas (modo --deep opcional)")
    parser.add_argument("--deep", action="store_true", help="Habilitar escaneo profundo por host (ping/ports/SSDP)")
    parser.add_argument("--workers", type=int, default=12, help="Número de hilos para el modo deep (default 12)")
    parser.add_argument("--iface", type=str, default=None, help="Forzar interfaz de red (ej: eth0)")
    args = parser.parse_args()

    if not hasattr(conf, 'iface'):
        conf.iface = None

    # Validación de workers
    if args.deep:
        if args.workers < 1:
            logger.error("--workers debe ser un entero >= 1 cuando se usa --deep")
            sys.exit(1)
    else:
        if args.workers != 12:
            logger.warning("--workers se ignora si no usas --deep")
        args.workers = None

    iface = args.iface
    src_ip = None
    gateway_ip = None

    if not iface:
        iface, src_ip, gateway_ip = get_default_iface()
    else:
        # Cuando se fuerza --iface, obtener también la IP origen y el gateway
        src_ip, gateway_ip = get_iface_info(iface)

    if not iface:
        logger.error("No se pudo detectar la interfaz por defecto. Usa --iface o ejecuta: ip route get 8.8.8.8")
        sys.exit(1)
    logger.info(f"Interfaz usada: {iface} (IP origen: {src_ip}, Gateway: {gateway_ip})")

    if not iface_has_ip(iface):
        logger.error(f"La interfaz {iface} no tiene IP asignada. Revisa la conexión.")
        sys.exit(1)

    # calcular subred
    try:
        out = subprocess.check_output(["ip", "-4", "addr", "show", "dev", iface], text=True)
        m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", out)
        if not m:
            logger.error("No pude leer la máscara de la interfaz.")
            sys.exit(1)
        ip_str, prefix = m.group(1), int(m.group(2))
        network = ipaddress.ip_network(f"{ip_str}/{prefix}", strict=False)
    except Exception as e:
        logger.error(f"Error calculando subred: {e}")
        sys.exit(1)

    logger.info(f"Escaneando red {network} en {iface} ... (esto puede tardar unos segundos)")
    devices = scan_network(network, iface)
    if not devices:
        logger.warning("No se han encontrado dispositivos.")
        sys.exit(0)

    devices_basic = add_vendor_info_basic(devices)

    if args.deep:
        logger.info(f"Modo deep: probeando {len(devices_basic)} hosts con {args.workers} hilos...")
        devices_out = deep_scan_devices(devices_basic, gateway_ip=gateway_ip, workers=args.workers)
    else:
        devices_out = []
        for d in devices_basic:
            devices_out.append({
                'ip': d['ip'],
                'mac': d['mac'],
                'vendor': d['vendor'],
                'ttl': None,
                'open_ports': [],
                'ssdp': [],
                'class': d['vendor']
            })
            
    if gateway_ip:
        for d in devices_out:
            if d['ip'] == gateway_ip:
                d['class'] = "Router (gateway)"

    save_results(devices_out, deep=args.deep)

    # imprimir tabla resumen
    table = []
    if args.deep:
        headers = ["#", "IP", "MAC", "Vendor", "TTL", "Open ports", "Clase"]
        for i, d in enumerate(devices_out):
            cls = d.get('class') or d.get('vendor') or "Unknown"
            table.append([
                i+1,
                d['ip'],
                d['mac'],
                d.get('vendor'),
                d.get('ttl'),
                d.get('open_ports'),
                cls
            ])
    else:
        headers = ["#", "IP", "MAC", "Vendor"]
        for i, d in enumerate(devices_out):
            table.append([i+1, d['ip'], d['mac'], d.get('vendor')])

    print("\nDispositivos encontrados (resumen):\n")
    print(tabulate(table, headers=headers, tablefmt="github"))


if __name__ == "__main__":
    main()
