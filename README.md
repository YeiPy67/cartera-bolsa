# Mi cartera

Página que se actualiza sola cada 30 minutos (precios de Yahoo Finance y noticias de Google Noticias) y alertas al celular con ntfy.

- `alertas.py` + `config.json`: qué acciones y noticias se vigilan. El canal de ntfy está en el secreto `NTFY_CANAL`.
- `pagina/`: `datos.py` baja los datos, `armar.py` arma `docs/index.html` desde `plantilla.html`. `nota.json` es un resumen escrito a mano (se oculta a los 2 días).
- `.github/workflows/actualizar.yml`: corre todo cada 30 minutos.

No es asesoría financiera.
