import tkinter as tk
from tkinter import ttk, scrolledtext
import requests
import threading
import random
import time
import uuid
import json
import os
import base64
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from fp.fp import FreeProxy
from fp.errors import FreeProxyException
import aiohttp
import asyncio
from bs4 import BeautifulSoup

class ModernTheme:
    # Colores principales
    BG = "#18181B"
    BG_DARK = "#121214"
    BG_LIGHT = "#27272A"
    ACCENT = "#6EE7B7"
    ACCENT_DARK = "#059669"
    FG = "#E4E4E7"
    FG_ALT = "#A1A1AA"
    SUCCESS = "#34D399"
    ERROR = "#F87171"
    WARNING = "#FBBF24"

    # Fuentes más pequeñas
    FONT = ("Inter", 9)
    FONT_BOLD = ("Inter", 9, "bold")
    TITLE_FONT = ("Inter", 14, "bold")

    # Bordes y espaciado reducidos
    BORDER_COLOR = "#27272A"
    BORDER_WIDTH = 1
    CORNER_RADIUS = 6
    PADDING = 6
    SMALL_PADDING = 3


class ProxyManager:
    def __init__(self):
        self.proxies = set()
        self.working_proxies = set()
        self.check_url = "https://ngl.link"
        self.timeout = 5
        self.max_concurrent_checks = 50
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.5',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
        }

    def fetch_from_free_proxy_list(self):
        try:
            response = requests.get(
                "https://free-proxy-list.net/",
                headers=self.headers,
                timeout=10
            )
            response.raise_for_status()  # Verificar si hay errores HTTP
            
            soup = BeautifulSoup(response.text, 'html.parser')
            table = soup.find('table')
            if not table:
                print("No se encontró la tabla de proxies en free-proxy-list")
                return
                
            rows = table.find_all('tr')[1:]  # Saltar el encabezado
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 7:
                    ip = cols[0].text.strip()
                    port = cols[1].text.strip()
                    https = cols[6].text.strip()
                    if https == 'yes' and self.is_valid_ip(ip):
                        self.proxies.add(f"{ip}:{port}")
        except Exception as e:
            print(f"Error fetching from free-proxy-list: {e}")

    def is_valid_ip(self, ip):
        try:
            parts = ip.split('.')
            return len(parts) == 4 and all(0 <= int(part) <= 255 for part in parts)
        except:
            return False

    def fetch_from_geonode(self):
        try:
            response = requests.get(
                "https://proxylist.geonode.com/api/proxy-list?limit=500&page=1&sort_by=lastChecked&sort_type=desc&protocols=https",
                headers=self.headers,
                timeout=10
            )
            data = response.json()
            for proxy in data.get('data', []):
                ip = proxy.get('ip')
                port = proxy.get('port')
                if ip and port and self.is_valid_ip(ip):
                    self.proxies.add(f"{ip}:{port}")
        except Exception as e:
            print(f"Error fetching from geonode: {e}")

    def fetch_from_proxyscrape(self):
        try:
            urls = [
                "https://api.proxyscrape.com/v2/?request=getproxies&protocol=http&timeout=5000&country=all&ssl=yes&anonymity=all&simplified=true",
                "https://raw.githubusercontent.com/TheSpeedX/PROXY-List/master/http.txt",
                "https://raw.githubusercontent.com/ShiftyTR/Proxy-List/master/https.txt",
                "https://raw.githubusercontent.com/mertguvencli/http-proxy-list/main/proxy-list/data.txt"
            ]
            
            for url in urls:
                try:
                    response = requests.get(url, headers=self.headers, timeout=10)
                    if response.status_code == 200:
                        proxies = response.text.strip().split('\\n')
                        for proxy in proxies:
                            proxy = proxy.strip()
                            if ':' in proxy:
                                ip = proxy.split(':')[0]
                                if self.is_valid_ip(ip):
                                    self.proxies.add(proxy)
                except Exception as e:
                    print(f"Error fetching from {url}: {e}")
                    continue
        except Exception as e:
            print(f"Error in fetch_from_proxyscrape: {e}")

    async def check_proxy(self, proxy):
        try:
            timeout = aiohttp.ClientTimeout(total=self.timeout)
            async with aiohttp.ClientSession(timeout=timeout) as session:
                proxy_url = f"http://{proxy}"
                async with session.get(
                    self.check_url,
                    proxy=proxy_url,
                    headers=self.headers,
                    ssl=False
                ) as response:
                    if response.status == 200:
                        self.working_proxies.add(proxy)
                        print(f"Proxy working: {proxy}")
                        return True
        except:
            pass
        return False

    async def verify_proxies(self):
        tasks = []
        for proxy in self.proxies:
            task = asyncio.ensure_future(self.check_proxy(proxy))
            tasks.append(task)
            if len(tasks) >= self.max_concurrent_checks:
                await asyncio.gather(*tasks)
                tasks = []
        if tasks:
            await asyncio.gather(*tasks)

    def get_working_proxies(self):
        print("Buscando proxies...")
        self.proxies.clear()
        self.working_proxies.clear()
        
        # Obtener proxies de múltiples fuentes
        self.fetch_from_free_proxy_list()
        print(f"Free-proxy-list: {len(self.proxies)} encontrados")
        
        self.fetch_from_geonode()
        print(f"Geonode: {len(self.proxies)} encontrados")
        
        self.fetch_from_proxyscrape()
        print(f"Proxyscrape y otros: {len(self.proxies)} encontrados")

        if not self.proxies:
            print("No se encontraron proxies en ninguna fuente")
            return []

        print(f"Verificando {len(self.proxies)} proxies...")
        # Verificar proxies de forma asíncrona
        asyncio.run(self.verify_proxies())
        return list(self.working_proxies)


