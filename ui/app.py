# ui/app.py
import re
import time
import threading
import queue
import tkinter as tk
from tkinter import ttk

from services.monitor_service import MonitorService
from clients.zimbra_client import ZimbraClient
from clients.notion_client import NotionTicketClient


# =========================================================
# PALETA PREMIUM ARCA
# =========================================================
BG_APP = "#111315"
BG_TOPBAR = "#15171B"
BG_SURFACE = "#171A1F"
BG_PANEL = "#1B1F25"
BG_PANEL_ALT = "#20252D"
BG_EVENT_ALT = "#161A20"
BG_LOG_CANVAS = "#14181D"

BORDER = "#2A303A"
BORDER_SOFT = "#232933"

TEXT_PRIMARY = "#F5F7FA"
TEXT_SECONDARY = "#B5BDC9"
TEXT_MUTED = "#7F8794"
TEXT_FAINT = "#626975"

ACCENT_BLUE = "#5B6CFF"
ACCENT_CYAN = "#25C7D9"
ACCENT_GREEN = "#1ED47E"
ACCENT_AMBER = "#F5B940"
ACCENT_RED = "#F36A6A"
ACCENT_GRAY = "#6B7280"


# =========================================================
# HELPERS UI
# =========================================================
def create_card(parent, bg_outer=BORDER, bg_inner=BG_SURFACE, padding=1):
    # Patron visual reutilizable: contenedor externo (borde) + interno (contenido).
    outer = tk.Frame(parent, bg=bg_outer, bd=0, highlightthickness=0)
    inner = tk.Frame(outer, bg=bg_inner, bd=0, highlightthickness=0)
    inner.pack(fill="both", expand=True, padx=padding, pady=padding)
    return outer, inner


def create_dot(parent, color, size=10):
    # Dibuja un punto de estado en un Canvas pequeno.
    dot = tk.Canvas(
        parent,
        width=size,
        height=size,
        bg=parent.cget("bg"),
        highlightthickness=0,
        bd=0,
    )
    dot.create_oval(2, 2, size - 2, size - 2, fill=color, outline=color)
    return dot


def human_time() -> str:
    # Hora local HH:MM:SS para timestamp visual en stream.
    return time.strftime("%H:%M:%S")


def shorten(text: str, limit: int = 68) -> str:
    # Trunca textos largos para no romper layout de labels compactos.
    return text if len(text) <= limit else text[: limit - 1] + "…"


