#!/usr/bin/env python3
"""
igdl.py - Descarga videos/reels de Instagram a partir de su URL.

Uso:
    python igdl.py <url> [<url> ...]
    python igdl.py <url> -o ./descargas
    python igdl.py <url> -a                               # solo audio (.m4a)
    python igdl.py <url> --cookies-from-browser chrome   # si Instagram pide login

Requisitos:
    pip install yt-dlp
"""

import argparse
import sys
from pathlib import Path

try:
    import yt_dlp
except ImportError:
    sys.exit("Falta yt-dlp. Instálalo con: pip install yt-dlp")


def build_options(output_dir: Path, cookies_browser: str | None, quiet: bool, audio_only: bool) -> dict:
    output_dir.mkdir(parents=True, exist_ok=True)
    opts = {
        # Nombre: <usuario>_<id>.<ext>
        "outtmpl": str(output_dir / "%(uploader)s_%(id)s.%(ext)s"),
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
    else:
        # Prioriza video H.264 (avc1) + audio AAC para máxima compatibilidad
        # (QuickTime/Finder no reproducen VP9 dentro de .mp4).
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


def download(urls: list[str], opts: dict) -> int:
    failed = 0
    with yt_dlp.YoutubeDL(opts) as ydl:
        for url in urls:
            try:
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
    parser = argparse.ArgumentParser(description="Descarga videos/reels de Instagram.")
    parser.add_argument("urls", nargs="+", help="Una o más URLs de Instagram")
    parser.add_argument("-o", "--output", default="downloads", help="Carpeta destino (default: downloads)")
    parser.add_argument(
        "--cookies-from-browser",
        metavar="BROWSER",
        help="Navegador del que tomar cookies (chrome, firefox, edge, brave). Necesario si Instagram exige login.",
    )
    parser.add_argument("-q", "--quiet", action="store_true", help="Menos salida en consola")
    parser.add_argument(
        "-a", "--audio", action="store_true",
        help="Extraer solo el audio en formato .m4a (sin video)",
    )
    args = parser.parse_args()

    opts = build_options(Path(args.output), args.cookies_from_browser, args.quiet, args.audio)
    failed = download(args.urls, opts)
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