class ModernEntry(ttk.Entry):
    def __init__(self, *args, **kwargs):
        style = ttk.Style()
        style.configure(
            "Modern.TEntry",
            fieldbackground=ModernTheme.BG_LIGHT,
            foreground=ModernTheme.FG,
            borderwidth=ModernTheme.BORDER_WIDTH,
            relief="flat",
            padding=ModernTheme.SMALL_PADDING  # Padding más pequeño
        )
        style.map("Modern.TEntry",
            fieldbackground=[("focus", ModernTheme.BG)],
            bordercolor=[("focus", ModernTheme.ACCENT)]
        )
        kwargs["style"] = "Modern.TEntry"
        super().__init__(*args, **kwargs)


class ModernButton(ttk.Button):
    def __init__(self, *args, **kwargs):
        style = ttk.Style()
        style.configure(
            "Modern.TButton",
            background=ModernTheme.ACCENT,
            foreground=ModernTheme.BG_DARK,
            borderwidth=0,
            font=ModernTheme.FONT_BOLD,
            padding=[ModernTheme.PADDING, ModernTheme.SMALL_PADDING],  # Padding más compacto
            relief="flat"
        )
        style.map("Modern.TButton",
            background=[("active", ModernTheme.ACCENT_DARK)],
            foreground=[("active", ModernTheme.BG_DARK)]
        )
        kwargs["style"] = "Modern.TButton"
        super().__init__(*args, **kwargs)


class ModernScrolledText(scrolledtext.ScrolledText):
    def __init__(self, *args, **kwargs):
        kwargs.update({
            "bg": ModernTheme.BG_DARK,
            "fg": ModernTheme.FG,
            "insertbackground": ModernTheme.ACCENT,
            "selectbackground": ModernTheme.ACCENT,
            "selectforeground": ModernTheme.BG_DARK,
            "relief": "flat",
            "borderwidth": ModernTheme.BORDER_WIDTH,
            "font": ModernTheme.FONT,
            "padx": ModernTheme.SMALL_PADDING,
            "pady": ModernTheme.SMALL_PADDING,
            "wrap": tk.WORD
        })
        super().__init__(*args, **kwargs)
        
        # Personalizar la barra de desplazamiento
        self.vbar.configure(
            background=ModernTheme.BG_LIGHT,
            troughcolor=ModernTheme.BG_DARK,
            width=12,
            relief="flat"
        )


