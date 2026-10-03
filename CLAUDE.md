# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Qué es este repo

Dos herramientas independientes construidas sobre [yt-dlp](https://github.com/yt-dlp/yt-dlp):

1. **`igdl.py`** — CLI para descargar reels/videos de Instagram.
2. **`plugins/alibaba_robust.py`** — plugin extractor de yt-dlp para fichas de producto de alibaba.com. No lo usa `igdl.py`; es una herramienta aparte que se instala dentro de yt-dlp.

No hay suite de tests, build ni gestor de dependencias (no hay `requirements.txt`/`pyproject.toml`). La única dependencia de ejecución es `yt-dlp`, y `ffmpeg` en el PATH para muxear/extraer audio.

## Comandos

```bash
# Instalar dependencia
pip install -U yt-dlp            # ffmpeg aparte: brew install ffmpeg (macOS)

# Ejecutar el descargador de Instagram
python igdl.py <url>             # video H.264 + audio -> downloads/<usuario>_<id>.mp4
python igdl.py <url> -a          # solo audio -> .m4a
python igdl.py <url> -o <dir>    # carpeta destino
python igdl.py <url> --cookies-from-browser chrome   # si Instagram exige login

# Verificar un cambio sin tests: comprobar que compila + inspeccionar el resultado
python -m py_compile igdl.py
ffprobe -v error -show_entries stream=codec_type,codec_name -of default=noprint_wrappers=1 <archivo>
```

## Arquitectura de `igdl.py`

Flujo lineal en tres funciones: `build_options()` arma el dict de opciones de yt-dlp, `download()` itera las URLs sobre una sola instancia de `YoutubeDL`, y `main()` parsea argumentos. Toda la lógica de negocio vive en el selector de `format` de `build_options()`.

Decisiones clave (no revertir sin entender el porqué):

- **El selector de formato prioriza H.264 (`vcodec^=avc1`), no "mejor calidad".** Instagram a veces sirve video VP9; VP9 dentro de `.mp4` no lo reproducen QuickTime ni el Finder de macOS (se oye el audio, pantalla negra). Forzar avc1 evita ese fallo. El fallback a `bestvideo+bestaudio/best` solo entra si no hay avc1 disponible.
- **El modo audio (`-a`) usa el postprocesador `FFmpegExtractAudio` a m4a con `preferredquality: "0"`.** Como Instagram ya entrega AAC, en la práctica no re-codifica (sin pérdida). Por eso `download()` lee la ruta final desde `info["requested_downloads"][0]["filepath"]` en vez de `prepare_filename()`: tras el postprocesado la extensión cambia a `.m4a`.

## El plugin de Alibaba (`plugins/`)

`alibaba_robust.py` define `AlibabaRobustIE`, que **reemplaza** al `AlibabaIE` interno de yt-dlp (los plugins cargan antes que los extractores de serie). No se ejecuta desde este repo: hay que copiarlo a la jerarquía `yt_dlp_plugins/extractor/` que yt-dlp descubre (ver `plugins/instalacion-plugin.md`). Requiere `yt-dlp[curl-cffi]` para `--impersonate chrome`, que es lo que sortea la página de captcha ("punish") de Alibaba.

El extractor está diseñado para sobrevivir cambios de layout mediante una cadena de fallbacks en `_extract_product()`: intenta `window.detailData`, luego varias claves JSON históricas (`__INITIAL_DATA__`, `__NEXT_DATA__`, …), y como último recurso `_regex_fallback()` busca cualquier `.mp4` de los CDNs de Alibaba en el HTML crudo. Al tocar este archivo, mantén esa degradación progresiva: un layout nuevo debe caer al siguiente fallback, no romper.

Documentación de uso en `plugins/Alibaba.md` e instalación en `plugins/instalacion-plugin.md`.

## Notas

- `downloads/` está en `.gitignore` junto con los artefactos de media (`*.mp4`, `*.m4a`, etc.); no commitear descargas.
- Mensajes al usuario, docstrings y comentarios van en español (incluidos los mensajes de error de yt-dlp que lanza el plugin).
