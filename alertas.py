#!/usr/bin/env python3
"""Alertas de bolsa al celular (ntfy).

Revisa noticias importantes (Google Noticias) y movimientos grandes de precio
(Yahoo Finance) y manda un aviso a la app ntfy. Lo que se vigila se cambia en
config.json, en esta misma carpeta.
"""
import json
import os
import re
import sys
import time
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path

CARPETA = Path(__file__).resolve().parent
CONFIG = CARPETA / "config.json"
ESTADO = CARPETA / "estado.json"
UA = "Mozilla/5.0 (X11; Linux x86_64) alertas-bolsa"

CONFIG_INICIAL = {
    "ntfy_canal": "",
    "acciones": {"VOO": 3, "ANT": 7, "NVDA": 5, "GOOGL": 5, "META": 5},
    "busquedas": [
        "Anthropic",
        "Nvidia",
        "Jensen Huang",
        "Alphabet Google",
        "Meta Zuckerberg",
        "Terafab",
        "IPO OpenAI OR SpaceX OR xAI OR Databricks OR Stripe",
    ],
    "palabras_importantes": [
        "ceo", "director ejecutivo", "renuncia", "renunció", "dimite", "destituido",
        "resign", "steps down", "stepping down", "ousted", "fired",
        "ficha", "fichaje", "contrata", "hires", "hired", "joins", "se une",
        "ipo", "salida a bolsa", "sale a bolsa", "saldrá a bolsa", "goes public", "files to go public",
        "adquiere", "adquisición", "compra a", "acquire", "acquisition", "merger", "fusión",
        "demanda", "lawsuit", "sues", "investigación", "investigation", "antimonopolio", "antitrust",
        "resultados", "earnings", "despidos", "layoffs", "split", "sanción", "sanctions", "prohíbe", "ban",
    ],
    "max_horas_noticia": 12,
    "max_avisos_por_ronda": 4,
}