class StatsPanel(ttk.Frame):
    def __init__(self, parent):
        style = ttk.Style()
        style.configure(
            "Stats.TFrame",
            background=ModernTheme.BG_DARK,
            borderwidth=ModernTheme.BORDER_WIDTH,
            relief="solid",
            padding=ModernTheme.SMALL_PADDING
        )

        super().__init__(parent, style="Stats.TFrame")

        self.stats = {
            "messages_sent": 0,
            "messages_failed": 0,
            "start_time": None,
            "proxies_active": 0,
        }

        self.setup_ui()

    def setup_ui(self):
        main_frame = ttk.Frame(self, style="Stats.TFrame")
        main_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        style = ttk.Style()
        style.configure(
            "StatValue.TLabel",
            background=ModernTheme.BG_DARK,
            foreground=ModernTheme.ACCENT,
            font=ModernTheme.FONT_BOLD,
        )

        style.configure(
            "StatLabel.TLabel",
            background=ModernTheme.BG_DARK,
            foreground=ModernTheme.FG_ALT,
            font=ModernTheme.FONT,
        )

        self.create_stat_grid(main_frame)
        self.update_stats()

    def create_stat_grid(self, parent):
        stats_frame = ttk.Frame(parent, style="Custom.TFrame")
        stats_frame.grid(row=0, column=0, sticky="nsew", padx=ModernTheme.SMALL_PADDING)
        stats_frame.grid_columnconfigure(1, weight=1)

        # Labels más compactos
        labels = [
            ("Mensajes enviados:", "messages_sent"),
            ("Mensajes fallidos:", "messages_failed"),
            ("Tiempo transcurrido:", "elapsed_time"),
            ("Proxies activos:", "proxies_active")
        ]

        for i, (text, key) in enumerate(labels):
            label = ttk.Label(stats_frame, text=text, style="Custom.TLabel")
            label.grid(row=i, column=0, sticky="w", pady=(0, ModernTheme.SMALL_PADDING))
            
            value_label = ttk.Label(stats_frame, text="0", style="Custom.TLabel")
            value_label.grid(row=i, column=1, sticky="e", pady=(0, ModernTheme.SMALL_PADDING))
            setattr(self, f"{key}_label", value_label)

    def create_stat_section(self, parent):
        frame = ttk.Frame(parent, style="Stats.TFrame")
        frame.columnconfigure(0, weight=1)
        return frame

    def start_timer(self):
        self.stats["start_time"] = time.time()
        self.update_stats()

    def stop_timer(self):
        self.stats["start_time"] = None
        self.elapsed_time_label.config(text="00:00:00")

    def update_stats(self):
        # Actualizar mensajes enviados y fallidos
        total = self.stats["messages_sent"] + self.stats["messages_failed"]
        success_rate = (self.stats["messages_sent"] / total * 100) if total > 0 else 0
        
        self.messages_sent_label.config(text=str(self.stats["messages_sent"]))
        self.messages_failed_label.config(text=str(self.stats["messages_failed"]))
        
        # Actualizar tiempo transcurrido
        if self.stats["start_time"]:
            elapsed = time.time() - self.stats["start_time"]
            hours = int(elapsed // 3600)
            minutes = int((elapsed % 3600) // 60)
            seconds = int(elapsed % 60)
            self.elapsed_time_label.config(text=f"{hours:02d}:{minutes:02d}:{seconds:02d}")
        else:
            self.elapsed_time_label.config(text="00:00:00")
        
        # Actualizar proxies activos
        self.proxies_active_label.config(text=str(self.stats["proxies_active"]))
        
        # Programar la próxima actualización
        if self.stats["start_time"]:
            self.after(1000, self.update_stats)

    def update_messages(self, sent, failed):
        self.stats["messages_sent"] = sent
        self.stats["messages_failed"] = failed

    def update_proxies(self, active):
        self.stats["proxies_active"] = active
        self.proxies_active_label.config(text=str(active))


class NGLSpammer(tk.Tk):
    def __init__(self):
        super().__init__()

        self.title("NGL Spammer")
        self.geometry("500x600")
        self.configure(bg=ModernTheme.BG)
        self.minsize(450, 550)

        self.running = False
        self.messages_from_file = []
        self.proxy_manager = ProxyManager()
        self.proxies = []

        # Firma oculta
        self._signature = "".join([chr(ord(c) ^ 42) for c in base64.b64encode("3ncriptado".encode()).decode()])
        
        self.setup_styles()
        self.create_interface()

        # Configurar el peso de las columnas para un mejor ajuste
        self.grid_columnconfigure(0, weight=1)
        
        self.update_proxies()
        self.load_messages()
        
        # Mostrar firma de forma sutil
        self.after(3000, self._show_signature)

    def setup_styles(self):
        style = ttk.Style()

        style.configure("Custom.TFrame", background=ModernTheme.BG)

        style.configure(
            "Custom.TLabel",
            background=ModernTheme.BG,
            foreground=ModernTheme.FG,
            font=ModernTheme.FONT,
        )

        style.configure(
            "Title.TLabel",
            background=ModernTheme.BG,
            foreground=ModernTheme.ACCENT,
            font=ModernTheme.TITLE_FONT,
        )

        style.configure("Custom.TButton", font=ModernTheme.FONT_BOLD, padding=10)

        style.configure(
            "Custom.Horizontal.TScale",
            background=ModernTheme.BG,
            troughcolor=ModernTheme.BG_LIGHT,
            slidercolor=ModernTheme.ACCENT,
        )

    def create_interface(self):
        main_frame = ttk.Frame(self, style="Custom.TFrame", padding=ModernTheme.PADDING)
        main_frame.grid(row=0, column=0, sticky="nsew", padx=ModernTheme.PADDING, pady=ModernTheme.PADDING)
        
        # Configurar el peso de las columnas en main_frame
        main_frame.grid_columnconfigure(0, weight=1)

        title_label = ttk.Label(
            main_frame, text="NGL Spammer", style="Title.TLabel"
        )
        title_label.grid(row=0, column=0, columnspan=2, pady=(0, 30))

        self.stats_panel = StatsPanel(main_frame)
        self.stats_panel.grid(row=1, column=0, sticky="ew", pady=(0, ModernTheme.PADDING))

        self.create_custom_message_section(main_frame)
        
        self.create_config_section(main_frame)
        self.create_operation_section(main_frame)

    def create_custom_message_section(self, parent):
        # Frame para mensaje personalizado
        custom_frame = ttk.Frame(parent, style="Custom.TFrame")
        custom_frame.grid(row=2, column=0, sticky="ew", pady=(0, ModernTheme.PADDING))
        custom_frame.grid_columnconfigure(1, weight=1)  # La columna del mensaje se expandirá

        # Título de la sección
        ttk.Label(custom_frame, text="MENSAJE PERSONALIZADO", style="Custom.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 5)
        )

        # Usuario específico
        ttk.Label(custom_frame, text="Usuario:", style="Custom.TLabel").grid(
            row=1, column=0, sticky="w", padx=(0, 5)
        )
        self.custom_username = ModernEntry(custom_frame)
        self.custom_username.grid(row=1, column=1, sticky="ew")

        # Mensaje personalizado
        ttk.Label(custom_frame, text="Mensaje:", style="Custom.TLabel").grid(
            row=2, column=0, sticky="w", padx=(0, 5), pady=(5, 0)
        )
        self.custom_message = ModernEntry(custom_frame)
        self.custom_message.grid(row=2, column=1, sticky="ew", pady=(5, 0))

        # Botón de envío
        self.send_custom_button = ModernButton(
            custom_frame, 
            text="ENVIAR MENSAJE", 
            command=self.send_custom_message
        )
        self.send_custom_button.grid(row=3, column=1, sticky="e", pady=(5, 0))

    def create_config_section(self, parent):
        config_frame = ttk.Frame(parent, style="Custom.TFrame")
        config_frame.grid(row=3, column=0, sticky="ew", pady=(0, ModernTheme.PADDING))
        config_frame.grid_columnconfigure(0, weight=1)

        ttk.Label(config_frame, text="TARGET USERNAME", style="Custom.TLabel").grid(
            row=0, column=0, sticky="w", pady=(0, 5)
        )

        self.username = ModernEntry(config_frame)
        self.username.grid(row=1, column=0, sticky="ew", pady=(0, ModernTheme.PADDING))

        # Delay control
        delay_frame = ttk.Frame(config_frame, style="Custom.TFrame")
        delay_frame.grid(row=2, column=0, sticky="ew")

        ttk.Label(delay_frame, text="DELAY (SECONDS)", style="Custom.TLabel").pack(
            side="left", padx=(0, 10)
        )

        self.delay = ttk.Scale(
            delay_frame,
            from_=1,
            to=10,
            orient="horizontal",
            length=150,
            style="Custom.Horizontal.TScale",
        )
        self.delay.pack(side="left", padx=5, fill="x", expand=True)
        self.delay.set(1)

        self.delay_value = ttk.Label(delay_frame, text="1s", style="Custom.TLabel")
        self.delay_value.pack(side="left", padx=5)

        self.delay.configure(command=self.update_delay_label)

    def create_operation_section(self, parent):
        ttk.Label(parent, text="CURRENT MESSAGE", style="Custom.TLabel").grid(
            row=4, column=0, sticky="w", pady=(0, 5)
        )

        self.message = ModernScrolledText(parent, height=3)
        self.message.grid(row=5, column=0, sticky="ew", pady=(0, ModernTheme.PADDING))

        ttk.Label(parent, text="OPERATION LOGS", style="Custom.TLabel").grid(
            row=6, column=0, sticky="w", pady=(0, 5)
        )

        self.logs = ModernScrolledText(parent, height=12)
        self.logs.grid(row=7, column=0, sticky="ew", pady=(0, ModernTheme.PADDING))

        button_frame = ttk.Frame(parent, style="Custom.TFrame")
        button_frame.grid(row=8, column=0, sticky="ew", pady=(0, ModernTheme.PADDING))
        button_frame.grid_columnconfigure(0, weight=1)
        button_frame.grid_columnconfigure(1, weight=1)

        ModernButton(
            button_frame, text="UPDATE PROXIES", command=self.update_proxies
        ).grid(row=0, column=0, padx=5)

        ModernButton(
            button_frame, text="RELOAD MESSAGES", command=self.load_messages
        ).grid(row=0, column=1, padx=5)

        control_frame = ttk.Frame(parent, style="Custom.TFrame")
        control_frame.grid(row=9, column=0, sticky="ew")
        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)

        self.start_button = ModernButton(
            control_frame, text="START ATTACK", command=self.start_sending
        )
        self.start_button.grid(row=0, column=0, padx=5)

        self.stop_button = ModernButton(
            control_frame, text="STOP ATTACK", command=self.stop_sending
        )
        self.stop_button.grid(row=0, column=1, padx=5)
        self.stop_button["state"] = "disabled"

    def update_delay_label(self, value=None):
        self.delay_value.config(text=f"{int(float(self.delay.get()))}s")

    def log_message(self, message, level="info"):
        timestamp = time.strftime("%H:%M:%S")
        prefix = {
            "error": "[-] ",
            "success": "[+] ",
            "warning": "[!] ",
            "info": "[*] ",
        }.get(level, "[*] ")

        color = {
            "error": ModernTheme.ERROR,
            "success": ModernTheme.SUCCESS,
            "warning": ModernTheme.WARNING,
            "info": ModernTheme.FG,
        }.get(level, ModernTheme.FG)

        start_pos = self.logs.index("end-1c linestart")
        self.logs.insert(tk.END, f"{prefix}[{timestamp}] {message}\n")
        end_pos = self.logs.index("end-1c")

        try:
            self.logs.tag_add(f"color_{level}", start_pos, end_pos)
            self.logs.tag_config(f"color_{level}", foreground=color)
        except Exception:
            pass

        self.logs.see(tk.END)
        self.update_idletasks()

    def verify_proxy(self, proxy):
        try:
            self.log_message(f"Verificando proxy {proxy}...", "info")
            response = requests.get(
                "https://httpbin.org/ip",
                proxies={"http": proxy, "https": proxy},
                timeout=5
            )
            success = response.status_code == 200
            if success:
                self.log_message(f"Proxy {proxy} verificado correctamente", "success")
            else:
                self.log_message(f"Proxy {proxy} falló con status {response.status_code}", "error")
            return success
        except requests.exceptions.RequestException as e:
            self.log_message(f"Error al verificar proxy {proxy}: {str(e)}", "error")
            return False
        except Exception as e:
            self.log_message(f"Error inesperado al verificar {proxy}: {str(e)}", "error")
            return False

    def update_proxies(self):
        self.proxies = self.proxy_manager.get_working_proxies()
        self.log_message(f"Se encontraron {len(self.proxies)} proxies funcionando", "success")
        # Actualizar el contador de proxies en el panel de estadísticas
        self.stats_panel.update_proxies(len(self.proxies))

    def send_message(self, username, message):
        proxy = random.choice(self.proxies) if self.proxies else None
        if not proxy:
            self.log_message("No proxies available", "error")
            return False

        device_id = str(uuid.uuid4())
        url = "https://ngl.link/api/submit"
        
        # Lista de colores disponibles en NGL
        colors = [
            "red", "blue", "green", "purple", "orange", 
            "pink", "cyan", "yellow", "lime", "violet",
            "coral", "teal", "magenta", "brown", "indigo"
        ]
        
        # Seleccionar un color aleatorio
        random_color = random.choice(colors)
        
        # Propiedades adicionales para personalizar el mensaje
        additional_props = {
            "color": random_color,
            "deviceId": device_id,
            "gameSlug": "",
            "imageUrl": "",
            "shareImage": "false",
            "userId": "anonymous"
        }
        
        headers = {
            "accept": "*/*",
            "accept-language": "en-US,en;q=0.7",
            "content-type": "application/x-www-form-urlencoded; charset=UTF-8",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-origin",
            "sec-gpc": "1",
            "x-requested-with": "XMLHttpRequest",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

        data = {
            "username": username,
            "question": message,
            **additional_props
        }

        try:
            response = requests.post(
                url,
                headers=headers,
                data=data,
                proxies={"http": proxy, "https": proxy},
                timeout=10,
            )
            if response.ok:
                self.log_message(f"Message sent via {proxy}", "success")
                return True
            else:
                self.log_message(f"Error with proxy {proxy}: HTTP {response.status_code}", "error")
                return False
        except requests.RequestException as e:
            self.log_message(f"Error with proxy {proxy}: {str(e)}", "error")
            return False

    def sending_loop(self):
        counter = 0
        failed = 0
        while self.running:
            if not self.messages_from_file:
                self.log_message("No messages available", "error")
                break

            username = self.username.get()
            message = random.choice(self.messages_from_file)

            self.message.delete(1.0, tk.END)
            self.message.insert(1.0, message)

            if self.send_message(username, message):
                counter += 1
                self.stats_panel.update_messages(counter, failed)
            else:
                failed += 1
                self.stats_panel.update_messages(counter, failed)
                if len(self.proxies) < 5:
                    self.update_proxies()
                    
            # Actualizar el contador de proxies
            self.stats_panel.update_proxies(len(self.proxies))

            delay = int(self.delay.get())
            time.sleep(delay)

    def start_sending(self):
        if not self.username.get():
            self.log_message("Error: Username required", "error")
            return

        if not self.messages_from_file:
            self.log_message("Error: No messages loaded", "error")
            return

        if not self.proxies:
            self.log_message("Error: No proxies available", "error")
            return

        self.running = True
        self.start_button["state"] = "disabled"
        self.stop_button["state"] = "normal"
        self.stats_panel.start_timer()

        thread = threading.Thread(target=self.sending_loop)
        thread.daemon = True
        thread.start()

    def stop_sending(self):
        self.running = False
        self.start_button["state"] = "normal"
        self.stop_button["state"] = "disabled"
        self.stats_panel.stop_timer()

    def send_custom_message(self):
        username = self.custom_username.get().strip()
        message = self.custom_message.get().strip()
        
        if not username or not message:
            self.log_message("Por favor, ingresa tanto el usuario como el mensaje.", "warning")
            return
            
        # Obtener un proxy
        proxy = random.choice(self.proxies) if self.proxies else None
        if not proxy:
            self.log_message("No hay proxies disponibles para enviar el mensaje.", "error")
            return

        try:
            success = self.send_message(username, message)
            if success:
                self.log_message(f"Mensaje personalizado enviado a {username}", "success")
                # Limpiar los campos
                self.custom_username.delete(0, tk.END)
                self.custom_message.delete(0, tk.END)
            else:
                self.log_message(f"Error al enviar mensaje personalizado a {username}", "error")
        except Exception as e:
            self.log_message(f"Error: {str(e)}", "error")

    def _show_signature(self):
        decoded = "".join([chr(ord(c) ^ 42) for c in self._signature])
        signature = base64.b64decode(decoded).decode()
        subtle_label = ttk.Label(
            self,
            text=signature,
            foreground=ModernTheme.BG_LIGHT,
            background=ModernTheme.BG,
            font=("Inter", 7)
        )
        subtle_label.place(relx=0.98, rely=0.99, anchor="se")

    def load_messages(self):
        try:
            with open("mensajes.txt", "r", encoding="utf-8") as file:
                self.messages_from_file = [
                    line.strip() for line in file if line.strip()
                ]
            self.log_message(
                f"Loaded {len(self.messages_from_file)} messages", "success"
            )
        except FileNotFoundError:
            self.log_message("Error: mensajes.txt not found", "error")
            self.messages_from_file = []
        except Exception as e:
            self.log_message(f"Error loading messages: {str(e)}", "error")
            self.messages_from_file = []


if __name__ == "__main__":
    app = NGLSpammer()
    app.mainloop()
