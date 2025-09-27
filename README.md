# NetMap

NetMap es una herramienta de análisis de red desarrollada en **Python** que permite descubrir todos los dispositivos conectados a tu red local y representarlos de manera visual e intuitiva.  

El proyecto está diseñado para estudiantes, administradores de sistemas y entusiastas de la seguridad que deseen comprender mejor qué ocurre en su red doméstica o de trabajo.  

---

## ✨ Características implementadas
- ✅ Escaneo de red mediante ARP para detectar dispositivos.  
- ✅ Identificación de direcciones **IP** y **MAC**.  
- ✅ Identificación de fabricantes (**OUI lookup**).  
- ✅ Representación en **tabla clara y alineada** (CLI).  

---

## 🚧 Próximas funcionalidades
- 🔜 Grafo interactivo en **HTML** con los dispositivos conectados.  
- 🔜 **Dashboard web** ligero para visualizar la red en tiempo real.  
- 🔜 Exportación de resultados en diferentes formatos (**JSON/PDF**).  
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

## ▶️ Uso

  Ejecuta el script principal (necesita permisos de root):

    sudo venv/bin/python3 netmap.py

## 📊 Ejemplo de salida (v0.2)

  [i] Escaneando red 192.168.1.0/24 en eth0 ... (esto puede tardar unos segundos)

  Dispositivos encontrados:
  |   # | IP            | MAC               | Vendor     |
  |-----|---------------|-------------------|------------|
  |   1 | 192.168.1.1   | 58:d3:12:70:30:bc | Unknown    | 
  |   2 | 192.168.1.10  | 0c:b8:15:75:d0:0b | Espressif  |
  |   3 | 192.168.1.21  | 00:45:e2:bb:14:3f | CyberTAN   |

## 🛣️ Roadmap

- v0.1: Escaneo básico (IP + MAC) ✅
- v0.2: Vendor lookup + tabla formateada ✅
- v0.3: Visualización de red (grafo interactivo en HTML) 🔜
- v0.4: Dashboard web (Flask/FastAPI) 🔜
- v1.0: Exportación avanzada y alertas 🔜

## 👨‍💻 Autor

Desarrollado por Serner77