def leer(ruta, defecto):
    try:
        return json.loads(ruta.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return defecto


def guardar(ruta, datos):
    ruta.write_text(json.dumps(datos, ensure_ascii=False, indent=2), encoding="utf-8")


def pedir(url):
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read()


def avisar(canal, titulo, mensaje, enlace=None, etiquetas=None, prioridad=3):
    datos = {"topic": canal, "title": titulo, "message": mensaje,
             "tags": etiquetas or [], "priority": prioridad}
    if enlace:
        datos["click"] = enlace
    req = urllib.request.Request(
        "https://ntfy.sh/", data=json.dumps(datos).encode("utf-8"),
        headers={"Content-Type": "application/json", "User-Agent": UA})
    urllib.request.urlopen(req, timeout=20).read()


def clave_titulo(t):
    t = re.sub(r"\s+-\s+[^-]+$", "", t.lower())  # quita " - Fuente"
    return re.sub(r"[^a-z0-9áéíóúñ ]", "", t)[:70]


def noticias(cfg, estado):
    vistos = set(estado.get("noticias", []))
    nuevas = []
    ahora = datetime.now(timezone.utc)
    palabras = [p.lower() for p in cfg["palabras_importantes"]]
    for q in cfg["busquedas"]:
        for hl, gl, ceid in (("es-419", "CO", "CO:es-419"), ("en-US", "US", "US:en")):
            url = ("https://news.google.com/rss/search?q=" + urllib.parse.quote(q + " when:1d")
                   + f"&hl={hl}&gl={gl}&ceid={ceid}")
            time.sleep(2)  # ir despacio para que Google no bloquee
            try:
                raiz = ET.fromstring(pedir(url))
            except Exception as e:
                print(f"Noticias '{q}' ({hl}): {e}", file=sys.stderr)
                continue
            for item in raiz.iter("item"):
                titulo = (item.findtext("title") or "").strip()
                enlace = item.findtext("link") or ""
                clave = clave_titulo(titulo)
                if not titulo or clave in vistos:
                    continue
                vistos.add(clave)
                try:
                    fecha = parsedate_to_datetime(item.findtext("pubDate"))
                    if (ahora - fecha).total_seconds() > cfg["max_horas_noticia"] * 3600:
                        continue
                except Exception:
                    pass
                bajo = titulo.lower()
                if any(re.search(r"(?<![a-záéíóúñ])" + re.escape(p) + r"(?![a-záéíóúñ])", bajo) for p in palabras):
                    nuevas.append((q, titulo, enlace))
    estado["noticias"] = list(vistos)[-3000:]
    return nuevas


def precios(cfg, estado):
    hoy = datetime.now().strftime("%Y-%m-%d")
    marcas = estado.get("precios", {})
    marcas = {k: v for k, v in marcas.items() if k.startswith(hoy)}
    avisos = []
    for simbolo, umbral in cfg["acciones"].items():
        try:
            meta = json.loads(pedir(
                f"https://query1.finance.yahoo.com/v8/finance/chart/{simbolo}?range=1d&interval=1d"
            ))["chart"]["result"][0]["meta"]
            cambio = float(meta["regularMarketChangePercent"])
            precio = float(meta["regularMarketPrice"])
        except Exception as e:
            print(f"Precio {simbolo}: {e}", file=sys.stderr)
            continue
        if abs(cambio) < umbral:
            continue
        nivel = int(abs(cambio) // umbral)  # vuelve a avisar si el movimiento se duplica
        clave = f"{hoy}:{simbolo}:{'+' if cambio > 0 else '-'}{nivel}"
        if clave in marcas:
            continue
        marcas[clave] = True
        avisos.append((simbolo, precio, cambio))
    estado["precios"] = marcas
    return avisos


def main():
    cfg = leer(CONFIG, None)
    if cfg is None:
        cfg = dict(CONFIG_INICIAL)
        guardar(CONFIG, cfg)
    # En GitHub el canal viene de un secreto (NTFY_CANAL), así no queda público.
    canal = os.environ.get("NTFY_CANAL") or cfg.get("ntfy_canal")
    if not canal:
        sys.exit("Falta el canal de ntfy: define NTFY_CANAL.")

    if "--canal" in sys.argv:
        print(canal)
        return
    if "--prueba" in sys.argv:
        avisar(canal, "Alertas de bolsa conectadas",
               "Si ves esto, las alertas ya llegan a tu celular.", etiquetas=["white_check_mark"])
        print("Aviso de prueba enviado a", canal)
        return

    estado = leer(ESTADO, {})
    primera_vez = "noticias" not in estado

    nuevas = noticias(cfg, estado)
    movimientos = precios(cfg, estado)
    guardar(ESTADO, estado)

    for simbolo, precio, cambio in movimientos:
        sube = cambio > 0
        avisar(canal, f"{simbolo} {'sube' if sube else 'baja'} {abs(cambio):.1f} % hoy",
               f"Precio: {precio:,.2f} USD",
               f"https://finance.yahoo.com/quote/{simbolo}",
               ["chart_with_upwards_trend" if sube else "chart_with_downwards_trend"], 4)

    if primera_vez:
        # La primera vez solo memoriza las noticias que ya salieron, para no llenarte de avisos viejos.
        print(f"Primera ronda: {len(nuevas)} noticias memorizadas sin avisar.")
        return

    for q, titulo, enlace in nuevas[: cfg["max_avisos_por_ronda"]]:
        avisar(canal, f"Noticia: {q.split(' OR ')[0]}", titulo, enlace, ["newspaper"], 4)
        time.sleep(1)
    if len(nuevas) > cfg["max_avisos_por_ronda"]:
        extra = len(nuevas) - cfg["max_avisos_por_ronda"]
        avisar(canal, "Más noticias", f"Hay {extra} noticias importantes más. Revisa Google Noticias.",
               etiquetas=["newspaper"])
    print(f"{len(nuevas)} noticias, {len(movimientos)} movimientos de precio.")


if __name__ == "__main__":
    main()
