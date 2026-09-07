import gc
import os
import sys
import traceback

from huggingface_hub.utils import HfHubHTTPError
from requests.exceptions import RequestException

from utils import InterceptorTerminal, Tiempo, obtener_ruta_raiz


class MotorTranscriptor:
    def __init__(self, callbacks):
        self.cb = callbacks

    def procesar(self, ruta_archivo, carpeta_final, nombre_base, modelo_elegido, hilos):
        original_stderr = sys.stderr
        try:
            ruta_final = os.path.join(carpeta_final, nombre_base)
            os.makedirs(ruta_final, exist_ok=True)

            ruta_base = obtener_ruta_raiz()
            nombre_carpeta = "fw_small" if modelo_elegido == "small" else "fw_medium"
            ruta_modelo = os.path.join(ruta_base, "models", nombre_carpeta)

            repo_id = (
                "Systran/faster-whisper-small"
                if modelo_elegido == "small"
                else "Systran/faster-whisper-medium"
            )
            peso_msg = "aprox. 400 MB" if modelo_elegido == "small" else "aprox. 1.5 GB"
            nombre_modelo = "Rapido" if modelo_elegido == "small" else "Preciso"

            # Evita que luego de descargar la transcripcion inicie automaticamente
            descarga_realizada = False

            if not (
                os.path.exists(os.path.join(ruta_modelo, "model.bin"))
                or os.path.exists(os.path.join(ruta_modelo, "model.safetensors"))
            ):
                self.cb["estado"](f"Preparando descarga del modelo {nombre_modelo}...")
                self.cb["preview"](
                    f"Iniciando descarga ({peso_msg}). Esto se hace solo una vez..."
                )

                from huggingface_hub import snapshot_download

                sys.stderr = InterceptorTerminal(
                    self.cb["progreso"], self.cb["check_abort"]
                )

                try:
                    snapshot_download(repo_id=repo_id, local_dir=ruta_modelo)
                    self.cb["preview"](
                        f"\nDescarga completada con exito. Listo para usar el modelo {nombre_modelo}."
                    )
                    descarga_realizada = True
                except InterruptedError:
                    self.cb["fin"]("cancelado", None)
                    return
                except (RequestException, HfHubHTTPError) as e:
                    self.cb["error"](
                        f"Error de red al descargar. Verifica tu conexion: {e!s}"
                    )
                    self.cb["fin"]("error", None)
                    return
                except OSError as e:
                    self.cb["error"](f"Error de almacenamiento: {e!s}")
                    self.cb["fin"]("error", None)
                    return
                finally:
                    sys.stderr = original_stderr

            if self.cb["check_abort"]():
                self.cb["fin"]("cancelado", None)
                return

            if descarga_realizada:
                self.cb["fin"]("descarga_completada", None)
                return

            self.cb["estado"]("Cargando modelo en memoria...")
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

        except (RuntimeError, MemoryError) as e:
            sys.stderr = original_stderr
            error_str = str(e)
            if (
                "mkl_malloc" in error_str.lower()
                or "memory" in error_str.lower()
                or "allocate" in error_str.lower()
            ):
                msj = "Error: Memoria RAM insuficiente.\nCierra otros programas o reduce hilos."
            else:
                msj = f"Error en el motor de IA:\n{error_str}"
            self.cb["error"](msj)
            self.cb["fin"]("error", None)

        except OSError as e:
            sys.stderr = original_stderr
            self.cb["error"](f"Error al leer/escribir archivos: {e!s}")
            self.cb["fin"]("error", None)

        except Exception as e:  # noqa: BLE001
            sys.stderr = original_stderr

            # Formatear el error para enviarlo al log de la interfaz
            error_detallado = f"Excepcion no controlada: {e!s}\n\nTraceback:\n{traceback.format_exc()}"
            self.cb["error"](error_detallado)
            self.cb["fin"]("error", None)

        finally:
            if "model" in locals():
                del model
            gc.collect()
