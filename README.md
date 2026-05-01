# Agente de noticias

Genera un `index.html` con noticias agrupadas desde Infobae, La Nación y Clarín.

## Ejecución local en Windows

```powershell
.\venv\Scripts\Activate.ps1
pip install -r requirements.txt
$env:GROQ_API_KEY="tu_api_key"
python main_web.py
```

Por defecto solo genera `index.html` y archivos de depuración en `data/`.

## Verificación

```powershell
.\venv\Scripts\python.exe -B -m unittest discover -s tests -v
```

Para publicar desde local:

```powershell
python main_web.py --publish
```

## GitHub Actions

El workflow `.github/workflows/run_noticias.yml` instala `requirements.txt`, ejecuta `python main_web.py` y publica `index.html`.

Configurar el secret:

- `GROQ_API_KEY`

La caché de IA se guarda en `.cache_ai.json`, se restaura con `actions/cache` y vence según `CACHE_IA_TTL_DIAS` (por defecto 3 días).

## Archivos de depuración

Cada corrida deja datos intermedios en `data/`:

- `raw_news.json`: noticias encontradas por los scrapers.
- `processed_news.json`: noticias procesadas por IA o caché.
- `groups.json`: grupos calculados por categoría.
- `site_input.txt`: texto usado para generar la web.
