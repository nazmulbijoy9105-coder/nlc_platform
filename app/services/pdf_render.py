"""
NEUM LEX COUNSEL — shared HTML-to-PDF rendering
app/services/pdf_render.py

WeasyPrint fetches every URL it finds in the HTML or CSS (<img>, <link>,
url(...)), including file:// URLs, through its default fetcher. A company name
such as <link rel="attachment" href="file:///..."> is enough to make the
default fetcher embed a local file into the PDF. Tenant-supplied text (company
names, flag descriptions, document bodies) must therefore be escaped before it
is placed in HTML, and rendering must use a fetcher that refuses everything
except our own bundled brand assets (app/static/brand).

Written against WeasyPrint 70 (pinned in requirements.txt), where url_fetcher
must be a weasyprint.urls.URLFetcher instance, not a plain function.
"""
from __future__ import annotations

import asyncio
import html
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit
from urllib.request import url2pathname

# app/services/pdf_render.py -> app/static/brand
ASSET_DIR = (Path(__file__).resolve().parent.parent / "static" / "brand").resolve()


def esc(value: Any) -> str:
    """HTML-escape any value. None becomes "", Enums are rendered by .value."""
    if value is None:
        return ""
    return html.escape(str(getattr(value, "value", value)), quote=True)


def safe_filename_part(value: Any, fallback: str = "company") -> str:
    """Reduce a user-supplied string to characters that are safe in a filename."""
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", str(value or "")).strip("._-")
    return cleaned[:60] or fallback


def asset_uri(name: str) -> str | None:
    """file:// URI of a bundled brand asset, or None if it is missing or not directly in ASSET_DIR."""
    path = (ASSET_DIR / name).resolve()
    if path.parent != ASSET_DIR or not path.is_file():
        return None
    return path.as_uri()


def make_safe_fetcher():
    """A WeasyPrint URLFetcher that serves files from ASSET_DIR and refuses everything else.

    Refused resources (other file paths, http, https, data, ...) are logged by
    WeasyPrint as warnings and skipped; the render itself continues.
    """
    from weasyprint.urls import URLFetcher

    class AssetOnlyFetcher(URLFetcher):
        def fetch(self, url, headers=None):
            parts = urlsplit(url)
            if parts.scheme.lower() != "file" or parts.netloc not in ("", "localhost"):
                raise ValueError("External resource blocked")
            path = Path(url2pathname(parts.path)).resolve()
            if path.parent != ASSET_DIR:
                raise ValueError("Resource outside the brand asset directory blocked")
            return super().fetch(url, headers)

    return AssetOnlyFetcher(allowed_protocols=("file",))


def render_html_to_pdf(html_content: str) -> bytes:
    """Render an HTML string to PDF bytes. Only app/static/brand files can be loaded."""
    from weasyprint import HTML  # imported lazily: pulls in Pango/Cairo

    return HTML(string=html_content, url_fetcher=make_safe_fetcher()).write_pdf()


async def render_html_to_pdf_async(html_content: str) -> bytes:
    """Run the CPU-bound render in a worker thread so the event loop stays free."""
    return await asyncio.to_thread(render_html_to_pdf, html_content)
