#!/usr/bin/env python3
"""Une plantilla.html + datos.json + nota.json en docs/index.html (la página web)."""
from pathlib import Path
c = Path(__file__).resolve().parent
seguro = lambda t: t.replace("</", "<\\/")
cuerpo = (c / "plantilla.html").read_text(encoding="utf-8")
cuerpo = cuerpo.replace("__DATOS__", seguro((c / "datos.json").read_text(encoding="utf-8")))
cuerpo = cuerpo.replace("__NOTA__", seguro((c / "nota.json").read_text(encoding="utf-8")))
html = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
        '<meta name="robots" content="noindex">'
        '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
        'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
        '</head><body>' + cuerpo + '</body></html>')
salida = c.parent / "docs" / "index.html"
salida.write_text(html, encoding="utf-8")
print("docs/index.html lista,", len(html) // 1024, "KB")
