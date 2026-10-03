#!/usr/bin/env python3
"""
igdl.py - Descarga videos/reels de Instagram y videos de fichas de Alibaba.

Detecta el sitio por la URL y ajusta las opciones automáticamente. En ambos
casos el archivo se guarda en la carpeta de salida (por defecto ./downloads).

Uso:
    python igdl.py <url> [<url> ...]
    python igdl.py <url> -o ./descargas
    python igdl.py <url> -a                               # solo audio (.m4a)
    python igdl.py <url> --cookies-from-browser chrome   # si pide login
    python igdl.py "https://www.alibaba.com/product-detail/..._1601271126969.html"

Requisitos:
    pip install yt-dlp          # Alibaba además: pip install curl_cffi
"""

import argparse
import re
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("Falta yt-dlp. Instálalo con: pip install yt-dlp")


def is_alibaba(url: str) -> bool:
    return re.search(r"https?://(?:[\w-]+\.)?alibaba\.com/", url) is not None


def build_options(
    output_dir: Path,
    cookies_browser: str | None,
    quiet: bool,
    audio_only: bool,
    url: str,
) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    alibaba = is_alibaba(url)
    opts = {
        # Instagram: <usuario>_<id>.<ext>   Alibaba: <id-ficha>_<id-video>.<ext>
        "outtmpl": str(output_dir / (
            "%(display_id,id)s_%(id)s.%(ext)s" if alibaba
            else "%(uploader)s_%(id)s.%(ext)s"
        )),
        "noplaylist": True,
        "quiet": quiet,
        "no_warnings": quiet,
        "retries": 3,
    }
    if audio_only:
        # Solo audio, extraído a .m4a (AAC) sin re-codificar cuando ya es AAC.
        opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"
        opts["postprocessors"] = [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "m4a",
                "preferredquality": "0",  # mejor calidad disponible
            }
        ]
    elif alibaba:
        # Alibaba sirve un .mp4 ya muxeado; basta con la mejor calidad.
        opts["format"] = "bestvideo+bestaudio/best"
        opts["merge_output_format"] = "mp4"
        # Imita a Chrome (requiere curl_cffi) para evitar la página de captcha.
        try:
            from yt_dlp.networking.impersonate import ImpersonateTarget
            opts["impersonate"] = ImpersonateTarget.from_str("chrome")
        except Exception:
            pass  # sin curl_cffi se intenta igual; puede dar captcha
    else:
        # Instagram: prioriza video H.264 (avc1) + audio AAC para máxima
        # compatibilidad (QuickTime/Finder no reproducen VP9 dentro de .mp4).
        opts["format"] = (
            "bestvideo[vcodec^=avc1]+bestaudio[ext=m4a]/"
            "best[vcodec^=avc1]/"
            "bestvideo+bestaudio/best"
        )
        opts["merge_output_format"] = "mp4"
    if cookies_browser:
        # Usa la sesión ya iniciada en tu navegador (chrome, firefox, edge, brave...)
        opts["cookiesfrombrowser"] = (cookies_browser,)
    return opts


def download(
    urls: list[str],
    output_dir: Path,
    cookies_browser: str | None,
    quiet: bool,
    audio_only: bool,
) -> int:
    failed = 0
    for url in urls:
        # Opciones por URL: Instagram y Alibaba necesitan ajustes distintos.
        opts = build_options(output_dir, cookies_browser, quiet, audio_only, url)
        try:
            with yt_dlp.YoutubeDL(opts) as ydl:
                info = ydl.extract_info(url, download=True)
                # Tras postprocesado (p. ej. extracción a .m4a) la ruta final
                # está en requested_downloads; si no, se usa prepare_filename.
                downloads = info.get("requested_downloads") or []
                filename = downloads[0].get("filepath") if downloads else ydl.prepare_filename(info)
                print(f"✔ Descargado: {filename}")
        except yt_dlp.utils.DownloadError as e:
            failed += 1
            print(f"✘ Error con {url}: {e}", file=sys.stderr)
    return failed


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Descarga videos/reels de Instagram y videos de fichas de Alibaba.",
    )
    # Por defecto: carpeta downloads/ JUNTO AL SCRIPT (no al directorio actual),
    # así el video siempre cae dentro del proyecto desde donde se ejecute.
    default_output = Path(__file__).resolve().parent / "downloads"
    parser.add_argument("urls", nargs="+", help="Una o más URLs de Instagram o Alibaba")
    parser.add_argument(
        "-o", "--output", default=str(default_output),
        help="Carpeta destino (default: <proyecto>/downloads)",
    )
    parser.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Navegador del que tomar cookies (chrome, firefox, edge, brave). Necesario si el sitio exige login.",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Menos salida en consola")
    parser.add_argument(
        "-a", "--audio", action="store_true",
        help="Extraer solo el audio en formato .m4a (sin video)",
    )
    args = parser.parse_args()

    failed = download(
        args.urls, Path(args.output), args.cookies_from_browser, args.quiet, args.audio,
    )
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
