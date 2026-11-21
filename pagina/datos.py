#!/usr/bin/env python3
"""Junta precios (Yahoo) y noticias (Google Noticias) para la página de la cartera."""
import json, time, urllib.request, urllib.parse, xml.etree.ElementTree as ET
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
UA = "Mozilla/5.0 (X11; Linux x86_64) alertas-bolsa"
def pedir(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": UA}), timeout=20).read()
SIMBOLOS = {"VOO": "1y", "ANT": "3mo", "NVDA": "1y", "GOOGL": "1y", "META": "1y", "COP=X": "1y"}
NOTICIAS = {"ANT": "Anthropic", "NVDA": "Nvidia", "GOOGL": "Google Alphabet", "META": "Meta Platforms", "VOO": "S&P 500 bolsa"}
out = {"generado": datetime.now(timezone.utc).isoformat(timespec="minutes"), "precios": {}, "noticias": {}}
for s, rango in SIMBOLOS.items():
    r = json.loads(pedir(f"https://query1.finance.yahoo.com/v8/finance/chart/{urllib.parse.quote(s)}?range={rango}&interval=1d"))["chart"]["result"][0]
    m = r["meta"]; ts = r["timestamp"]; cl = r["indicators"]["quote"][0]["close"]
    serie = [[datetime.fromtimestamp(t, timezone.utc).strftime("%Y-%m-%d"), round(c, 2)] for t, c in zip(ts, cl) if c is not None]
    out["precios"][s] = {"nombre": m.get("longName") or m.get("shortName") or s, "precio": m["regularMarketPrice"],
        "cambio_dia": round(m.get("regularMarketChangePercent", 0), 2), "max52": m.get("fiftyTwoWeekHigh"),
        "min52": m.get("fiftyTwoWeekLow"), "serie": serie}
    time.sleep(1)
for s, q in NOTICIAS.items():
    raiz = ET.fromstring(pedir("https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:3d") + "&hl=es-419&gl=CO&ceid=CO:es-419"))
    items = []
    for it in list(raiz.iter("item"))[:6]:
        titulo = it.findtext("title") or ""; fuente = it.findtext("source") or ""
        if fuente and titulo.endswith(" - " + fuente): titulo = titulo[: -len(fuente) - 3]
        try: fecha = parsedate_to_datetime(it.findtext("pubDate")).strftime("%Y-%m-%d %H:%M")
        except Exception: fecha = ""
        items.append({"titulo": titulo, "fuente": fuente, "fecha": fecha, "enlace": it.findtext("link")})
    out["noticias"][s] = items
    time.sleep(2)
json.dump(out, open(__import__("pathlib").Path(__file__).resolve().parent / "datos.json", "w"), ensure_ascii=False)
print({k: (v["precio"], v["cambio_dia"], len(v["serie"])) for k, v in out["precios"].items()})
print({k: len(v) for k, v in out["noticias"].items()})
