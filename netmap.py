#!/usr/bin/env python3
import sys
import ipaddress
from scapy.all import ARP, Ether, srp, conf
import subprocess
import re

def get_default_iface():
    # usa 'ip route get' para obtener iface y source ip
    try:
        out = subprocess.check_output(["ip", "route", "get", "8.8.8.8"], text=True)
        m = re.search(r"dev (\S+).*src (\S+)", out)
        if m:
            return m.group(1), m.group(2)
    except Exception as e:
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
        print("[!] No se han encontrado dispositivos. Prueba los pasos de troubleshooting:")
        print("   - Comprueba permisos (ejecuta con sudo).")
        print("   - Verifica que la interfaz y la subred sean correctas.")
        print("   - Prueba 'sudo arp-scan --interface=<iface> --localnet' o 'sudo nmap -sn -PR <red>'")
        print("   - Revisa si la red es 'guest' o tiene aislamiento de cliente a cliente.")
        sys.exit(0)

    print("Dispositivos encontrados:")
    for d in devices:
        print(f" - {d['ip']}   {d['mac']}")

