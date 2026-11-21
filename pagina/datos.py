#!/usr/bin/env python3
"""Junta precios (Yahoo Finance, 5 años) y noticias (Google Noticias) para la página."""
import json
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

UA = "Mozilla/5.0 (X11; Linux x86_64) alertas-bolsa"
CARPETA = Path(__file__).resolve().parent

# Todo lo que se puede poner en los perfiles de seguimiento.
SIMBOLOS = [
    "VOO", "ANT", "NVDA", "GOOGL", "META",
    "AAPL", "MSFT", "AMZN", "TSLA",
    "AMD", "AVGO", "TSM", "ASML", "PLTR",
    "QQQ", "VT", "SCHD", "GLD", "^VIX",
    "EC", "CIB", "COP=X", "BZ=F",
    "BTC-USD", "ETH-USD", "SOL-USD",
]
NOTICIAS = {
    "ANT": "Anthropic",
    "NVDA": "Nvidia",
    "GOOGL": "Google Alphabet",
    "META": "Meta Platforms",
    "VOO": "S&P 500 Wall Street",
    "MUNDO": "economía mundial mercados Fed",
    "COLOMBIA": "economía Colombia dólar Banco de la República",
}
DIARIOS = 260  # último año: un punto por día; antes: uno por semana


def pedir(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    return urllib.request.urlopen(req, timeout=25).read()


def serie_comprimida(fechas, cierres):
    puntos = [(datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"), round(c, 4 if c < 10 else 2))
              for t, c in zip(fechas, cierres) if c is not None]
    viejos, recientes = puntos[:-DIARIOS], puntos[-DIARIOS:]
    return [list(p) for p in viejos[::5] + recientes]


def main():
    out = {"generado": datetime.now(timezone.utc).isoformat(timespec="minutes"), "precios": {}, "noticias": {}}
    for s in SIMBOLOS:
        try:
            r = json.loads(pedir("https://query1.finance.yahoo.com/v8/finance/chart/"
                                 + urllib.parse.quote(s) + "?range=5y&interval=1d"))["chart"]["result"][0]
            m = r["meta"]
            out["precios"][s] = {
                "nombre": m.get("longName") or m.get("shortName") or s,
                "precio": m["regularMarketPrice"],
                "cambio_dia": round(m.get("regularMarketChangePercent") or 0, 2),
                "max52": m.get("fiftyTwoWeekHigh"),
                "min52": m.get("fiftyTwoWeekLow"),
                "serie": serie_comprimida(r["timestamp"], r["indicators"]["quote"][0]["close"]),
            }
        except Exception as e:
            print("Precio", s, e)
        time.sleep(0.8)
    for clave, q in NOTICIAS.items():
        try:
            raiz = ET.fromstring(pedir("https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:3d")
                                       + "&hl=es-419&gl=CO&ceid=CO:es-419"))
        except Exception as e:
            print("Noticias", clave, e)
            continue
        items = []
        for it in list(raiz.iter("item"))[:8]:
            titulo = it.findtext("title") or ""
            fuente = it.findtext("source") or ""
            if fuente and titulo.endswith(" - " + fuente):
                titulo = titulo[: -len(fuente) - 3]
            try:
                fecha = parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d %H:%M")
            except Exception:
                fecha = ""
            items.append({"titulo": titulo, "fuente": fuente, "fecha": fecha, "enlace": it.findtext("link")})
        out["noticias"][clave] = items
        time.sleep(2)
    (CARPETA / "datos.json").write_text(json.dumps(out, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
    print(len(out["precios"]), "símbolos,", sum(len(v) for v in out["noticias"].values()), "noticias")


if __name__ == "__main__":
    main()
