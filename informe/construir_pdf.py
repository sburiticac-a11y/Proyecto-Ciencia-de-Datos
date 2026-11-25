r"""Genera Informe_tecnico.pdf y Guia_sustentacion.pdf a partir de los archivos .md de esta carpeta.

Uso, desde la carpeta del proyecto:
    .venv\Scripts\python informe\construir_pdf.py

Requiere Microsoft Edge (viene con Windows) y la librería markdown (pip install markdown)."""
import re
import subprocess
import tempfile
from pathlib import Path

import markdown

CARPETA = Path(__file__).resolve().parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
PERFIL = Path(tempfile.mkdtemp())  # perfil temporal de Edge, para no interferir con el navegador abierto

CSS = """
@page { size: A4; margin: 20mm 18mm 20mm 18mm;
  @top-left { content: "ENCABEZADO"; font: 8pt "Segoe UI", sans-serif; color: #8a8882; }
  @bottom-right { content: "Página " counter(page) " de " counter(pages); font: 8.5pt "Segoe UI", sans-serif; color: #6b6a66; } }
@page portada { @top-left { content: none; } @bottom-right { content: none; } }
* { box-sizing: border-box; }
body { font-family: "Segoe UI", Arial, sans-serif; font-size: 10.3pt; line-height: 1.5; color: #1f1f1d; margin: 0; }
h1, h2, h3 { font-family: "Segoe UI Semibold", "Segoe UI", Arial, sans-serif; color: #17325c; }
h2 { font-size: 15.5pt; margin: 22pt 0 8pt; padding-bottom: 4pt; border-bottom: 1.5px solid #2a78d6; break-after: avoid; }
h2.junto { break-before: auto; margin-top: 18pt; }
h3 { font-size: 12pt; margin: 14pt 0 5pt; break-after: avoid; }
p { margin: 0 0 7pt; orphans: 3; widows: 3; }
ul, ol { margin: 0 0 8pt; padding-left: 18pt; }
li { margin-bottom: 3pt; }
a { color: #1c5cab; text-decoration: none; }
strong { color: #111; }
table { width: 100%; border-collapse: collapse; font-size: 8.9pt; line-height: 1.35; margin: 6pt 0 11pt; }
thead { display: table-header-group; }
th { background: #e9f1fb; color: #17325c; text-align: left; font-weight: 600; }
th, td { border: 1px solid #d6d4cc; padding: 3.5pt 5pt; vertical-align: top; }
tr { break-inside: avoid; }
code { font-family: Consolas, "Courier New", monospace; font-size: 8.6pt; background: #f2f1ed; padding: 0 2pt; border-radius: 2px; }
pre { background: #f6f5f1; border: 1px solid #e1e0d9; border-radius: 4px; padding: 7pt 9pt; font-size: 8.2pt; line-height: 1.4; white-space: pre-wrap; break-inside: avoid; }
pre code { background: none; padding: 0; font-size: 8.2pt; }
figure { margin: 8pt 0 13pt; break-inside: avoid; text-align: center; }
figure img { width: 100%; height: auto; border: 1px solid #ecebe6; }
figure img.angosta { width: 62%; }
figcaption { font-size: 8.8pt; color: #52514e; margin-top: 4pt; text-align: left; line-height: 1.35; }
.portada { page: portada; height: 255mm; display: flex; flex-direction: column; justify-content: center; break-after: page; }
.portada .sup { font-size: 10pt; letter-spacing: .08em; text-transform: uppercase; color: #2a78d6; margin-bottom: 10pt; }
.portada h1 { font-size: 30pt; line-height: 1.15; margin: 0 0 10pt; }
.portada .subtitulo { font-size: 13pt; color: #3d3c39; margin-bottom: 26pt; max-width: 150mm; }
.portada .datos { font-size: 9.5pt; color: #52514e; margin-bottom: 30pt; }
.portada table { width: 125mm; font-size: 10pt; }
.portada td:first-child { width: 42mm; background: #f4f7fc; font-weight: 600; color: #17325c; }
.indice { break-after: page; }
.indice h2 { break-before: auto; }
.indice ul { list-style: none; padding-left: 0; }
.indice > .toc > ul > li { margin: 3pt 0; font-size: 10.5pt; }
.indice .figuras li { font-size: 9.3pt; color: #3d3c39; margin: 2pt 0; }
.titulo-guia { font-size: 22pt; margin: 0 0 4pt; }
.guia h2 { break-before: auto; margin-top: 16pt; font-size: 13.5pt; }
.guia p { break-inside: avoid; }
"""


