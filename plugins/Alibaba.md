# Uso: descargar videos de Alibaba con yt-dlp + plugin `alibaba:robust`

Guía práctica para usar el extractor desde la terminal, desde Python y desde un backend. Asume que seguiste `instalacion-plugin.md`.

---

## 1. URLs soportadas

El plugin reconoce cualquiera de estas formas y las normaliza a `www.alibaba.com`:

```
https://www.alibaba.com/product-detail/Nombre-Del-Producto_1601271126969.html
https://m.alibaba.com/product/1601271126969.html
https://spanish.alibaba.com/product-detail/..._1601271126969.html
https://es.alibaba.com/product-detail/..._1601271126969.html
```

Lo único que importa es el **ID numérico** (10+ dígitos) al final de la URL.

> Los enlaces cortos que genera la app (`alibaba.com/x/...`, `s.alibaba.com/...`) no se resuelven aún. Ábrelos en el navegador y copia la URL final.

---

## 2. Uso básico (CLI)

### Descargar el video principal en la mejor calidad

```bash
yt-dlp --impersonate chrome "https://www.alibaba.com/product-detail/Kids-Entertainment-Bouncer-Bouncy-Castle-Waterslide_1601271126969.html"
```

Resultado típico:

```
[alibaba:robust] 1601271126969: Downloading webpage
[info] 6000280444270: Downloading 1 format(s): hd
[download] Destination: Kids Entertainment Bouncer Bouncy Castle Waterslide [6000280444270].mp4
[download] 100% of 4.21MiB in 00:00:02
```

### Ver las calidades disponibles sin descargar

```bash
yt-dlp --impersonate chrome -F "<URL>"
```

```
ID   EXT RESOLUTION │  FILESIZE  TBR
ld   mp4 480x480    │  1.10MiB  290k
sd   mp4 720x720    │  2.35MiB  620k
hd   mp4 1080x1080  │  4.21MiB 1120k
```

### Elegir una calidad concreta

```bash
yt-dlp --impersonate chrome -f sd "<URL>"          # por format_id
yt-dlp --impersonate chrome -f "best[height<=720]" "<URL>"
yt-dlp --impersonate chrome -f worst "<URL>"       # la más liviana
```

### Descargar varios productos

```bash
yt-dlp --impersonate chrome "<URL1>" "<URL2>" "<URL3>"
# o desde un archivo con una URL por línea
yt-dlp --impersonate chrome -a urls.txt
```

### Nombre y carpeta de salida

```bash
yt-dlp --impersonate chrome \
  -o "~/Videos/alibaba/%(display_id)s_%(format_id)s.%(ext)s" "<URL>"
```

Variables útiles: `%(display_id)s` (ID del producto), `%(id)s` (ID del video), `%(title)s`, `%(format_id)s`, `%(height)s`.

---

## 3. Varios videos por ficha

Algunas fichas incluyen, además del video principal, videos de empresa o por SKU. El plugin los expone como *playlist*.

```bash
# Solo el principal (por defecto si configuraste --no-playlist)
yt-dlp --impersonate chrome --no-playlist "<URL>"

# Todos los videos de la ficha
yt-dlp --impersonate chrome --yes-playlist "<URL>"

# Numerarlos
yt-dlp --impersonate chrome --yes-playlist \
  -o "%(display_id)s_%(playlist_index)02d.%(ext)s" "<URL>"
```

---

## 4. Modo API: solo metadatos (JSON)

Para una web o backend lo normal es **no descargar en el servidor**: obtienes las URLs del CDN y el navegador del usuario descarga directo.

```bash
yt-dlp --impersonate chrome -J "<URL>" > producto.json
```

Campos relevantes del JSON:

```json
{
  "id": "6000280444270",
  "display_id": "1601271126969",
  "title": "Kids Entertainment Bouncer ...",
  "duration": 30,
  "thumbnail": "https://sc04.alicdn.com/kf/....jpg",
  "formats": [
    { "format_id": "ld", "url": "https://cloud.video.taobao.com/.../ld.mp4", "width": 480, "height": 480, "tbr": 290, "filesize": 1153433 },
    { "format_id": "sd", "url": "...", "width": 720, "height": 720 },
    { "format_id": "hd", "url": "...", "width": 1080, "height": 1080 }
  ]
}
```

