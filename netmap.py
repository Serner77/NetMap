#!/usr/bin/env python3 
import sys
import ipaddress
from scapy.all import ARP, Ether, srp, conf
from manuf import manuf 
from tabulate import tabulate
import subprocess
import re
import json

def get_default_iface():
    try:
        out = subprocess.check_output(["ip", "route", "get", "8.8.8.8"], text=True)
        m = re.search(r"dev (\S+).*src (\S+)", out)
        if m:
            return m.group(1), m.group(2)
    except Exception:
        return None, None
    return None, None

def iface_has_ip(iface):
    try:
        out = subprocess.check_output(["ip", "-4", "addr", "show", "dev", iface], text=True)
        return "inet " in out
    except:
        return False

def scan_network(network, iface):
    conf.verb = 0
    conf.iface = iface
    arp = ARP(pdst=str(network))
    ether = Ether(dst="ff:ff:ff:ff:ff:ff")
    packet = ether/arp
    try:
        ans = srp(packet, timeout=3, retry=1)[0]
    except Exception as e:
        print(f"[!] Error enviando paquetes con Scapy: {e}")
        return []
    devices = []
    for sent, received in ans:
        devices.append({'ip': received.psrc, 'mac': received.hwsrc})
    return devices

def add_vendor_info(devices):
    p = manuf.MacParser()
    enhanced = []
    for d in devices:
        vendor = p.get_manuf(d['mac']) or "Unknown"
        enhanced.append({'ip': d['ip'], 'mac': d['mac'], 'vendor': vendor})
    return enhanced

def save_results(devices, filename="netmap_results.json"):
    with open(filename, "w") as f:
        json.dump(devices, f, indent=2)
    print(f"[i] Resultados guardados en {filename}")

if __name__ == "__main__":
    if not hasattr(conf, 'iface'):
        conf.iface = None
    iface, src_ip = get_default_iface()
    if not iface:
        print("[!] No se pudo detectar la interfaz por defecto. Ejecuta: ip route get 8.8.8.8")
        sys.exit(1)
    print(f"[i] Interfaz detectada: {iface} (IP origen: {src_ip})")
    if not iface_has_ip(iface):
        print(f"[!] La interfaz {iface} no tiene IP asignada. Revisa la conexión.")
        sys.exit(1)

    # calcular red a partir de la IP local
    try:
        out = subprocess.check_output(["ip", "-4", "addr", "show", "dev", iface], text=True)
        m = re.search(r"inet (\d+\.\d+\.\d+\.\d+)/(\d+)", out)
        if not m:
            print("[!] No pude leer la máscara de la interfaz.")
            sys.exit(1)
        ip_str, prefix = m.group(1), int(m.group(2))
        network = ipaddress.ip_network(f"{ip_str}/{prefix}", strict=False)
    except Exception as e:
        print(f"[!] Error calculando subred: {e}")
        sys.exit(1)

    print(f"[i] Escaneando red {network} en {iface} ... (esto puede tardar unos segundos)")
    devices = scan_network(network, iface)
    if not devices:
        print("[!] No se han encontrado dispositivos.")
        sys.exit(0)

    # añadir fabricantes
    devices = add_vendor_info(devices)

    # imprimir tabla
    table = [[i+1, d['ip'], d['mac'], d['vendor']] for i, d in enumerate(devices)]
    print("\nDispositivos encontrados:")
    print(tabulate(table, headers=["#", "IP", "MAC", "Vendor"], tablefmt="github"))
    
    # exportar resultados a JSON
    save_results(devices)


