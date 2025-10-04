# NetMap


NetMap es una herramienta de análisis de red desarrollada en **Python** que permite descubrir todos los dispositivos conectados a tu red local y representarlos de manera visual e intuitiva.  

El proyecto está diseñado para estudiantes, administradores de sistemas y entusiastas de la seguridad que deseen comprender mejor qué ocurre en su red doméstica o de trabajo.      

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

**Escaneo desde CLI:**

  Ejecuta el script principal (necesita permisos de root):

    sudo venv/bin/python3 netmap.py

  Opciones disponibles en netmap.py:

     --deep → habilita escaneo profundo (ping, puertos abiertos, SSDP).
     --workers N → define número de hilos para el escaneo paralelo.
     --iface eth0 → fuerza el uso de una interfaz concreta.

  Una vez generado el archivo netmap_results.json, puedes crear el grafo interactivo:

    python3 make_graph.py

**Dashboard web (FastAPI):**

Levanta el servidor en http://localhost:8000

    sudo venv/bin/uvicorn app:app --host 0.0.0.0 --port 8000 --reload

Accede al dashboard en:

    http://localhost:8000


---

## 📊 Ejemplo de salida (v0.42)

  **CLI: Modo Simple**
  
  INFO: Interfaz usada: eth0 (IP origen: 192.168.1.22, Gateway: 192.168.1.1)
  
  INFO: Escaneando red 192.168.1.0/24 en eth0 ... (esto puede tardar unos segundos)
  
  INFO: Resultados guardados en netmap_results.json

  Dispositivos encontrados (resumen):

  |   # | IP          | MAC               | Vendor          |
  |-----|-------------|-------------------|-----------------|
  |   1 | 192.168.1.1 | 58:d3:12:70:30:bc | ZTE Corporation |
  |   2 | 192.168.1.10| 0c:b8:15:75:d0:0b | Espressif       |
  |   3 | 192.168.1.21| 00:45:e2:bb:14:3f | CyberTAN        |

  **CLI: Modo Deep**
  
  INFO: Interfaz usada: eth0 (IP origen: 192.168.1.22, Gateway: 192.168.1.1)
  
  INFO: Escaneando red 192.168.1.0/24 en eth0 ... (esto puede tardar unos segundos)
  
  INFO: Modo deep: probeando 3 hosts con 12 hilos...
  
  INFO: Resultados guardados en netmap_results.json
  
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

**Dashboard:**

Modo oscuro:
<img width="1904" height="901" alt="image" src="https://github.com/user-attachments/assets/fdaf7eb3-4611-401e-8404-30f321a66d12" />

Modo claro:
<img width="1898" height="905" alt="image" src="https://github.com/user-attachments/assets/cc42f01b-1234-468d-a60d-25b1e12b0041" />

---

## 🛣️ Roadmap

- v0.1: Escaneo básico (IP + MAC) ✅
- v0.2: Vendor lookup + tabla formateada ✅
- v0.3: Visualización de red (grafo interactivo en HTML) ✅
- v0.4: Dashboard web (FastAPI) ✅
- v1.0: Exportación avanzada y versión estable y sin errores 🔜
- v1.*: Mejoras de topología y auto-refresco 🔜  
  - Detección de enlaces reales (router ↔ switch ↔ cliente) vía SNMP o captura pasiva.  
  - Auto-refresco en tiempo real con WebSockets.  
  - Notificaciones de nuevos dispositivos directamente en el dashboard. 

---

## 👨‍💻 Autor

Desarrollado por Serner77

