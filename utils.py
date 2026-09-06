import re
import unicodedata
from pathlib import Path


class Tiempo:
    def __init__(self, segundos):
        self.hora = int(segundos // 3600)
        self.minuto = int((segundos % 3600) // 60)
        self.segundo = int(segundos % 60)

    @property
    def marca_tiempo(self):
        return f"{self.hora:02d}:{self.minuto:02d}:{self.segundo:02d}"


def sanitizar_nombre(texto_original: str) -> str:
    nfkd = unicodedata.normalize("NFKD", texto_original)
    texto = "".join([c for c in nfkd if not unicodedata.combining(c)]).lower()
    texto = re.sub(r"[^\w\s]", "_", texto)
    texto = re.sub(r"\s+", "_", texto)
    return re.sub(r"_+", "_", texto).strip("_")


def acortar_ruta(ruta, max_len=45):
    """Acorta la ruta para que no rompa la interfaz si es muy larga."""
    if len(ruta) <= max_len:
        return ruta
    partes = Path(ruta).parts
    if len(partes) > 3:
        return f"{partes[0]}...\\{partes[-2]}\\{partes[-1]}"
    return f"...\\{ruta[-max_len:]}"


class InterceptorTerminal:
    def __init__(self, log_func, chequeo_aborto):
        self.log_func = log_func
        self.chequeo_aborto = chequeo_aborto

    def write(self, texto):
        if self.chequeo_aborto():
            raise InterruptedError("Descarga cancelada por el usuario.")

        limpio = texto.replace("\r", "").strip()
        if limpio and ("%" in limpio or "MB/s" in limpio or "it/s" in limpio):
            self.log_func(f"Descargando: {limpio.split()[-1]}")

    def flush(self):
        pass
