"""
Plugin de yt-dlp: extractor robusto para fichas de producto de alibaba.com.

Instalación (cualquiera de las dos):
  - copiar la carpeta yt_dlp_plugins/ junto al script que usa yt-dlp, o
  - ~/.config/yt-dlp/plugins/alibaba_robust/yt_dlp_plugins/extractor/alibaba_robust.py

Uso:
  yt-dlp "https://www.alibaba.com/product-detail/Foo_1601271126969.html"
  yt-dlp --impersonate chrome ...            # si Alibaba devuelve la página "punish"
  yt-dlp --cookies-from-browser chrome ...   # idem, con sesión real
  yt-dlp -J URL | jq .                       # solo metadatos + formatos (modo API)
  yt-dlp --yes-playlist URL                  # baja también videos de empresa/SKU

Los plugins se cargan ANTES que los extractores internos, así que este reemplaza
al AlibabaIE de serie para las URLs que matchea.
"""
import json
import re

from yt_dlp.extractor.common import InfoExtractor
from yt_dlp.utils import (
    ExtractorError,
    int_or_none,
    str_or_none,
    url_or_none,
)
from yt_dlp.utils.traversal import traverse_obj


class AlibabaRobustIE(InfoExtractor):
    IE_NAME = 'alibaba:robust'
    _VALID_URL = r'''(?x)
        https?://(?:(?:www|m|spanish|es|french)\.)?alibaba\.com/
        (?:product-detail|product)/
        # Prefijo opcional del slug: "Nombre-Producto_", "subject-", etc.
        (?:[^/?#]*?[-_])?(?P<id>\d{8,})(?:\.html)?
    '''
    _TESTS = [{
        'url': 'https://www.alibaba.com/product-detail/Kids-Entertainment-Bouncer-Bouncy-Castle-Waterslide_1601271126969.html',
        'info_dict': {
            'id': '6000280444270',
            'display_id': '1601271126969',
            'ext': 'mp4',
            'title': str,
            'duration': int,
        },
    }]

    # Frases que aparecen en la página de verificación/captcha de Alibaba
    _PUNISH_MARKERS = ('punish', 'Verify yourself', 'slide to verify', '_____tmd_____', 'x5secdata')

    # ------------------------------------------------------------------ helpers
    def _fetch_webpage(self, url, display_id):
        """Descarga la ficha; detecta captcha y da pistas accionables."""
        webpage, urlh = self._download_webpage_handle(
            url, display_id, headers={'Accept-Language': 'en-US,en;q=0.9'})
        final_url = urlh.url
        if any(m in webpage for m in self._PUNISH_MARKERS) or '/punish' in final_url:
            raise ExtractorError(
                'Alibaba devolvió una página de verificación (captcha). '
                'Prueba con --impersonate chrome (requiere curl_cffi), '
                '--cookies-from-browser <navegador> o cambia de IP/proxy.',
                expected=True)
        return webpage, final_url

    def _extract_product(self, webpage, display_id):
        """Cadena de fallbacks para encontrar el JSON del producto."""
        # 1) Formato actual
        data = self._search_json(
            r'window\.detailData\s*=', webpage, 'detailData', display_id,
            default=None, fatal=False)
        product = traverse_obj(data, ('globalData', 'product', {dict}))
        if product:
            return product
        # 2) Variantes históricas / móviles
        for name in ('__INITIAL_DATA__', '__NEXT_DATA__', 'detailPageData', 'pageData'):
            data = self._search_json(
                rf'(?:window\.)?{re.escape(name)}\s*=', webpage, name, display_id,
                default=None, fatal=False)
            product = traverse_obj(data, (..., 'product', {dict}), get_all=False)
            if product:
                return product
        return None

    def _formats_from_media(self, media):
        """mediaItem['videoUrl'] es una lista de definiciones -> formats de yt-dlp."""
        return traverse_obj(media, ('videoUrl', lambda _, v: url_or_none(v['videoUrl']), {
            'url': 'videoUrl',
            'format_id': ('definition', {str_or_none}),
            'tbr': ('bitrate', {int_or_none}),
            'width': ('width', {int_or_none}),
            'height': ('height', {int_or_none}),
            'filesize': ('length', {int_or_none}),
            'ext': {lambda _: 'mp4'},
        }))

    def _entry(self, media, title, display_id, suffix=''):
        formats = self._formats_from_media(media)
        if not formats:
            return None
        return {
            'id': str_or_none(media.get('videoId')) or f'{display_id}{suffix}',
            'display_id': display_id,
            'title': f'{title}{suffix}',
            'duration': int_or_none(media.get('duration')),
            'thumbnail': url_or_none(media.get('videoCoverUrl')),
            'formats': formats,
        }

    def _regex_fallback(self, webpage, display_id, title):
        """Último recurso: cualquier .mp4 de los CDNs de Alibaba en el HTML."""
        urls = re.findall(
            r'https?://(?:cloud\.video\.taobao\.com|[\w.-]*alicdn\.com)/[^"\'\s\\]+\.mp4[^"\'\s\\]*',
            webpage)
        urls = list(dict.fromkeys(u.replace('\\/', '/') for u in urls))
        if not urls:
            return None
        return {
            'id': display_id,
            'display_id': display_id,
            'title': title,
            'formats': [{'url': u, 'format_id': f'fallback{i}', 'ext': 'mp4'} for i, u in enumerate(urls)],
        }

    # -------------------------------------------------------------- main entry
    def _real_extract(self, url):
        display_id = self._match_id(url)
        # Normaliza m./spanish./es. -> www. para obtener siempre el mismo layout
        canonical = f'https://www.alibaba.com/product-detail/_{display_id}.html'
        webpage, _ = self._fetch_webpage(canonical, display_id)

        product = self._extract_product(webpage, display_id)
        title = (traverse_obj(product, ('subject', {str}))
                 or self._og_search_title(webpage, default=None)
                 or display_id)

        if not product:
            entry = self._regex_fallback(webpage, display_id, title)
            if entry:
                self.report_warning('Layout desconocido: usando fallback por regex')
                return entry
            raise ExtractorError('No se encontró información de video en la ficha', expected=True)

        entries = []
        # Video principal
        for media in traverse_obj(product, ('mediaItems', lambda _, v: v['type'] == 'video')):
            e = self._entry(media, title, display_id)
            if e:
                entries.append(e)
        # Videos de empresa / SKU (si existen en el payload)
        for i, media in enumerate(traverse_obj(product, (('companyVideos', 'skuVideos'), ..., {dict}))):
            e = self._entry(media, title, display_id, suffix=f' (extra {i + 1})')
            if e:
                entries.append(e)

        if not entries:
            entry = self._regex_fallback(webpage, display_id, title)
            if entry:
                return entry
            raise ExtractorError('La ficha no tiene video', expected=True)

        if len(entries) == 1 or self._downloader.params.get('noplaylist'):
            return entries[0]
        return self.playlist_result(entries, display_id, title)
