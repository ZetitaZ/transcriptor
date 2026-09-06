import os
import threading
from pathlib import Path
import ctypes

import tkinter as tk
from tkinter import filedialog, messagebox
from tkinter.ttk import Progressbar, Spinbox
from tkinterdnd2 import TkinterDnD, DND_FILES

from utils import sanitizar_nombre, acortar_ruta
from motor_ia import MotorTranscriptor

os.environ["OMP_NUM_THREADS"] = "1"
os.environ["MKL_NUM_THREADS"] = "1"

try:
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    pass


class TranscriptorApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Transcriptor Inteligente")

        ancho_ventana = 650
        alto_ventana = 900
        ancho_pantalla = self.root.winfo_screenwidth()
        alto_pantalla = self.root.winfo_screenheight()
        pos_x = int((ancho_pantalla / 2) - (ancho_ventana / 2))
        pos_y = int((alto_pantalla / 2) - (alto_ventana / 2)) - 60

        self.root.geometry(f"{ancho_ventana}x{alto_ventana}+{pos_x}+{pos_y}")
        self.root.minsize(ancho_ventana, alto_ventana)
        self.root.configure(bg="#f5f7fa")

        self.ruta_archivo = ""
        self.ruta_txt_generado = ""
        self.carpeta_destino = os.path.abspath("transcripciones")
        self.abortar = False

        self.fuente_base = ("Segoe UI", 10)
        self.fuente_titulos = ("Segoe UI", 16, "bold")
        self.fuente_subtitulos = ("Segoe UI", 11, "bold")
        self.fuente_proceso = ("Segoe UI", 10, "bold")

        # Callbacks para conectar la UI con el Motor IA
        self.callbacks_motor = {
            "estado": lambda msg: self.actualizar_estado(msg),
            "preview": lambda msg: self.log_preview(msg),
            "progreso": lambda msg: self.log_progreso_descarga(msg),
            "fin": lambda estado, txt: self.terminar_interfaz(estado, txt),
            "error": lambda err: self.root.after(
                0, lambda: messagebox.showerror("Error", err)
            ),
            "check_abort": lambda: self.abortar,
        }

        self.construir_interfaz()

    def construir_interfaz(self):
        self.lbl_titulo = tk.Label(
            self.root,
            text="Transcriptor de Video y Audio",
            font=self.fuente_titulos,
            bg="#f5f7fa",
            fg="#2c3e50",
        )
        self.lbl_titulo.pack(pady=(20, 10))

        # --- PASO 1 ---
        self.frame_paso1 = tk.Frame(self.root, bg="#ffffff", bd=1, relief="solid")
        self.frame_paso1.pack(fill=tk.X, padx=30, pady=10)
        tk.Label(
            self.frame_paso1,
            text="1. Archivo de entrada y destino",
            font=self.fuente_subtitulos,
            bg="#ffffff",
            fg="#34495e",
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.zona_drop = tk.Label(
            self.frame_paso1,
            text="Arrastra tu archivo de audio/video aqui\no haz clic para buscar",
            bg="#f8fafc",
            fg="#64748b",
            relief="groove",
            bd=2,
            font=self.fuente_base,
            cursor="hand2",
        )
        self.zona_drop.pack(fill=tk.X, padx=20, pady=10, ipady=30)
        self.zona_drop.drop_target_register(DND_FILES)
        self.zona_drop.dnd_bind("<<Drop>>", self.soltar_archivo)
        self.zona_drop.bind("<Button-1>", lambda e: self.seleccionar_archivo())

        self.frame_destino = tk.Frame(self.frame_paso1, bg="#ffffff")
        self.frame_destino.pack(fill=tk.X, padx=20, pady=(0, 15))
        self.lbl_destino = tk.Label(
            self.frame_destino,
            text=f"Guardar en: {acortar_ruta(self.carpeta_destino)}",
            font=("Segoe UI", 9),
            bg="#ffffff",
            fg="#7f8c8d",
            anchor="w",
        )
        self.lbl_destino.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.btn_destino = tk.Button(
            self.frame_destino,
            text="Cambiar Destino",
            command=self.cambiar_destino,
            font=("Segoe UI", 9),
            bg="#e2e8f0",
            relief="flat",
            cursor="hand2",
        )
        self.btn_destino.pack(side=tk.RIGHT)

        # --- PASO 2 ---
        self.frame_paso2 = tk.Frame(self.root, bg="#ffffff", bd=1, relief="solid")
        tk.Label(
            self.frame_paso2,
            text="2. Opciones de procesamiento",
            font=self.fuente_subtitulos,
            bg="#ffffff",
            fg="#34495e",
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.frame_botones = tk.Frame(self.frame_paso2, bg="#ffffff")
        self.frame_botones.pack(pady=10)
        self.btn_small = tk.Button(
            self.frame_botones,
            text="Modelo Rapido\n(Velocidad)",
            command=lambda: self.iniciar_hilo("small"),
            font=("Segoe UI", 10, "bold"),
            bg="#2ecc71",
            fg="white",
            relief="flat",
            width=18,
            height=2,
            cursor="hand2",
        )
        self.btn_small.grid(row=0, column=0, padx=10)
        self.btn_medium = tk.Button(
            self.frame_botones,
            text="Modelo Preciso\n(Calidad)",
            command=lambda: self.iniciar_hilo("medium"),
            font=("Segoe UI", 10, "bold"),
            bg="#3498db",
            fg="white",
            relief="flat",
            width=18,
            height=2,
            cursor="hand2",
        )
        self.btn_medium.grid(row=0, column=1, padx=10)

        self.btn_avanzadas = tk.Button(
            self.frame_paso2,
            text="Ver opciones avanzadas",
            command=self.toggle_avanzadas,
            relief="flat",
            bg="#ffffff",
            fg="#95a5a6",
            font=("Segoe UI", 9, "underline"),
            cursor="hand2",
        )
        self.btn_avanzadas.pack(pady=(0, 10))

        self.frame_avanzadas = tk.Frame(self.frame_paso2, bg="#f1f5f9")
        tk.Label(
            self.frame_avanzadas,
            text="Cantidad de hilos del procesador (RAM/CPU uso):",
            bg="#f1f5f9",
            font=("Segoe UI", 8),
            fg="#475569",
        ).pack(pady=(10, 2))

        hilos_totales = os.cpu_count() or 4
        default_hilos = 2 if hilos_totales <= 4 else 4
        self.var_hilos = tk.IntVar(value=default_hilos)
        self.spin_hilos = Spinbox(
            self.frame_avanzadas,
            from_=1,
            to=hilos_totales,
            textvariable=self.var_hilos,
            width=5,
            state="readonly",
        )
        self.spin_hilos.pack(pady=(0, 10))

        # --- PASO 3 ---
        self.frame_paso3 = tk.Frame(self.root, bg="#f5f7fa")
        self.lbl_estado = tk.Label(
            self.frame_paso3,
            text="Preparando entorno...",
            font=self.fuente_base,
            bg="#f5f7fa",
            fg="#34495e",
        )
        self.lbl_estado.pack(pady=(10, 0))
        tk.Label(
            self.frame_paso3,
            text="* La inteligencia artificial puede cometer errores en la transcripcion.",
            font=("Segoe UI", 8, "italic"),
            bg="#f5f7fa",
            fg="#7f8c8d",
        ).pack(pady=(0, 5))

        self.barra_progreso = Progressbar(
            self.frame_paso3, orient="horizontal", mode="indeterminate", length=400
        )
        self.barra_progreso.pack(pady=10)

        self.frame_vista_previa = tk.Frame(
            self.frame_paso3, bg="white", bd=1, relief="solid"
        )
        self.frame_vista_previa.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        self.txt_vista_previa = tk.Text(
            self.frame_vista_previa,
            state=tk.DISABLED,
            bg="#ffffff",
            fg="#2c3e50",
            font=("Segoe UI", 10),
            height=6,
            wrap=tk.WORD,
            relief="flat",
            padx=10,
            pady=10,
        )
        self.txt_vista_previa.pack(fill=tk.BOTH, expand=True)

        self.frame_acciones_finales = tk.Frame(self.frame_paso3, bg="#f5f7fa")
        self.frame_acciones_finales.pack(pady=15)
        self.btn_cancelar = tk.Button(
            self.frame_acciones_finales,
            text="Cancelar Proceso",
            command=self.cancelar_proceso,
            font=("Segoe UI", 10),
            bg="#e74c3c",
            fg="white",
            relief="flat",
            padx=15,
            cursor="hand2",
        )
        self.btn_abrir = tk.Button(
            self.frame_acciones_finales,
            text="ABRIR TEXTO TRANSCRITO",
            command=self.abrir_archivo,
            font=("Segoe UI", 11, "bold"),
            bg="#2980b9",
            fg="white",
            relief="flat",
            padx=20,
            pady=5,
            cursor="hand2",
        )

    # --- Logica de UI ---
    def toggle_avanzadas(self):
        if self.frame_avanzadas.winfo_ismapped():
            self.frame_avanzadas.pack_forget()
            self.btn_avanzadas.config(text="Ver opciones avanzadas")
        else:
            self.frame_avanzadas.pack(fill=tk.X, padx=15, pady=(0, 15))
            self.btn_avanzadas.config(text="Ocultar opciones avanzadas")

    def actualizar_estado(self, mensaje, color="#3498db", usar_negrilla=True):
        fuente_aplicar = self.fuente_proceso if usar_negrilla else self.fuente_base
        self.root.after(
            0,
            lambda: self.lbl_estado.config(text=mensaje, fg=color, font=fuente_aplicar),
        )

    def log_preview(self, texto):
        def actualizar_texto():
            self.txt_vista_previa.config(state=tk.NORMAL)
            self.txt_vista_previa.insert(tk.END, texto + "\n")
            self.txt_vista_previa.see(tk.END)
            self.txt_vista_previa.config(state=tk.DISABLED)

        self.root.after(0, actualizar_texto)

    def log_progreso_descarga(self, texto):
        def actualizar_texto():
            self.txt_vista_previa.config(state=tk.NORMAL)
            lineas = self.txt_vista_previa.get(1.0, tk.END).split("\n")
            if len(lineas) >= 2 and lineas[-2].startswith("Descargando:"):
                self.txt_vista_previa.delete(f"{len(lineas) - 2}.0", tk.END)
                self.txt_vista_previa.insert(tk.END, texto + "\n")
            else:
                self.txt_vista_previa.insert(tk.END, texto + "\n")
            self.txt_vista_previa.see(tk.END)
            self.txt_vista_previa.config(state=tk.DISABLED)

        self.root.after(0, actualizar_texto)

    def soltar_archivo(self, event):
        archivo = event.data.strip("{}")
        self.cargar_archivo(archivo)

    def seleccionar_archivo(self):
        if self.abortar:
            return
        archivo = filedialog.askopenfilename(
            title="Seleccionar archivo",
            filetypes=(
                ("Video/Audio", "*.mp4 *.mkv *.mp3 *.wav *.avi *.mov *.flac"),
                ("Todos", "*.*"),
            ),
        )
        if archivo:
            self.cargar_archivo(archivo)

    def cambiar_destino(self):
        if self.abortar:
            return
        carpeta = filedialog.askdirectory(
            title="Elegir carpeta para guardar los textos"
        )
        if carpeta:
            self.carpeta_destino = os.path.abspath(carpeta)
            self.lbl_destino.config(
                text=f"Guardar en: {acortar_ruta(self.carpeta_destino)}"
            )

    def cargar_archivo(self, ruta):
        self.ruta_archivo = ruta
        nombre = Path(ruta).name
        self.zona_drop.config(
            text=f"Archivo cargado:\n{nombre}\n(Clic para cambiar)",
            bg="#e8f5e9",
            fg="#2e7d32",
            font=("Segoe UI", 10, "bold"),
            relief="solid",
        )
        self.frame_paso2.pack(fill=tk.X, padx=30, pady=10)
        self.frame_paso3.pack_forget()
        self.btn_abrir.pack_forget()

    def abrir_archivo(self):
        if self.ruta_txt_generado and os.path.exists(self.ruta_txt_generado):
            os.startfile(self.ruta_txt_generado)

    def cancelar_proceso(self):
        self.abortar = True
        self.btn_cancelar.config(state=tk.DISABLED, text="Deteniendo...")
        self.actualizar_estado("Cancelando operacion...", color="#e74c3c")

    def iniciar_hilo(self, modelo_elegido):
        self.abortar = False
        self.btn_small.config(state=tk.DISABLED, bg="#95a5a6")
        self.btn_medium.config(state=tk.DISABLED, bg="#95a5a6")
        self.btn_destino.config(state=tk.DISABLED)
        self.spin_hilos.config(state=tk.DISABLED)
        self.zona_drop.dnd_bind("<<Drop>>", "")
        self.zona_drop.unbind("<Button-1>")

        self.frame_paso3.pack(fill=tk.BOTH, expand=True, padx=30, pady=10)
        self.btn_abrir.pack_forget()
        self.btn_cancelar.pack(side=tk.TOP)
        self.btn_cancelar.config(state=tk.NORMAL, text="Cancelar Proceso")
        self.txt_vista_previa.config(state=tk.NORMAL)
        self.txt_vista_previa.delete(1.0, tk.END)
        self.txt_vista_previa.config(state=tk.DISABLED)

        self.actualizar_estado("Iniciando motor de transcripcion...")
        self.barra_progreso.start(15)

        # Usamos el Motor Externo
        nombre_base = sanitizar_nombre(Path(self.ruta_archivo).stem)
        hilos = self.var_hilos.get()
        motor = MotorTranscriptor(self.callbacks_motor)

        # Corremos el motor en un hilo separado
        hilo = threading.Thread(
            target=motor.procesar,
            args=(
                self.ruta_archivo,
                self.carpeta_destino,
                nombre_base,
                modelo_elegido,
                hilos,
            ),
        )
        hilo.start()

    def terminar_interfaz(self, estado_final, ruta_generada=None):
        def actualizar_ui():
            self.barra_progreso.stop()
            self.btn_cancelar.pack_forget()
            self.btn_destino.config(state=tk.NORMAL)
            self.spin_hilos.config(state="readonly")
            self.btn_small.config(state=tk.NORMAL, bg="#2ecc71")
            self.btn_medium.config(state=tk.NORMAL, bg="#3498db")
            self.zona_drop.dnd_bind("<<Drop>>", self.soltar_archivo)
            self.zona_drop.bind("<Button-1>", lambda e: self.seleccionar_archivo())

            if estado_final == "completado":
                self.ruta_txt_generado = ruta_generada
                self.barra_progreso.pack_forget()
                self.lbl_estado.config(
                    text="Proceso completado con exito",
                    fg="#27ae60",
                    font=("Segoe UI", 12, "bold"),
                )
                self.btn_abrir.pack(side=tk.TOP, pady=10)
            elif estado_final == "descargado":
                self.barra_progreso.pack_forget()
                self.lbl_estado.config(
                    text="Modelo descargado correctamente",
                    fg="#27ae60",
                    font=("Segoe UI", 12, "bold"),
                )
            elif estado_final == "cancelado":
                self.lbl_estado.config(
                    text="Operacion cancelada por el usuario",
                    fg="#e74c3c",
                    font=("Segoe UI", 12, "bold"),
                )
                self.barra_progreso.pack_forget()
            else:
                self.lbl_estado.config(
                    text="Error durante el proceso",
                    fg="#e74c3c",
                    font=("Segoe UI", 12, "bold"),
                )
                self.barra_progreso.pack_forget()

        self.root.after(0, actualizar_ui)


if __name__ == "__main__":
    ventana = TkinterDnD.Tk()
    app = TranscriptorApp(ventana)
    ventana.mainloop()
