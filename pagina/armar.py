#!/usr/bin/env python3
"""Arma docs/index.html (la página) y los calendarios docs/fechas*.ics."""
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

C = Path(__file__).resolve().parent
DOCS = C.parent / "docs"
seguro = lambda t: t.replace("</", "<\\/")


def leer(nombre):
    return (C / nombre).read_text(encoding="utf-8")


def pagina():
    cuerpo = leer("plantilla.html")
    for marca, archivo in (("__DATOS__", "datos.json"), ("__ANALISIS__", "analisis.json"), ("__EVENTOS__", "eventos.json")):
        cuerpo = cuerpo.replace(marca, seguro(leer(archivo)))
    html = ('<!doctype html><html lang="es"><head><meta charset="utf-8">'
            '<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">'
            '<meta name="robots" content="noindex">'
            '<style>:root{padding-top:env(safe-area-inset-top,0px);padding-bottom:env(safe-area-inset-bottom,0px)}'
            'body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>'
            '</head><body>' + cuerpo + '</body></html>')
    (DOCS / "index.html").write_text(html, encoding="utf-8")
    return len(html)


def esc(t):
    return t.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def doblar(linea):
    """Las líneas de un .ics no pueden pasar de 75 bytes."""
    b = linea.encode("utf-8")
    partes = []
    while len(b) > 75:
        corte = 75 if not partes else 74
        while corte > 0 and (b[corte] & 0xC0) == 0x80:
            corte -= 1
        partes.append(b[:corte].decode("utf-8"))
        b = b[corte:]
    partes.append(b.decode("utf-8"))
    return "\r\n ".join(partes)


def calendario(eventos, nombre):
    ahora = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    L = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//cartera-bolsa//ES", "CALSCALE:GREGORIAN", "METHOD:PUBLISH",
         f"X-WR-CALNAME:{esc(nombre)}", "X-WR-TIMEZONE:America/Bogota", "REFRESH-INTERVAL;VALUE=DURATION:PT12H",
         "X-PUBLISHED-TTL:PT12H"]
    for e in eventos:
        d = datetime.strptime(e["fecha"], "%Y-%m-%d")
        slug = re.sub(r"[^a-z0-9]+", "-", e["titulo"].lower())[:40]
        titulo = ("⭐ " if e.get("importante") else "") + e["titulo"] + (" (fecha aprox.)" if e.get("aprox") else "")
        L += ["BEGIN:VEVENT", f"UID:{e['fecha']}-{slug}@cartera-bolsa", f"DTSTAMP:{ahora}"]
        if e.get("hora"):
            h, m = map(int, e["hora"].split(":"))
            ini = (d + timedelta(hours=h + 5, minutes=m))  # hora Colombia (UTC-5) a UTC
            L += [f"DTSTART:{ini:%Y%m%dT%H%M%SZ}", f"DTEND:{ini + timedelta(hours=1):%Y%m%dT%H%M%SZ}"]
        else:
            L += [f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + timedelta(days=1):%Y%m%d}"]
        L += [f"SUMMARY:{esc(titulo)}", f"DESCRIPTION:{esc(e['desc'])}",
              "URL:https://yeipy67.github.io/cartera-bolsa/#fechas", "TRANSP:TRANSPARENT"]
        if e.get("importante"):
            L += ["BEGIN:VALARM", "ACTION:DISPLAY", f"DESCRIPTION:{esc(e['titulo'])}", "TRIGGER:-P1D", "END:VALARM"]
        L.append("END:VEVENT")
    L.append("END:VCALENDAR")
    return "\r\n".join(doblar(x) for x in L) + "\r\n"


def main():
    DOCS.mkdir(exist_ok=True)
    tam = pagina()
    eventos = json.loads(leer("eventos.json"))
    grupos = {"fechas": ("Mi cartera · todas las fechas", eventos)}
    for tipo, nombre in (("cartera", "Mi cartera · empresas"), ("mercado", "Mi cartera · mercado"), ("colombia", "Mi cartera · Colombia")):
        grupos[f"fechas-{tipo}"] = (nombre, [e for e in eventos if e["tipo"] == tipo])
    for archivo, (nombre, evs) in grupos.items():
        (DOCS / f"{archivo}.ics").write_text(calendario(evs, nombre), encoding="utf-8", newline="")
    print(f"docs/index.html lista ({tam // 1024} KB) y {len(grupos)} calendarios")


if __name__ == "__main__":
    main()