# =========================================================
# EVENT STREAM PREMIUM
# =========================================================
class EventStream(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_SURFACE)

        # Canvas + frame interno para lograr scroll vertical fluido en eventos.
        self.canvas = tk.Canvas(
            self,
            bg=BG_LOG_CANVAS,
            bd=0,
            highlightthickness=0,
            relief="flat",
        )
        self.scrollbar = ttk.Scrollbar(self, orient="vertical", command=self.canvas.yview)
        self.content = tk.Frame(self.canvas, bg=BG_LOG_CANVAS)

        self.content.bind(
            "<Configure>",
            # Ajusta region de scroll cuando cambia el tamano del contenido.
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all"))
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0), window=self.content, anchor="nw"
        )

        self.canvas.bind(
            "<Configure>",
            # Mantiene el frame interno al ancho del canvas para wrap correcto.
            lambda e: self.canvas.itemconfigure(self.canvas_window, width=e.width)
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        # Lista de widgets fila para poder recortar historial viejo.
        self.rows: list[tk.Frame] = []
        self.max_rows = 120

        self.canvas.bind_all("<MouseWheel>", self._on_mousewheel)

    def _on_mousewheel(self, event):
        try:
            # Scroll en unidades normalizadas para mouse wheel de Windows.
            self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
        except Exception:
            pass

    def add_event(self, level: str, category: str, message: str, meta: str = ""):
        # Paletas por nivel para distinguir visualmente errores/ok/info.
        colors = {
            "SYSTEM": {"accent": ACCENT_BLUE, "border": "#31407C", "text": TEXT_PRIMARY},
            "INFO": {"accent": ACCENT_CYAN, "border": "#1F5E66", "text": TEXT_PRIMARY},
            "SUCCESS": {"accent": ACCENT_GREEN, "border": "#1C6A4A", "text": TEXT_PRIMARY},
            "WARN": {"accent": ACCENT_AMBER, "border": "#7B6223", "text": TEXT_PRIMARY},
            "ERROR": {"accent": ACCENT_RED, "border": "#7A3535", "text": TEXT_PRIMARY},
            "DEFAULT": {"accent": ACCENT_GRAY, "border": BORDER_SOFT, "text": TEXT_PRIMARY},
        }

        palette = colors.get(level, colors["DEFAULT"])

        # Crea una fila nueva en el stream.
        row = tk.Frame(self.content, bg=BG_LOG_CANVAS)
        row.pack(fill="x", padx=12, pady=(0, 10))

        left_col = tk.Frame(row, bg=BG_LOG_CANVAS, width=26)
        left_col.pack(side="left", fill="y")
        left_col.pack_propagate(False)

        if self.rows:
            tk.Frame(left_col, bg=BORDER_SOFT, width=2, height=8).pack(pady=(0, 2))

        dot = tk.Canvas(
            left_col,
            width=14,
            height=14,
            bg=BG_LOG_CANVAS,
            highlightthickness=0,
            bd=0,
        )
        dot.pack()
        dot.create_rectangle(5, 5, 9, 9, fill=palette["accent"], outline=palette["accent"])

        tk.Frame(left_col, bg=BORDER_SOFT, width=2, height=58).pack(pady=(2, 0), fill="y")

        body = tk.Frame(
            row,
            bg=BG_EVENT_ALT,
            highlightthickness=1,
            highlightbackground=palette["border"],
            bd=0
        )
        body.pack(side="left", fill="x", expand=True)

        tk.Frame(body, bg=palette["accent"], width=3).pack(side="left", fill="y")

        inner = tk.Frame(body, bg=BG_EVENT_ALT)
        inner.pack(side="left", fill="both", expand=True)

        header = tk.Frame(inner, bg=BG_EVENT_ALT)
        header.pack(fill="x", padx=12, pady=(10, 6))

        tk.Label(
            header,
            text=f"[ {human_time()} ]",
            bg=BG_EVENT_ALT,
            fg=TEXT_MUTED,
            font=("Consolas", 8),
        ).pack(side="left")

        tk.Label(
            header,
            text=category.upper(),
            bg=BG_EVENT_ALT,
            fg=TEXT_FAINT,
            font=("Segoe UI", 8),
        ).pack(side="left", padx=(10, 0))

        if meta:
            tk.Label(
                header,
                text=meta,
                bg=BG_EVENT_ALT,
                fg=TEXT_FAINT,
                font=("Consolas", 8),
            ).pack(side="right")

        content = tk.Frame(inner, bg=BG_EVENT_ALT)
        content.pack(fill="x", padx=12, pady=(0, 10))

        tk.Label(
            content,
            text=f"{level}:",
            bg=BG_EVENT_ALT,
            fg=palette["accent"],
            font=("Consolas", 9, "bold"),
        ).pack(side="left", anchor="n")

        tk.Label(
            content,
            text=message,
            bg=BG_EVENT_ALT,
            fg=palette["text"],
            font=("Consolas", 9),
            justify="left",
            anchor="w",
            wraplength=760,
        ).pack(side="left", fill="x", expand=True, padx=(8, 0))

        self.rows.append(row)

        # Si supera el maximo, elimina la mas antigua (FIFO visual).
        if len(self.rows) > self.max_rows:
            old = self.rows.pop(0)
            old.destroy()

        # Auto-scroll al final para mostrar ultimo evento.
        self.update_idletasks()
        self.canvas.yview_moveto(1.0)


# =========================================================
# APP
# =========================================================
def create_app() -> tk.Tk:
    # Ventana principal del dashboard ARCA.
    root = tk.Tk()
    root.title("ARCA · Automatic Relay for Case Automation")
    root.geometry("1280x760")
    root.minsize(1160, 700)
    root.configure(bg=BG_APP)

    # Configuracion de estilos ttk centralizados.
    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TFrame", background=BG_APP)
    style.configure(
        "HeaderTitle.TLabel",
        background=BG_APP,
        foreground=TEXT_PRIMARY,
        font=("Segoe UI", 24, "bold"),
    )
    style.configure(
        "HeaderSub.TLabel",
        background=BG_APP,
        foreground=TEXT_SECONDARY,
        font=("Segoe UI", 10),
    )
    style.configure(
        "HeaderChip.TLabel",
        background=BG_APP,
        foreground=ACCENT_CYAN,
        font=("Consolas", 10, "bold"),
    )
    style.configure(
        "MetricTitle.TLabel",
        background=BG_SURFACE,
        foreground=TEXT_MUTED,
        font=("Segoe UI", 9),
    )
    style.configure(
        "MetricValue.TLabel",
        background=BG_SURFACE,
        foreground=TEXT_PRIMARY,
        font=("Segoe UI", 18, "bold"),
    )
    style.configure(
        "MetricValueMono.TLabel",
        background=BG_SURFACE,
        foreground=TEXT_PRIMARY,
        font=("Consolas", 16, "bold"),
    )
    style.configure(
        "Footer.TLabel",
        background=BG_APP,
        foreground=TEXT_FAINT,
        font=("Segoe UI", 9),
    )
    style.configure(
        "Signature.TLabel",
        background=BG_APP,
        foreground=TEXT_MUTED,
        font=("Segoe UI", 8, "italic"),
    )

    # Contenedor principal de toda la interfaz.
    shell = tk.Frame(root, bg=BG_APP)
    shell.pack(fill="both", expand=True)

    # TOPBAR: barra superior con estado rapido de sistema.
    topbar = tk.Frame(shell, bg=BG_TOPBAR, height=30)
    topbar.pack(fill="x", side="top")
    topbar.pack_propagate(False)

    topbar_left = tk.Frame(topbar, bg=BG_TOPBAR)
    topbar_left.pack(side="left", padx=12)

    create_dot(topbar_left, ACCENT_BLUE, 9).pack(side="left", pady=9)

    tk.Label(
        topbar_left,
        text="  ARCA",
        bg=BG_TOPBAR,
        fg=TEXT_PRIMARY,
        font=("Segoe UI", 10, "bold"),
    ).pack(side="left", pady=4)

    tk.Label(
        topbar_left,
        text="Automatic Relay for Case Automation",
        bg=BG_TOPBAR,
        fg=TEXT_MUTED,
        font=("Segoe UI", 8),
    ).pack(side="left", padx=(8, 0), pady=4)

    topbar_right = tk.Frame(topbar, bg=BG_TOPBAR)
    topbar_right.pack(side="right", padx=14)

    tk.Label(
        topbar_right,
        text="SYSTEM LIVE",
        bg=BG_TOPBAR,
        fg=TEXT_MUTED,
        font=("Segoe UI", 8),
    ).pack(side="left", padx=(0, 14), pady=4)

    session_uptime_label = tk.Label(
        topbar_right,
        text="00:00:00",
        bg=BG_TOPBAR,
        fg=TEXT_PRIMARY,
        font=("Consolas", 8, "bold"),
    )
    session_uptime_label.pack(side="left", padx=(0, 14), pady=4)

    tk.Label(
        topbar_right,
        text="API 24ms",
        bg=BG_TOPBAR,
        fg=ACCENT_GREEN,
        font=("Segoe UI", 8, "bold"),
    ).pack(side="left", pady=4)

    main = tk.Frame(shell, bg=BG_APP, padx=18, pady=18)
    main.pack(fill="both", expand=True)

    # HEADER: branding y descripcion del sistema.
    header = tk.Frame(main, bg=BG_APP)
    header.pack(fill="x", pady=(0, 18))

    header_left = tk.Frame(header, bg=BG_APP)
    header_left.pack(side="left", fill="x", expand=True)

    ttk.Label(header_left, text="ARCA", style="HeaderTitle.TLabel").pack(
        anchor="w", side="left"
    )
    ttk.Label(
        header_left,
        text="Automatic Relay for Case Automation",
        style="HeaderSub.TLabel",
    ).pack(side="left", padx=(12, 0), pady=(8, 0))

    chip_row = tk.Frame(main, bg=BG_APP)
    chip_row.pack(fill="x", pady=(0, 14))

    ttk.Label(
        chip_row,
        text="ZIMBRA  →  NOTION   ·   EVENT RELAY   ·   TICKET AUTOMATION",
        style="HeaderChip.TLabel",
    ).pack(anchor="w")

    # TOP STATUS ROW: metricas de monitor y estado de conexiones.
    top_row = tk.Frame(main, bg=BG_APP)
    top_row.pack(fill="x", pady=(0, 16))

    # Tarjeta 1: Monitor (estado, total procesado, ultimo evento, intervalo).
    monitor_outer, monitor_inner = create_card(top_row, BORDER, BG_SURFACE, padding=1)
    monitor_outer.pack(side="left", fill="x", expand=True)

    top_bar = tk.Frame(monitor_inner, bg=BG_SURFACE)
    top_bar.pack(fill="x", padx=16, pady=(14, 8))

    tk.Label(
        top_bar,
        text="MONITOR",
        bg=BG_SURFACE,
        fg=TEXT_MUTED,
        font=("Segoe UI", 9),
    ).pack(side="left")

    state_chip = tk.Frame(
        top_bar,
        bg=BG_PANEL_ALT,
        highlightthickness=1,
        highlightbackground=BORDER_SOFT
    )
    state_chip.pack(side="right")

    state_chip_inner = tk.Frame(state_chip, bg=BG_PANEL_ALT, padx=10, pady=5)
    state_chip_inner.pack()

    state_dot_canvas = tk.Canvas(
        state_chip_inner,
        width=10,
        height=10,
        bg=BG_PANEL_ALT,
        highlightthickness=0,
        bd=0,
    )
    state_dot_canvas.pack(side="left", padx=(0, 6))
    state_dot = state_dot_canvas.create_oval(
        2, 2, 8, 8, fill=ACCENT_RED, outline=ACCENT_RED
    )

    monitor_state = tk.Label(
        state_chip_inner,
        text="STOPPED",
        bg=BG_PANEL_ALT,
        fg=ACCENT_RED,
        font=("Segoe UI", 9, "bold"),
    )
    monitor_state.pack(side="left")

    tk.Frame(monitor_inner, bg=BORDER_SOFT, height=1).pack(fill="x", padx=16, pady=(0, 10))

    metrics_grid = tk.Frame(monitor_inner, bg=BG_SURFACE)
    metrics_grid.pack(fill="x", padx=16, pady=(0, 14))

    metrics_grid.grid_columnconfigure(0, weight=1)
    metrics_grid.grid_columnconfigure(1, weight=2)
    metrics_grid.grid_columnconfigure(2, weight=1)

    block_1 = tk.Frame(metrics_grid, bg=BG_SURFACE)
    block_1.grid(row=0, column=0, sticky="nsew", padx=(0, 14))

    ttk.Label(block_1, text="Tickets procesados", style="MetricTitle.TLabel").pack(anchor="w")
    count_label = ttk.Label(block_1, text="0", style="MetricValueMono.TLabel")
    count_label.pack(anchor="w", pady=(4, 0))

    block_2 = tk.Frame(metrics_grid, bg=BG_SURFACE)
    block_2.grid(row=0, column=1, sticky="nsew", padx=14)

    ttk.Label(block_2, text="Último evento", style="MetricTitle.TLabel").pack(anchor="w")
    last_event_label = tk.Label(
        block_2,
        text="Esperando actividad del monitor",
        bg=BG_SURFACE,
        fg=TEXT_PRIMARY,
        font=("Consolas", 16, "bold"),
        anchor="w",
        justify="left",
    )
    last_event_label.pack(anchor="w", pady=(4, 0), fill="x")

    block_3 = tk.Frame(metrics_grid, bg=BG_SURFACE)
    block_3.grid(row=0, column=2, sticky="nsew", padx=(14, 0))

    ttk.Label(block_3, text="Intervalo", style="MetricTitle.TLabel").pack(anchor="w")
    interval_label = ttk.Label(block_3, text="20s", style="MetricValue.TLabel")
    interval_label.pack(anchor="w", pady=(4, 0))

    # Tarjeta 2: estado de conectividad Zimbra/Notion.
    status_outer, status_inner = create_card(top_row, BORDER, BG_SURFACE, padding=1)
    status_outer.pack(side="left", fill="y", padx=(16, 0))
    status_outer.configure(width=300, height=170)
    status_outer.pack_propagate(False)

    tk.Label(
        status_inner,
        text="SYSTEM STATUS",
        bg=BG_SURFACE,
        fg=TEXT_MUTED,
        font=("Segoe UI", 9),
    ).pack(anchor="w", padx=16, pady=(14, 10))

    tk.Frame(status_inner, bg=BORDER_SOFT, height=1).pack(fill="x", padx=16)

    conn_section = tk.Frame(status_inner, bg=BG_SURFACE)
    conn_section.pack(fill="x", padx=16, pady=(14, 14))

    tk.Label(
        conn_section,
        text="Conexiones",
        bg=BG_SURFACE,
        fg=TEXT_FAINT,
        font=("Segoe UI", 8),
    ).pack(anchor="w", pady=(0, 12))

    # Fila Zimbra
    row_zimbra = tk.Frame(conn_section, bg=BG_SURFACE)
    row_zimbra.pack(fill="x", pady=(0, 10))

    tk.Label(
        row_zimbra,
        text="Zimbra",
        bg=BG_SURFACE,
        fg=TEXT_SECONDARY,
        font=("Segoe UI", 10),
    ).pack(side="left")

    zimbra_status = tk.Label(
        row_zimbra,
        text="UNKNOWN",
        bg=BG_SURFACE,
        fg=TEXT_MUTED,
        font=("Segoe UI", 10, "bold"),
    )
    zimbra_status.pack(side="right")

    # Fila Notion
    row_notion = tk.Frame(conn_section, bg=BG_SURFACE)
    row_notion.pack(fill="x", pady=(0, 2))

    tk.Label(
        row_notion,
        text="Notion",
        bg=BG_SURFACE,
        fg=TEXT_SECONDARY,
        font=("Segoe UI", 10),
    ).pack(side="left")

    notion_status = tk.Label(
        row_notion,
        text="UNKNOWN",
        bg=BG_SURFACE,
        fg=TEXT_MUTED,
        font=("Segoe UI", 10, "bold"),
    )
    notion_status.pack(side="right")

    # MAIN CONTENT AREA: stream de eventos + panel contextual.
    content = tk.Frame(main, bg=BG_APP)
    content.pack(fill="both", expand=True)

    # Panel izquierdo: stream temporal de eventos de monitoreo.
    console_outer, console_inner = create_card(content, BORDER, BG_SURFACE, padding=1)
    console_outer.pack(side="left", fill="both", expand=True)

    console_head = tk.Frame(console_inner, bg=BG_SURFACE)
    console_head.pack(fill="x", padx=16, pady=(14, 10))

    tk.Label(
        console_head,
        text="EVENT STREAM",
        bg=BG_SURFACE,
        fg=TEXT_MUTED,
        font=("Segoe UI", 9),
    ).pack(side="left")

    console_filters = tk.Frame(console_head, bg=BG_SURFACE)
    console_filters.pack(side="right")

    tk.Label(
        console_filters,
        text="FILTER: ALL",
        bg=BG_PANEL_ALT,
        fg=TEXT_SECONDARY,
        font=("Segoe UI", 7),
        padx=10,
        pady=4,
    ).pack(side="left", padx=(0, 8))

    tk.Label(
        console_filters,
        text="AUTO-SCROLL ON",
        bg=BG_PANEL_ALT,
        fg=TEXT_SECONDARY,
        font=("Segoe UI", 7),
        padx=10,
        pady=4,
    ).pack(side="left")

    tk.Frame(console_inner, bg=BORDER_SOFT, height=1).pack(fill="x", padx=16)

    stream_container = tk.Frame(console_inner, bg=BG_SURFACE)
    stream_container.pack(fill="both", expand=True, pady=(14, 0))

    event_stream = EventStream(stream_container)
    event_stream.pack(fill="both", expand=True)

    # Panel derecho: ultimo ticket, detalle y estado global.
    rail_outer, rail_inner = create_card(content, BORDER, BG_SURFACE, padding=1)
    rail_outer.pack(side="left", fill="y", padx=(16, 0))
    rail_outer.configure(width=300)
    rail_outer.pack_propagate(False)

    tk.Label(
        rail_inner,
        text="CONTEXT",
        bg=BG_SURFACE,
        fg=TEXT_MUTED,
        font=("Segoe UI", 9),
    ).pack(anchor="w", padx=16, pady=(14, 10))

    tk.Frame(rail_inner, bg=BORDER_SOFT, height=1).pack(fill="x", padx=16)

    ctx_wrap = tk.Frame(rail_inner, bg=BG_SURFACE)
    ctx_wrap.pack(fill="both", expand=True, padx=16, pady=(14, 16))

    last_ticket_block = tk.Frame(
        ctx_wrap,
        bg=BG_PANEL,
        highlightthickness=1,
        highlightbackground=BORDER_SOFT,
    )
    last_ticket_block.pack(fill="x", pady=(0, 10))

    tk.Label(
        last_ticket_block,
        text="Último ticket",
        bg=BG_PANEL,
        fg=TEXT_FAINT,
        font=("Segoe UI", 8),
    ).pack(anchor="w", padx=10, pady=(10, 4))

    last_ticket_label = tk.Label(
        last_ticket_block,
        text="—",
        bg=BG_PANEL,
        fg=TEXT_PRIMARY,
        font=("Consolas", 12, "bold"),
        anchor="w",
        justify="left",
    )
    last_ticket_label.pack(anchor="w", padx=10, pady=(0, 10))

    detail_block = tk.Frame(
        ctx_wrap,
        bg=BG_PANEL,
        highlightthickness=1,
        highlightbackground=BORDER_SOFT,
    )
    detail_block.pack(fill="both", expand=True, pady=(0, 10))

    tk.Label(
        detail_block,
        text="Detalle contextual",
        bg=BG_PANEL,
        fg=TEXT_FAINT,
        font=("Segoe UI", 8),
    ).pack(anchor="w", padx=10, pady=(10, 4))

    detail_label = tk.Label(
        detail_block,
        text="Sin actividad reciente",
        bg=BG_PANEL,
        fg=TEXT_SECONDARY,
        font=("Segoe UI", 10),
        anchor="nw",
        justify="left",
        wraplength=240,
    )
    detail_label.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    global_block = tk.Frame(
        ctx_wrap,
        bg=BG_PANEL,
        highlightthickness=1,
        highlightbackground=BORDER_SOFT,
    )
    global_block.pack(fill="x")

    tk.Label(
        global_block,
        text="Estado global",
        bg=BG_PANEL,
        fg=TEXT_FAINT,
        font=("Segoe UI", 8),
    ).pack(anchor="w", padx=10, pady=(10, 4))

    global_status_label = tk.Label(
        global_block,
        text="Sin datos aún",
        bg=BG_PANEL,
        fg=TEXT_PRIMARY,
        font=("Segoe UI", 11, "bold"),
        anchor="w",
    )
    global_status_label.pack(anchor="w", padx=10, pady=(0, 10))

    # Footer: shortcuts de teclado operativos.
    footer = tk.Frame(main, bg=BG_APP)
    footer.pack(fill="x", pady=(12, 0))

    ttk.Label(
        footer,
        text="Controles: 1 = iniciar monitor   ·   2 = detener   ·   Q = salir",
        style="Footer.TLabel",
    ).pack(side="left")

    ttk.Label(
        footer,
        text="by @Jhon Gil",
        style="Signature.TLabel",
    ).pack(side="right")

    # BUSINESS / MONITOR: wiring entre UI y servicio de monitoreo.
    event_queue: "queue.Queue[str]" = queue.Queue()
    # stop_event detiene monitor thread sin forzar cierre de app.
    stop_event = threading.Event()
    monitor_thread: threading.Thread | None = None
    # Dict mutables para poder escribir desde cierres internos.
    monitor_running = {"value": False}
    uptime_seconds = {"value": 0}

    def classify_level(msg: str) -> str:
        # Clasifica mensaje textual a nivel log para colorear stream.
        upper = msg.upper()
        if "[ERROR" in upper or upper.startswith("ERROR"):
            return "ERROR"
        if "[WARN" in upper or "WARNING" in upper:
            return "WARN"
        if "[INFO" in upper:
            return "INFO"
        if "SUCCESS" in upper or "CREADO" in upper or "REGISTRO" in upper:
            return "SUCCESS"
        if msg.startswith("[SYSTEM]"):
            return "SYSTEM"
        return "INFO"

    def derive_category(msg: str, level: str) -> str:
        # Deriva categoria funcional (ZIMBRA_SYNC, NOTION_PUSH, etc.) para lectura rapida.
        upper = msg.upper()
        if "ZIMBRA" in upper:
            return "ZIMBRA_SYNC"
        if "NOTION" in upper:
            return "NOTION_PUSH"
        if "MONITOR" in upper:
            return "MONITOR"
        if "TICKET" in upper:
            return "TICKET_EVENT"
        if level == "SYSTEM":
            return "SYS_CORE"
        if level == "WARN":
            return "EXCEPTION_HANDLED"
        if level == "ERROR":
            return "PIPELINE_ERROR"
        return "EVENT"

    def derive_meta(msg: str, level: str) -> str:
        # Meta corto opcional para mostrar contexto tecnico en la cabecera de cada evento.
        upper = msg.upper()
        if level == "ERROR":
            return "RETRY 1/3"
        if "NOTION" in upper:
            return "NOTION_API"
        if "ZIMBRA" in upper:
            return "IMAP"
        if "TICKET" in upper:
            return "TKT_FLOW"
        return ""

    def extract_clean_message(msg: str) -> str:
        # Limpia prefijos [SYSTEM]/[INFO]/... para mostrar texto final al usuario.
        return re.sub(r"^\[(SYSTEM|INFO|WARN|ERROR)\]\s*", "", msg, flags=re.IGNORECASE).strip()

    def set_monitor_visual(running: bool) -> None:
        # Sincroniza chip visual y estado global cuando monitor inicia/detiene.
        if running:
            monitor_state.config(text="RUNNING", fg=ACCENT_GREEN)
            state_dot_canvas.itemconfig(state_dot, fill=ACCENT_GREEN, outline=ACCENT_GREEN)
            global_status_label.config(text="Monitor activo", fg=ACCENT_GREEN)
        else:
            monitor_state.config(text="STOPPED", fg=ACCENT_RED)
            state_dot_canvas.itemconfig(state_dot, fill=ACCENT_RED, outline=ACCENT_RED)
            global_status_label.config(text="Monitor detenido", fg=TEXT_PRIMARY)

    def update_connection_status(label: tk.Label, ok: bool) -> None:
        # Helper simple para pintar OK/FAIL por conexion.
        label.config(text="OK" if ok else "FAIL", fg=ACCENT_GREEN if ok else ACCENT_RED)

    def try_extract_ticket(text: str) -> str | None:
        # Busca codigos de ticket en mensajes de log para actualizar "Ultimo ticket".
        patterns = [
            r"\bSOP[0-9A-Z]+\b",
            r"\bTKT[0-9A-Z]+\b",
            r"\bINC[0-9A-Z]+\b",
        ]
        for pattern in patterns:
            # Recorre patrones conocidos y retorna primer match.
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(0)
        return None

    def check_zimbra() -> None:
        try:
            # Healthcheck basico: lectura limitada de 1 correo.
            client = ZimbraClient()
            client.get_recent_emails_from_support(limit=1)
            update_connection_status(zimbra_status, True)
        except Exception:
            update_connection_status(zimbra_status, False)

    def check_notion() -> None:
        try:
            # Healthcheck basico: retrieve de base Notion.
            client = NotionTicketClient()
            client.test_connection()
            update_connection_status(notion_status, True)
        except Exception:
            update_connection_status(notion_status, False)

    def on_event(msg: str) -> None:
        # Productor de eventos desde monitor thread hacia cola thread-safe.
        event_queue.put(msg)

    count_label.config(text="0")

    def add_stream_event(raw_msg: str):
        # Traduce texto crudo a componentes visuales del EventStream.
        level = classify_level(raw_msg)
        category = derive_category(raw_msg, level)
        meta = derive_meta(raw_msg, level)
        clean_msg = extract_clean_message(raw_msg)
        event_stream.add_event(level, category, clean_msg, meta)

    def start_monitor() -> None:
        nonlocal monitor_thread
        if monitor_running["value"]:
            return

        # Antes de arrancar, valida conectividad de dependencias externas.
        add_stream_event("[SYSTEM] Verificando conexiones...")
        check_zimbra()
        check_notion()

        stop_event.clear()
        # Crea servicio y lo ejecuta en hilo daemon para no bloquear UI.
        monitor = MonitorService(on_event=on_event, stop_event=stop_event)
        monitor_thread = threading.Thread(target=monitor.run_loop, daemon=True)
        monitor_thread.start()

        monitor_running["value"] = True
        uptime_seconds["value"] = 0
        set_monitor_visual(True)

        add_stream_event("[SYSTEM] Monitor ARCA iniciado.")
        add_stream_event("[INFO] Monitoreo en ejecución. Intervalo activo.")
        detail_label.config(
            text="El motor de monitoreo quedó inicializado y está escuchando nuevos correos desde el buzón configurado."
        )

    def stop_monitor() -> None:
        if not monitor_running["value"]:
            return

        # Solicita parada cooperativa del monitor.
        stop_event.set()
        monitor_running["value"] = False
        set_monitor_visual(False)

        add_stream_event("[SYSTEM] Monitor ARCA detenido.")
        detail_label.config(text="El monitoreo fue detenido manualmente por el operador.")

    def on_key(event: tk.Event) -> None:
        # Atajos operativos:
        # 1 -> iniciar, 2 -> detener, q -> salir.
        key = event.keysym.lower()
        if key == "1":
            start_monitor()
        elif key == "2":
            stop_monitor()
        elif key == "q":
            stop_monitor()
            root.destroy()

    root.bind("<Key>", on_key)

    def drain_queue():
        try:
            while True:
                # Consumidor: vacia todos los eventos pendientes en este tick UI.
                msg = event_queue.get_nowait()

                if msg.startswith("TICKET_COUNT:"):
                    # Evento de metrica numerica para contador principal.
                    count = int(msg.split(":", 1)[1])
                    count_label.config(text=str(count))
                    continue

                clean_msg = msg.strip()
                last_event_label.config(text=shorten(extract_clean_message(clean_msg), 64))
                add_stream_event(clean_msg)

                ticket_found = try_extract_ticket(clean_msg)
                if ticket_found:
                    # Actualiza ultimo ticket detectado en logs.
                    last_ticket_label.config(text=ticket_found)

                level = classify_level(clean_msg)
                if level == "ERROR":
                    # Estado global en advertencia cuando hay errores recientes.
                    global_status_label.config(
                        text="Incidencias recientes detectadas",
                        fg=ACCENT_AMBER
                    )
                    detail_label.config(text=shorten(extract_clean_message(clean_msg), 180))
                elif level == "SUCCESS":
                    # Estado global en verde cuando hay eventos exitosos.
                    global_status_label.config(
                        text="Última sincronización exitosa",
                        fg=ACCENT_GREEN
                    )
                    detail_label.config(text=shorten(extract_clean_message(clean_msg), 180))
                else:
                    detail_label.config(text=shorten(extract_clean_message(clean_msg), 180))

        except queue.Empty:
            pass

        # Reagenda consumo de cola cada 200ms para mantener UI reactiva.
        root.after(200, drain_queue)

    root.after(200, drain_queue)

    def tick_uptime():
        # Incrementa uptime solo cuando monitor esta corriendo.
        if monitor_running["value"]:
            uptime_seconds["value"] += 1

        # Convierte segundos acumulados a formato HH:MM:SS.
        total = uptime_seconds["value"]
        hh = total // 3600
        mm = (total % 3600) // 60
        ss = total % 60
        session_uptime_label.config(text=f"{hh:02}:{mm:02}:{ss:02}")

        # Reagenda cada 1 segundo.
        root.after(1000, tick_uptime)

    root.after(1000, tick_uptime)

    # Estado inicial del dashboard al abrir.
    set_monitor_visual(False)
    add_stream_event("[SYSTEM] Interfaz ARCA lista.")
    add_stream_event("[INFO] Presiona 1 para iniciar el monitor.")

    return root