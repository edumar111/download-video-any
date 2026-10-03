# Instalación del plugin `alibaba:robust` para yt-dlp

Plugin que reemplaza al extractor interno de yt-dlp para fichas de producto de **alibaba.com**, con fallbacks ante cambios de layout, detección de captcha y soporte para varios videos por ficha.

---

## 1. Requisitos

| Componente | Versión mínima | Para qué |
|---|---|---|
| Python | 3.9+ | Ejecutar yt-dlp |
| yt-dlp | 2025.12.08+ | Motor de descarga |
| curl_cffi | última | `--impersonate chrome` (evita el captcha de Alibaba) |
| ffmpeg | cualquiera reciente | Solo si vas a recortar/convertir; Alibaba sirve MP4 ya muxeado |

Instalación en un solo paso:

```bash
pip install -U "yt-dlp[default,curl-cffi]"
```

Verifica:

```bash
yt-dlp --version
python -c "import curl_cffi; print('curl_cffi OK')"
```

> **Windows:** si `pip` no está en el PATH usa `py -m pip install -U "yt-dlp[default,curl-cffi]"`.

---

## 2. Estructura del plugin

El archivo debe quedar dentro de esta jerarquía exacta (yt-dlp la exige para descubrir plugins):

```
yt_dlp_plugins/
└── extractor/
    └── alibaba_robust.py
```

No hace falta `__init__.py`: yt-dlp usa *namespace packages*.

---

## 3. Dónde colocarlo

yt-dlp busca la carpeta `yt_dlp_plugins/` en varias rutas. Elige **una**.

### Opción A — Global para el usuario (recomendada)

| Sistema | Ruta |
|---|---|
| Linux / macOS | `~/.config/yt-dlp/plugins/alibaba_robust/yt_dlp_plugins/extractor/alibaba_robust.py` |
| Windows | `%APPDATA%\yt-dlp\plugins\alibaba_robust\yt_dlp_plugins\extractor\alibaba_robust.py` |

```bash
# Linux / macOS
mkdir -p ~/.config/yt-dlp/plugins/alibaba_robust/yt_dlp_plugins/extractor
cp alibaba_robust.py ~/.config/yt-dlp/plugins/alibaba_robust/yt_dlp_plugins/extractor/
```

```powershell
# Windows (PowerShell)
$dst = "$env:APPDATA\yt-dlp\plugins\alibaba_robust\yt_dlp_plugins\extractor"
New-Item -ItemType Directory -Force $dst | Out-Null
Copy-Item alibaba_robust.py $dst
```

### Opción B — Junto a tu proyecto

Deja la carpeta `yt_dlp_plugins/` en el directorio desde donde ejecutas `yt-dlp` o tu script Python. Útil para un backend (FastAPI, Spring Boot llamando a subproceso, Docker).

### Opción C — Como paquete pip (para distribuirlo)

Crea un `pyproject.toml` mínimo con el paquete `yt_dlp_plugins.extractor` y publícalo o instálalo con `pip install -e .`. yt-dlp lo detecta automáticamente desde `site-packages`.

---

## 4. Verificar que cargó

```bash
yt-dlp -v "https://www.alibaba.com/product-detail/Kids-Entertainment-Bouncer-Bouncy-Castle-Waterslide_1601271126969.html" --skip-download
```

En la salida verbose debes ver:

```
[debug] Extractor Plugins: AlibabaRobustIE (alibaba_robust)
[alibaba:robust] 1601271126969: Downloading webpage
```

Si aparece `[Alibaba]` en lugar de `[alibaba:robust]`, el plugin no está en una ruta reconocida. Lista las rutas que yt-dlp revisa con:

```bash
yt-dlp -v 2>&1 | grep -i plugin
```

---

## 5. Configuración recomendada (opcional)

Para no repetir flags, crea un archivo de configuración:

| Sistema | Ruta |
|---|---|
| Linux / macOS | `~/.config/yt-dlp/config` |
| Windows | `%APPDATA%\yt-dlp\config` |

Contenido sugerido:

```
# Evita el captcha "punish" de Alibaba
--impersonate chrome

# Carpeta y nombre de salida
-o "~/Videos/alibaba/%(display_id)s_%(id)s_%(format_id)s.%(ext)s"

# Reintentos ante cortes del CDN
--retries 5
--fragment-retries 5

# Solo el video principal por defecto (usa --yes-playlist para todos)
--no-playlist
```

---

## 6. Docker (backend)

```dockerfile
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends ffmpeg && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir "yt-dlp[default,curl-cffi]"
WORKDIR /app
COPY yt_dlp_plugins/ /app/yt_dlp_plugins/
ENTRYPOINT ["yt-dlp", "--impersonate", "chrome"]
```

```bash
docker build -t alibaba-dl .
docker run --rm -v "$PWD/out:/app/out" alibaba-dl -o "/app/out/%(id)s.%(ext)s" "<URL>"
```

---

## 7. Actualización

```bash
pip install -U "yt-dlp[default,curl-cffi]"
# y reemplaza alibaba_robust.py por la nueva versión en la misma ruta
```

Tras actualizar yt-dlp, corre el test del extractor para confirmar que el layout de Alibaba no cambió:

```bash
python -m pytest --pyargs yt_dlp.test.test_download -k AlibabaRobust   # si tienes el repo de yt-dlp
# o simplemente:
yt-dlp -J "<URL de prueba>" > /dev/null && echo OK
```

---

## 8. Solución de problemas

| Síntoma | Causa | Solución |
|---|---|---|
| `Alibaba devolvió una página de verificación (captcha)` | IP marcada o TLS detectado | `--impersonate chrome`; si persiste `--cookies-from-browser chrome` o cambiar de IP/proxy |
| `Impersonate target "chrome" is not available` | Falta `curl_cffi` | `pip install curl_cffi` |
| `No se encontró información de video en la ficha` | Layout nuevo y fallback regex sin resultados | Abre un issue con la URL; guarda el HTML con `--write-pages` para analizarlo |
| `La ficha no tiene video` | El producto solo tiene imágenes | Nada que descargar |
| Aparece `[Alibaba]` y no `[alibaba:robust]` | Plugin fuera de ruta | Revisa sección 3 y 4 |
| Descarga lenta o cortada | CDN de Alibaba | `--retries 10 -N 4` (descarga concurrente por fragmentos) |