def convertir(md_texto):
    md = markdown.Markdown(extensions=["tables", "fenced_code", "toc"], extension_configs={"toc": {"toc_depth": "2-2"}})
    return md.convert(md_texto), md.toc


def imprimir(html, nombre_pdf):
    temporal = CARPETA / f"_{Path(nombre_pdf).stem}.html"
    temporal.write_text(html, encoding="utf-8")
    salida = CARPETA / nombre_pdf
    subprocess.run([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--user-data-dir={PERFIL}",
                    f"--print-to-pdf={salida}", temporal.resolve().as_uri()], check=True, timeout=180,
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    temporal.unlink()
    print(f"{salida.name}: {salida.stat().st_size / 1e6:.2f} MB")


# ---------------------------------------------------------------- Informe técnico
cuerpo, indice = convertir((CARPETA / "Informe_tecnico.md").read_text(encoding="utf-8"))
cuerpo = cuerpo.replace('<img alt="Curvas ROC en validación" class="angosta"', '<img class="angosta" alt="Curvas ROC en validación"')
cuerpo = re.sub(r'<h2 id="2-', '<h2 class="junto" id="2-', cuerpo)  # la sección 2 sigue a la 1 en la misma página
figuras = re.findall(r"<figcaption>(Figura \d+\.[^<]*?\.)", cuerpo)
lista_figuras = "".join(f"<li>{f.split(':')[0].rstrip('.')}.</li>" if ":" in f else f"<li>{f}</li>" for f in figuras)
portada = """
<section class="portada">
  <div class="sup">Proyecto final · Ciencia de datos</div>
  <h1>Sistema predictivo de entregas</h1>
  <p class="subtitulo">Informe técnico: modelos de regresión, clasificación y serie de tiempo integrados en una aplicación con arquitectura frontend–backend.</p>
  <p class="datos">Datos: <em>Brazilian E-Commerce Public Dataset by Olist</em> (Kaggle) · licencia CC BY-NC-SA 4.0</p>
  <table>
    <tr><td>Integrantes</td><td>Por completar</td></tr>
    <tr><td>Curso y docente</td><td>Por completar</td></tr>
    <tr><td>Fecha de entrega</td><td>Por completar</td></tr>
    <tr><td>Repositorio</td><td>Por completar (enlace de GitHub)</td></tr>
  </table>
</section>"""
html = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Informe técnico · Sistema predictivo de entregas</title>
<style>{CSS.replace('ENCABEZADO', 'Informe técnico · Sistema predictivo de entregas (Olist)')}</style></head><body>
{portada}
<section class="indice"><h2>Contenido</h2>{indice}<h3>Figuras</h3><ul class="figuras">{lista_figuras}</ul></section>
{cuerpo}
</body></html>"""
imprimir(html, "Informe_tecnico.pdf")

# ---------------------------------------------------------------- Guía de sustentación
cuerpo_guia, _ = convertir((CARPETA / "Guia_sustentacion.md").read_text(encoding="utf-8"))
html_guia = f"""<!doctype html><html lang="es"><head><meta charset="utf-8"><title>Guía de sustentación</title>
<style>{CSS.replace('ENCABEZADO', 'Guía de sustentación · uso interno del grupo')}</style></head><body class="guia">
<h1 class="titulo-guia">Guía de sustentación</h1>
{cuerpo_guia}
</body></html>"""
imprimir(html_guia, "Guia_sustentacion.pdf")
