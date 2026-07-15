"""Tests de regresion (snapshot) contra HTML/JSON real de cada fuente.

Objetivo: detectar si un cambio de markup en el sitio de origen rompe los
selectores de un scraper. Los fixtures en tests/fixtures/ son una captura
real de cada pagina/endpoint tomada en 2026-07-15; si el sitio cambia su
estructura despues de esa fecha, este test seguira pasando con el fixture
viejo pero el scraper en produccion puede empezar a devolver 0 noticias.
Sirve como red de contencion para cambios en el codigo de parseo, no como
monitor en vivo del sitio.
"""

import json
import unittest
from pathlib import Path
from unittest.mock import patch

from scrapers.clarin import get_clarin
from scrapers.finanzas_argy import extraer_dolares, extraer_riesgo_pais
from scrapers.infobae import get_infobae
from scrapers.lanacion import get_lanacion

FIXTURES = Path(__file__).parent / "fixtures"


def _leer(nombre):
    return (FIXTURES / nombre).read_text(encoding="utf-8")


class ScrapersRegresionTest(unittest.TestCase):
    def test_clarin_extrae_noticias_desde_html_real(self):
        html = _leer("clarin_economia.html")
        with patch("scrapers.clarin.obtener_html", return_value=html):
            noticias = get_clarin()

        self.assertGreater(len(noticias), 0)
        for noticia in noticias:
            self.assertEqual(noticia["diario"], "Clarín")
            self.assertTrue(noticia["titulo"])
            self.assertTrue(noticia["link"].startswith("https://www.clarin.com"))

    def test_infobae_extrae_noticias_desde_html_real(self):
        html = _leer("infobae_economia.html")
        with patch("scrapers.infobae.obtener_html", return_value=html):
            noticias = get_infobae()

        self.assertGreater(len(noticias), 0)
        for noticia in noticias:
            self.assertEqual(noticia["diario"], "Infobae")
            self.assertTrue(noticia["titulo"])
            self.assertTrue(noticia["link"].startswith("https://www.infobae.com"))

    def test_lanacion_extrae_noticias_desde_html_real(self):
        html = _leer("lanacion_economia.html")
        with patch("scrapers.lanacion.obtener_html", return_value=html):
            noticias = get_lanacion()

        self.assertGreater(len(noticias), 0)
        for noticia in noticias:
            self.assertEqual(noticia["diario"], "La Nación")
            self.assertTrue(noticia["titulo"])
            self.assertTrue(noticia["link"].startswith("https://www.lanacion.com.ar"))

    def test_finanzas_argy_extrae_dolares_desde_payload_real(self):
        payload = json.loads(_leer("finanzas_argy_dolar.json"))
        indicadores = extraer_dolares(payload)

        self.assertEqual(
            [i["nombre"] for i in indicadores],
            ["Dólar Blue", "Dólar Oficial", "Dólar MEP"],
        )
        for indicador in indicadores:
            self.assertTrue(indicador["valor"].startswith("$ "))

    def test_finanzas_argy_extrae_riesgo_pais_desde_html_real(self):
        html = _leer("finanzas_argy_datos.html")
        riesgo_pais = extraer_riesgo_pais(html)

        self.assertIsNotNone(riesgo_pais)
        self.assertEqual(riesgo_pais["nombre"], "Riesgo País")
        self.assertRegex(riesgo_pais["valor"], r"^\d")


if __name__ == "__main__":
    unittest.main()
