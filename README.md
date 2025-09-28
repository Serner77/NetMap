# NetMap


NetMap es una herramienta de análisis de red desarrollada en **Python** que permite descubrir todos los dispositivos conectados a tu red local y representarlos de manera visual e intuitiva.  

El proyecto está diseñado para estudiantes, administradores de sistemas y entusiastas de la seguridad que deseen comprender mejor qué ocurre en su red doméstica o de trabajo.  

---

## ✨ Características implementadas
- ✅ Escaneo de red mediante ARP para detectar dispositivos.  
- ✅ Identificación de direcciones **IP** y **MAC**.  
- ✅ Identificación de fabricantes (**OUI lookup**).
- ✅Clasificación heurística de dispositivos: router, switch/AP, ordenador, móvil, impresora, TV/consola, IoT…
- ✅ Exportación de resultados a **JSON**.  
- ✅ Representación en **tabla clara y alineada** (CLI).
- ✅ **Grafo interactivo en HTML** con iconos según el tipo de dispositivo.  



## 🚧 Próximas funcionalidades
- 🔜 **Dashboard web** ligero para visualizar la red en tiempo real.  
- 🔜 Exportación avanzada en múltiples formatos (**PDF, CSV, Excel**).  .
- 🔜 Detección de relaciones entre dispositivos (router principal, puntos de acceso, etc.).    
- 🔜 **Sistema de alertas** al detectar nuevos dispositivos desconocidos.  

---

## 📦 Instalación

  Clona este repositorio y entra al directorio:

    git clone https://github.com/Serner77/NetMap.git
    cd NetMap

  Crea un entorno virtual (recomendado):

    python3 -m venv venv
    source venv/bin/activate

  Instala las dependencias:

    pip install -r requirements.txt

---

## ▶️ Uso
  Ejecuta el script principal (necesita permisos de root):

    sudo venv/bin/python3 netmap.py

  Opciones disponibles en netmap.py:

     --deep → habilita escaneo profundo (ping, puertos abiertos, SSDP).
     --workers N → define número de hilos para el escaneo paralelo.
     --iface eth0 → fuerza el uso de una interfaz concreta.

  Una vez generado el archivo netmap_results.json, puedes crear el grafo interactivo:

    python3 make_graph.py

---

## 📊 Ejemplo de salida (v0.3)

  [i] Escaneando red 192.168.1.0/24 en eth0 ... (esto puede tardar unos segundos)

  Dispositivos encontrados (resumen):
  |   # | IP          | MAC               | Vendor          |   TTL | Open ports   | Clase            |
  |-----|-------------|-------------------|-----------------|-------|--------------|------------------|
  |   1 | 192.168.1.1 | 58:d3:12:70:30:bc | ZTE Corporation |    64 | [80, 443]    | Router (gateway) |
  |   2 | 192.168.1.10| 0c:b8:15:75:d0:0b | Espressif       |   255 | []           | IoT Device       |
  |   3 | 192.168.1.21| 00:45:e2:bb:14:3f | CyberTAN        |   128 | []           | Ordenador        |

**HTML (grafo interactivo):**
  El grafo muestra cada dispositivo con un icono distinto:

  - 🌐 Router → azul
  - 📶 Switch/AP → naranja
  - 💻 Ordenador → cian
  - 📱 Móvil → verde
  - 📺 TV/Consola → morado
  - 🖨️ Impresora → marrón
  - ⚙️ IoT → rosa
  - ❔ Desconocido → gris

---

## 🛣️ Roadmap

- v0.1: Escaneo básico (IP + MAC) ✅
- v0.2: Vendor lookup + tabla formateada ✅
- v0.3: Visualización de red (grafo interactivo en HTML) ✅
- v0.4: Dashboard web (Flask/FastAPI) 🔜
- v1.0: Exportación avanzada y alertas 🔜

---

## 👨‍💻 Autor

Desarrollado por Serner77

