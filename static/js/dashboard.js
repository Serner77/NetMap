function netmapApp() {
      return {
        // Estado
        devices: [],
        previousIPs: new Set(),
        metrics: { total: 0, active: 0, iot: 0, newDevices: 0 },
        classes: ["Router (gateway)","Switch/AP","Ordenador","Móvil","TV / Consola","Impresora","IoT Device","Desconocido"],
        activeClasses: new Set(),
        q: "",
        deep: true,
        workers: 12,
        refreshSeconds: 10,
        timer: null,
        job: null,
        status: null,
        toasts: [],
        dark: window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches,

        init() {
          this.loadDevices();
          //this.setupAutoRefresh();
          this.renderIcons();
          this.restoreTheme();
        },

        renderIcons() { window.lucide && window.lucide.createIcons(); },

        persistTheme(){ localStorage.setItem('netmap_dark', this.dark ? '1':'0'); },
        restoreTheme(){ this.dark = localStorage.getItem('netmap_dark') === '1' || this.dark; },

        /*setupAutoRefresh() {
          this.clearTimer();
          if (this.refreshSeconds > 0) {
            this.timer = setInterval(() => this.loadDevices(), this.refreshSeconds * 1000);
          }
        },
        clearTimer() { if (this.timer) clearInterval(this.timer); },
        */

        async loadDevices() {
          try {
            const res = await fetch('/api/devices');
            if (!res.ok) throw new Error('No se pudieron cargar dispositivos');
            const data = await res.json();
            const newList = data.devices || [];
            // métricas
            this.metrics.total = newList.length;
            this.metrics.active = newList.filter(d => (d.ttl && d.ttl > 0) || (d.open_ports || []).length).length;
            this.metrics.iot = newList.filter(d => (d.class || '').toLowerCase().includes('iot')).length;
            const currIPs = new Set(newList.map(d => d.ip));
            const newIPs = [...currIPs].filter(ip => !this.previousIPs.has(ip));
            this.metrics.newDevices = newIPs.length;
            this.previousIPs = currIPs;

            // orden por IP
            newList.sort((a,b) => a.ip.split('.').map(Number).reduce((acc,v,i)=>acc+(v - b.ip.split('.')[i])*(256**(3-i)),0));
            this.devices = newList;

            // si hay job corriendo, consulta estado
            if (this.job) { this.checkStatus(); }
          } catch (e) {
            this.toast('Error: ' + e.message, 'error');
          } finally {
            this.$nextTick(()=>this.renderIcons());
          }
        },

        get filteredDevices() {
          const q = this.q.toLowerCase().trim();
          return this.devices.filter(d => {
            const classMatch = this.activeClasses.size === 0 || this.activeClasses.has(d.class || 'Desconocido');
            const qMatch = !q || [d.ip, d.mac, d.vendor, d.class].join(' ').toLowerCase().includes(q);
            return classMatch && qMatch;
          });
        },

        toggleClass(tag){
          if (this.activeClasses.has(tag)) this.activeClasses.delete(tag); else this.activeClasses.add(tag);
        },

        badgeClass(c) {
          const x = (c || 'Desconocido').toLowerCase();
          if (x.includes('router')) return 'bg-blue-600/15 text-blue-600 dark:text-blue-400';
          if (x.includes('switch') || x.includes('ap')) return 'bg-amber-500/15 text-amber-600 dark:text-amber-400';
          if (x.includes('ordenador')) return 'bg-cyan-500/15 text-cyan-600 dark:text-cyan-400';
          if (x.includes('móvil') || x.includes('movil')) return 'bg-emerald-500/15 text-emerald-600 dark:text-emerald-400';
          if (x.includes('tv') || x.includes('consola')) return 'bg-purple-500/15 text-purple-600 dark:text-purple-400';
          if (x.includes('impresora')) return 'bg-rose-500/15 text-rose-600 dark:text-rose-400';
          if (x.includes('iot')) return 'bg-pink-500/15 text-pink-600 dark:text-pink-400';
          return 'bg-slate-500/15 text-slate-600 dark:text-slate-400';
        },

        async scan() {
	  if (this.workers < 1) {
	    this.toast("El número de hilos debe ser al menos 1", "error");
	    return;
	  }
	  
	  if (this.job) {
	    // Si ya hay job → cancelar
	    try {
	      const res = await fetch(`/api/scan/cancel/${this.job}`, { method: 'POST' });
	      if (res.ok) {
		this.toast('Escaneo cancelado');
		this.job = null;
		this.status = null;
	      } else {
		this.toast('No se pudo cancelar el escaneo', 'error');
	      }
	    } catch (e) {
	      this.toast('Error al cancelar: ' + e.message, 'error');
	    }
	    return;
	  }

	  // Iniciar escaneo
	  try {
	    const url = `/api/scan?deep=${this.deep}&workers=${this.workers}`;
	    const res = await fetch(url, { method: 'POST' });
	    if (!res.ok) throw new Error('No se pudo iniciar el escaneo');
	    const data = await res.json();
	    this.job = data.job_id;
	    this.status = { state: 'pending' };
	    this.toast('Escaneo iniciado');
	    this.pollStatus();
	  } catch (e) {
	    this.toast('Error: ' + e.message, 'error');
	  }
	},

        async pollStatus() {
          if (!this.job) return;
          const poll = async () => {
            await this.checkStatus();
            if (this.status && (this.status.state === 'running' || this.status.state === 'pending')) {
              setTimeout(poll, 1500);
            } else if (this.status && this.status.state === 'done') {
              this.toast('Escaneo completado');
              await this.loadDevices();
              this.reloadGraph();
              this.job = null;
            } else if (this.status && this.status.state === 'error') {
              this.toast('Escaneo falló: ' + (this.status.message || ''), 'error');
              this.job = null;
            }
          };
          poll();
        },

        async checkStatus() {
          if (!this.job) return;
          const res = await fetch(`/api/scan/status/${this.job}`);
          if (res.ok) this.status = await res.json();
          this.$nextTick(()=>this.renderIcons());
        },

        reloadGraph() {
          const iframe = document.getElementById('graphFrame');
          if (iframe) iframe.src = '/api/graph?ts=' + Date.now(); // cache bust
        },

        toast(msg, type='info') {
          const id = crypto.randomUUID ? crypto.randomUUID() : String(Date.now()+Math.random());
          this.toasts.push({id, msg, type});
          setTimeout(()=> this.toasts = this.toasts.filter(t=>t.id!==id), 3500);
          this.$nextTick(()=>this.renderIcons());
        },
      }
    }
