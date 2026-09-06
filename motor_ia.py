import os
import sys
import gc
from pathlib import Path
from utils import Tiempo, InterceptorTerminal


class MotorTranscriptor:
    def __init__(self, callbacks):
        """
        callbacks es un diccionario con funciones de la interfaz para actualizar visualmente:
        'estado': actualiza el label principal
        'preview': añade texto a la consola
        'progreso': actualiza la barra de descarga
        'fin': avisa cuando termina todo
        'error': lanza una ventana de error
        'check_abort': devuelve True si el usuario canceló
        """
        self.cb = callbacks

    def procesar(self, ruta_archivo, carpeta_final, nombre_base, modelo_elegido, hilos):
        original_stderr = sys.stderr
        try:
            ruta_final = os.path.join(carpeta_final, nombre_base)
            os.makedirs(ruta_final, exist_ok=True)

            ruta_modelo = (
                "./models/fw_small"
                if modelo_elegido == "small"
                else "./models/fw_medium"
            )

            # --- Lógica de Descarga ---
            if modelo_elegido == "medium" and not (
                os.path.exists(os.path.join(ruta_modelo, "model.bin"))
                or os.path.exists(os.path.join(ruta_modelo, "model.safetensors"))
            ):
                self.cb["estado"]("Preparando descarga del modelo...")
                self.cb["preview"](
                    "Iniciando descarga del modelo de alta precision (aprox 1.5 GB)..."
                )

                from huggingface_hub import snapshot_download

                sys.stderr = InterceptorTerminal(
                    self.cb["progreso"], self.cb["check_abort"]
                )
                try:
                    snapshot_download(
                        repo_id="Systran/faster-whisper-medium", local_dir=ruta_modelo
                    )
                    self.cb["preview"](
                        "\nDescarga completada con exito. Ahora puede usar el 'Modelo Preciso'."
                    )
                    self.cb["fin"]("descargado", None)
                except InterruptedError:
                    self.cb["fin"]("cancelado", None)
                except Exception as e:
                    self.cb["error"](f"Error de Descarga: {str(e)}")
                    self.cb["fin"]("error", None)
                finally:
                    sys.stderr = original_stderr
                return

            if self.cb["check_abort"]():
                self.cb["fin"]("cancelado", None)
                return

            self.cb["estado"]("Cargando modelo en memoria...")

            # Importamos Whisper solo si es necesario usarlo
            from faster_whisper import WhisperModel

            model = WhisperModel(
                ruta_modelo, device="cpu", compute_type="int8", cpu_threads=hilos
            )

            self.cb["estado"]("Transcribiendo audio... (esto puede tomar un tiempo)")
            segments, info = model.transcribe(ruta_archivo, language="es")

            ruta_txt_generado = os.path.join(ruta_final, f"{nombre_base}.txt")

            with open(ruta_txt_generado, "w", encoding="utf-8") as f_txt:
                for segment in segments:
                    if self.cb["check_abort"]():
                        break

                    inicio = Tiempo(segment.start)
                    fin = Tiempo(segment.end)
                    linea_txt = (
                        f"[{inicio.marca_tiempo} -> {fin.marca_tiempo}] {segment.text}"
                    )

                    f_txt.write(linea_txt + "\n")
                    self.cb["preview"](linea_txt)

            if not self.cb["check_abort"]():
                self.cb["fin"]("completado", ruta_txt_generado)
            else:
                self.cb["fin"]("cancelado", None)

        except Exception as e:
            sys.stderr = original_stderr
            error_str = str(e)

            if (
                "mkl_malloc" in error_str.lower()
                or "memory" in error_str.lower()
                or "allocate" in error_str.lower()
            ):
                msj = "Error: Memoria RAM insuficiente.\nCierra otros programas o reduce la cantidad de hilos."
            else:
                msj = f"Ocurrio un problema inesperado:\n{error_str}"

            self.cb["error"](msj)
            self.cb["fin"]("error", None)

        finally:
            if "model" in locals():
                del model
            gc.collect()