Extraer solo la URL de la mejor calidad:

```bash
yt-dlp --impersonate chrome -g "<URL>"
```

---

## 5. Uso desde Python

```python
import yt_dlp

OPTS = {
    "impersonate": yt_dlp.networking.impersonate.ImpersonateTarget("chrome"),
    "noplaylist": True,
    "quiet": True,
}

def resolve(url: str) -> dict:
    """Devuelve título, miniatura y formatos sin descargar nada."""
    with yt_dlp.YoutubeDL(OPTS) as ydl:
        info = ydl.extract_info(url, download=False)
    return {
        "title": info["title"],
        "thumbnail": info.get("thumbnail"),
        "formats": [
            {"id": f["format_id"], "url": f["url"], "height": f.get("height"), "size": f.get("filesize")}
            for f in info["formats"]
        ],
    }

def download(url: str, out_dir: str = "downloads") -> str:
    opts = {**OPTS, "outtmpl": f"{out_dir}/%(display_id)s_%(format_id)s.%(ext)s", "quiet": False}
    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        return info["requested_downloads"][0]["filepath"]
```

Recuerda tener la carpeta `yt_dlp_plugins/` en el directorio de trabajo o en la ruta global del usuario.

---

## 6. Uso desde un backend Java / Spring Boot

Llama a yt-dlp por subproceso en modo JSON; es la integración más estable (no dependes de bindings).

```java
ProcessBuilder pb = new ProcessBuilder(
    "yt-dlp", "--impersonate", "chrome", "--no-playlist", "-J", url);
pb.redirectErrorStream(false);
Process p = pb.start();
String json = new String(p.getInputStream().readAllBytes(), StandardCharsets.UTF_8);
if (p.waitFor() != 0) throw new IllegalStateException(new String(p.getErrorStream().readAllBytes()));
JsonNode info = objectMapper.readTree(json);   // info.get("formats") -> lista de URLs
```

Recomendaciones para producción:

- **Caché** por `display_id` (Redis, TTL 1-6 h): las URLs del CDN de Alibaba son públicas y estables.
- **Cola** (una o pocas peticiones concurrentes por IP) para no disparar el captcha.
- **Timeout** de 30-60 s por subproceso y reintento único.
- Devuelve al frontend las URLs del CDN y deja que el navegador descargue; no hagas proxy del video salvo que necesites recortar/convertir.

---

## 7. Problemas frecuentes

| Mensaje / síntoma | Qué hacer |
|---|---|
| `Alibaba devolvió una página de verificación (captcha)` | Asegura `--impersonate chrome`. Si sigue: `--cookies-from-browser chrome` (o firefox/edge/brave) o cambia de IP. Espera unos minutos antes de reintentar. |
| `Layout desconocido: usando fallback por regex` | Funciona pero Alibaba cambió el HTML. Guarda la página con `--write-pages` y reporta para actualizar el plugin. |
| `La ficha no tiene video` | El producto solo tiene fotos. |
| Video descargado con nombre raro | Usa `-o` con `%(display_id)s` en vez de `%(title)s` (los títulos de Alibaba son muy largos). |
| Quiero solo el audio | `yt-dlp --impersonate chrome -x --audio-format m4a "<URL>"` (requiere ffmpeg). |
| Quiero un recorte | `yt-dlp --impersonate chrome --download-sections "*00:05-00:15" "<URL>"` (requiere ffmpeg). |
| Quiero la miniatura | `yt-dlp --impersonate chrome --write-thumbnail --skip-download "<URL>"`. |

---

## 8. Consideraciones de uso

Los videos pertenecen a los proveedores que los publican en Alibaba. Descargarlos para referencia personal, análisis de producto o respaldo es un uso de bajo riesgo; republicarlos, monetizarlos o usarlos como propios en tu tienda sin permiso del proveedor va contra los términos de Alibaba y la ley de derechos de autor. Si ofreces esto como servicio, inclúyelo en tus propios términos de uso.
