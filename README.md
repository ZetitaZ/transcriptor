# Transcriptor Inteligente de Audio y Video

Aplicación de escritorio de código abierto para transcribir archivos de audio y video a texto utilizando modelos de inteligencia artificial de forma local.

La aplicación está pensada para ser sencilla de utilizar y no depender de servicios externos para realizar las transcripciones. Una vez descargado el modelo necesario, el procesamiento puede realizarse sin conexión a Internet.

## Características

- **Procesamiento local:** los archivos de audio y video se procesan directamente en el equipo, sin enviarlos a servidores externos.
- **Selección de modelos:** permite elegir entre un modelo orientado a obtener una mayor velocidad de procesamiento y otro orientado a obtener una mayor precisión.
- **Descarga automática de modelos:** los modelos no se incluyen directamente en el ejecutable. Se descargan automáticamente la primera vez que se utilizan y quedan disponibles para las siguientes transcripciones.
- **Versión portable:** la aplicación se distribuye como un ejecutable compilado, por lo que no es necesario instalar Python ni utilizar la consola para ejecutarla.
- **Registro de errores:** si ocurre algún problema durante la ejecución, la aplicación intenta capturar el error y generar un archivo `error_log.txt` con información que permita identificar qué ocurrió.

## Instalación y uso

La aplicación cuenta con una versión portable para usuarios que solamente quieran utilizarla sin configurar el entorno de desarrollo.

1. Ve a la sección **Releases** de este repositorio.
2. Descarga el archivo `.zip` correspondiente a la versión más reciente.
3. Extrae el contenido del archivo en tu computadora.
4. Ejecuta `Transcriptor.exe`.
5. Arrastra el archivo de audio o video hacia la ventana de la aplicación.
6. Selecciona el modelo que quieras utilizar e inicia la transcripción.

La primera vez que utilices un modelo, este se descargará automáticamente. Por este motivo, se requiere conexión a Internet durante esa primera descarga.

## Compilación

Si quieres modificar el código fuente o generar tu propia versión del ejecutable, primero debes clonar el repositorio e instalar las dependencias necesarias.

Se recomienda utilizar un entorno virtual de Python para mantener las dependencias del proyecto separadas de las demás instalaciones de Python del equipo.

Para ejecutar la aplicación directamente desde el código fuente:

```bash
python main.py
```

Para generar el ejecutable utilizando PyInstaller:

```bash
python -m PyInstaller --noconfirm --noconsole --onedir --name "Transcriptor" --icon "icono.ico" --collect-data tkinterdnd2 main.py
```

## Autoría y créditos

El proyecto fue ideado, estructurado y desarrollado por **LEANDRO EZEQUIEL SOLORZANO ARANIBAR**.

Durante el desarrollo se utilizó asistencia de herramientas de inteligencia artificial para tareas relacionadas con programación, resolución de problemas y revisión de código. La estructura del proyecto, su lógica y las decisiones de implementación fueron realizadas como parte del desarrollo del proyecto.

El motor de transcripción utilizado es [faster-whisper](https://github.com/SYSTRAN/faster-whisper).

## Licencia

Este proyecto se distribuye bajo la licencia **GNU GPL v3.0**.

Puedes utilizar, estudiar y modificar el software de acuerdo con los términos establecidos por esta licencia. Para consultar las condiciones completas, revisa el archivo `LICENSE` incluido en el repositorio.
