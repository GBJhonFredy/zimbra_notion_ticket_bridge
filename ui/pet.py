# ui/pet.py
import tkinter as tk
from pathlib import Path
from typing import Dict, Optional


class PetWindow:
    """
    Ventana flotante con la mascota (PNG con transparencia) y tarjeta de notificación.
    """

    def __init__(
        self,
        poses: Optional[Dict[str, str]] = None,
        size: int = 150,
    ) -> None:
        if poses is None:
            poses = {
                "ok": "assets/goldie-goldie-sleeping.png",
                "new_ticket": "assets/goldie-goldie-thinking.png",
                "new_mail": "assets/goldie-goldie-listening.png",
                "notion_error": "assets/goldie-goldie-confused.png",
                "pending_item": "assets/goldie-goldie-surprised.png",
                "pending_summary": "assets/goldie-goldie-greeting.png",
                "in_progress_item": "assets/goldie-goldie-artist.png",
                "in_progress_summary": "assets/goldie-goldie-burying-bone.png",
                "stale_item": "assets/goldie-goldie-holding-bone.png",
                "done_summary": "assets/goldie-goldie-celebrating.png",
                "support_1": "assets/goldie-goldie-ball-play.png",
                "support_2": "assets/goldie-goldie-zooming.png",
            }

        self.target_size = size

        self.bg_color = "#1e1e1e"
        self.border_color = "#3a3a3a"
        self.text_color = "#f5f5f5"
        self.badge_bg = "#252525"
        self.transparent_color = "#ff00ff"

        self.state_labels = {
            "ok": "AL DÍA",
            "new_ticket": "NUEVO TICKET",
            "new_mail": "NUEVO CORREO",
            "notion_error": "ERROR NOTION",
            "pending_item": "PENDIENTE",
            "pending_summary": "PENDIENTES",
            "in_progress_item": "EN PROCESO",
            "in_progress_summary": "EN PROCESO",
            "stale_item": "PRIORIZAR",
            "done_summary": "FINALIZADAS",
            "support_1": "INFO",
            "support_2": "INFO",
        }

        self.images: Dict[str, tk.PhotoImage] = {}
        for state, path in poses.items():
            img_file = Path(path)
            if not img_file.exists():
                raise FileNotFoundError(f"No se encontró la imagen: {img_file}")

            base = tk.PhotoImage(file=str(img_file))
            w, h = base.width(), base.height()
            scale = min(self.target_size / w, self.target_size / h)

            if scale < 1:
                factor = max(1, int(round(1 / scale)))
                scaled = base.subsample(factor, factor)
            elif scale > 1:
                factor = int(round(scale))
                scaled = base.zoom(factor, factor)
            else:
                scaled = base

            self.images[state] = scaled

        self.current_state = "ok" if "ok" in self.images else next(iter(self.images))
        current_img = self.images[self.current_state]

        self.root = tk.Toplevel()
        self.root.title("ARCA Pet")
        self.root.overrideredirect(True)
        self.root.attributes("-topmost", True)
        self.root.config(bg=self.transparent_color)
        self.root.geometry(f"{self.target_size}x{self.target_size}+40+40")

        try:
            self.root.wm_attributes("-transparentcolor", self.transparent_color)
        except tk.TclError:
            pass

        self.canvas = tk.Canvas(
            self.root,
            width=self.target_size,
            height=self.target_size,
            bg=self.transparent_color,
            highlightthickness=0,
            bd=0,
            relief="flat",
        )
        self.canvas.pack(fill="both", expand=True)

        self.image_id = self.canvas.create_image(
            self.target_size // 2,
            self.target_size // 2,
            image=current_img,
        )

        self._drag_data = {"x": 0, "y": 0}
        self.canvas.bind("<ButtonPress-1>", self._on_start_drag)
        self.canvas.bind("<B1-Motion>", self._on_drag)

        self._create_message_window()
        self._update_message_position()

    def _create_message_window(self) -> None:
        self.msg_win = tk.Toplevel(self.root)
        self.msg_win.overrideredirect(True)
        self.msg_win.attributes("-topmost", True)
        self.msg_win.config(bg=self.bg_color)

        self.msg_width = 370
        self.msg_height = 150

        x = self.root.winfo_x() + self.target_size + 12
        y = self.root.winfo_y()
        self.msg_win.geometry(f"{self.msg_width}x{self.msg_height}+{x}+{y}")

        frame = tk.Frame(
            self.msg_win,
            bg=self.bg_color,
            highlightthickness=1,
            highlightbackground=self.border_color,
            bd=0,
        )
        frame.pack(fill="both", expand=True, padx=4, pady=4)

        header = tk.Frame(frame, bg=self.bg_color)
        header.pack(fill="x", padx=10, pady=(10, 6))

        self.status_chip = tk.Label(
            header,
            text=self.state_labels.get(self.current_state, "ESTADO"),
            bg=self.badge_bg,
            fg=self.text_color,
            font=("Segoe UI", 8, "bold"),
            padx=8,
            pady=3,
            anchor="w",
        )
        self.status_chip.pack(side="left")

        body = tk.Frame(frame, bg=self.bg_color)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        self.msg_label = tk.Label(
            body,
            text="",
            bg=self.bg_color,
            fg=self.text_color,
            font=("Segoe UI", 9),
            justify="left",
            wraplength=self.msg_width - 40,
            anchor="nw",
        )
        self.msg_label.pack(fill="both", expand=True, anchor="nw")

        self.msg_win.bind("<ButtonPress-1>", self._on_start_drag_message)
        self.msg_win.bind("<B1-Motion>", self._on_drag_message)

    def _update_message_position(self) -> None:
        self.root.update_idletasks()
        self.msg_win.update_idletasks()

        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_h = self.root.winfo_height()
        msg_h = self.msg_win.winfo_height()

        x = root_x + self.target_size + 12
        y = root_y + max(0, (root_h - msg_h) // 2)

        self.msg_win.geometry(f"+{x}+{y}")

    def _on_start_drag(self, event) -> None:
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def _on_drag(self, event) -> None:
        x = self.root.winfo_x() + event.x - self._drag_data["x"]
        y = self.root.winfo_y() + event.y - self._drag_data["y"]
        self.root.geometry(f"+{x}+{y}")
        self._update_message_position()

    def _on_start_drag_message(self, event) -> None:
        self._drag_data["x"] = event.x_root - self.root.winfo_x()
        self._drag_data["y"] = event.y_root - self.root.winfo_y()

    def _on_drag_message(self, event) -> None:
        x = event.x_root - self._drag_data["x"]
        y = event.y_root - self._drag_data["y"]
        self.root.geometry(f"+{x}+{y}")
        self._update_message_position()

    def set_state(self, state: str, message: str) -> None:
        if state in self.images:
            self.current_state = state
            self.canvas.itemconfigure(self.image_id, image=self.images[state])

        self.status_chip.config(
            text=self.state_labels.get(state, state.upper().replace("_", " "))
        )
        self.msg_label.config(text=message)
        self._update_message_position()