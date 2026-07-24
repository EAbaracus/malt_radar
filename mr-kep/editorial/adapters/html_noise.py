"""HTML noise reduction for editorial adapters.

The editorial adapters only need to *strip* script/style blocks and consent
banners before markdown tasting-note extraction. They never render the HTML, so
this is pure noise reduction — but a regex over HTML (``re.sub(r"<script.*?>",
...)``) is both fragile and flagged by security scanners as "bad HTML
filtering". Use a real parser instead.
"""

from html.parser import HTMLParser


class _NoiseStripper(HTMLParser):
    """Drop the *content* of <script>/<style> elements and keep everything else.

    We keep tag text (unlike a full HTML-to-text renderer) because the adapters
    operate on already-fairly-clean editorial HTML/markdown where the visible
    prose is what we want. Only the opaque script/style blocks are removed.
    """

    _VOID_DROP = {"script", "style"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self._drop_depth = 0
        self._out = []

    def handle_starttag(self, tag, attrs):
        if tag in self._VOID_DROP:
            self._drop_depth += 1
            return
        # Keep structural tags as plain text markers so layout is preserved.
        self._out.append(" ")

    def handle_endtag(self, tag):
        if tag in self._VOID_DROP and self._drop_depth > 0:
            self._drop_depth -= 1
            return
        self._out.append(" ")

    def handle_data(self, data):
        if self._drop_depth == 0:
            self._out.append(data)

    def handle_entityref(self, name):
        if self._drop_depth == 0:
            self._out.append(f"&{name};")

    def handle_charref(self, name):
        if self._drop_depth == 0:
            self._out.append(f"&#{name};")


def strip_html_noise(html: str) -> str:
    """Remove <script>/<style> block contents from an HTML string.

    Uses the stdlib HTMLParser (no regex over markup) so it is robust to
    attributes, newlines and nested tags, and does not trip "bad HTML
    filtering" static analysis.
    """
    if not html:
        return html
    p = _NoiseStripper()
    p.feed(html)
    return "".join(p._out)
