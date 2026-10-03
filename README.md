# igdl — Instagram Video Downloader

Script de línea de comandos en Python para descargar videos y reels de Instagram a partir de su URL. Usa [yt-dlp](https://github.com/yt-dlp/yt-dlp) por debajo.

## Requisitos

- Python 3.10 o superior
- `ffmpeg` instalado y en el PATH (necesario para unir video y audio)
  - Windows: `winget install ffmpeg` o descargar desde https://ffmpeg.org
  - macOS: `brew install ffmpeg`
  - Ubuntu/Debian: `sudo apt install ffmpeg`

## Instalación

```bash
git clone <tu-repo> igdl
cd igdl
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install yt-dlp
```

## Uso básico

```bash
python igdl.py https://www.instagram.com/reel/XXXXXXXXXXX/
```

El archivo se guarda en `./downloads/` con el nombre `<usuario>_<id>.mp4`.

### Varias URLs a la vez

```bash
python igdl.py https://www.instagram.com/reel/AAA/ https://www.instagram.com/p/BBB/
```

### Cambiar la carpeta de destino

```bash
python igdl.py <url> -o ~/Videos/instagram
```

### Solo audio (.m4a)

Descarga únicamente la pista de audio y la guarda como `<usuario>_<id>.m4a`:

```bash
python igdl.py <url> -a
# o
python igdl.py <url> --audio
```

Si el audio ya viene en AAC (lo habitual en Instagram) no se re-codifica, así que es rápido y sin pérdida de calidad.

### Modo silencioso

```bash
python igdl.py <url> -q
```

## Si Instagram pide iniciar sesión

Instagram suele exigir una sesión activa para servir videos, incluso públicos. Si ves errores como `login required`, `rate-limit reached` o `This content isn't available`, usa las cookies del navegador donde ya tengas la sesión iniciada:

```bash
python igdl.py <url> --cookies-from-browser chrome
```

Navegadores soportados: `chrome`, `chromium`, `firefox`, `edge`, `brave`, `opera`, `safari`.

> **Nota (Windows + Chrome):** Chrome bloquea su base de datos de cookies mientras está abierto. Ciérralo antes de ejecutar el script, o usa Firefox, que no tiene ese problema.

## Opciones

| Opción | Descripción | Default |
|---|---|---|
| `urls` | Una o más URLs de Instagram | — |
| `-o`, `--output` | Carpeta de destino | `downloads` |
| `--cookies-from-browser BROWSER` | Navegador del que tomar las cookies de sesión | ninguno |
| `-a`, `--audio` | Extrae solo el audio en formato `.m4a` (sin video) | off |
| `-q`, `--quiet` | Reduce la salida en consola | off |
| `-h`, `--help` | Muestra la ayuda | — |

## Códigos de salida

- `0`: todas las descargas fueron exitosas
- `1`: al menos una URL falló (el detalle se imprime en `stderr`)

## Solución de problemas

**`Falta yt-dlp`**
Instala la dependencia: `pip install yt-dlp`.

**`ffmpeg not found` / el archivo se descarga sin audio**
Instala `ffmpeg` y verifica con `ffmpeg -version`.

**El video se reproduce pero solo se oye el audio (pantalla negra)**
Suele ser un video en códec VP9 dentro de `.mp4`, que QuickTime/Finder de macOS no reproducen. El script ya prioriza H.264 (avc1) para evitarlo. Si tienes un archivo antiguo así, re-codifícalo:
`ffmpeg -i entrada.mp4 -c:v libx264 -c:a copy -movflags +faststart salida.mp4`

**Errores extraños o descargas que antes funcionaban y ya no**
Instagram cambia su sitio con frecuencia. Actualiza yt-dlp: `pip install -U yt-dlp`.

**Contenido privado**
Solo se puede descargar si tu cuenta tiene acceso al perfil; usa `--cookies-from-browser`.

## Aviso

Este script es para uso personal. Los términos de uso de Instagram no permiten descargar contenido de terceros sin autorización, y el contenido descargado sigue siendo propiedad de quien lo publicó. Pide permiso antes de republicarlo.

## Licencia

MIT
