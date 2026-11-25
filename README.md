# Sistema predictivo de entregas (Olist)

Proyecto final de ciencia de datos. Una página web (frontend) envía los datos de un pedido a una API (backend), que prepara los datos, consulta tres modelos y devuelve:

1. **Días estimados de entrega**, con un rango probable (modelo de regresión).
2. **Probabilidad de que el pedido llegue tarde** (modelo de clasificación).
3. **Pedidos esperados por día** en la tienda (modelo de serie de tiempo).

## Estructura

```
proyecto/
├── data/
│   ├── raw/                CSV originales de Olist (no se suben al repositorio)
│   └── processed/          datos limpios que genera el cuaderno 01 (no se suben)
├── notebooks/
│   ├── 01_union_y_eda.ipynb              preparación de los datos y análisis exploratorio
│   ├── 02_regresion_dias_entrega.ipynb   modelo 1: días de entrega
│   ├── 03_clasificacion_tarde.ipynb      modelo 2: ¿llegará tarde?
│   └── 04_serie_pedidos_diarios.ipynb    modelo 3: pedidos por día
├── models/                 modelos entrenados (.joblib), su descripción (.json) y tablas para la app
├── backend/
│   ├── main.py             API hecha con FastAPI
│   └── prueba_backend.py   pruebas automáticas de la API
├── frontend/
│   └── app.py              página web hecha con Streamlit
├── informe/
│   ├── Informe_tecnico.pdf     informe técnico para entregar
│   ├── Guia_sustentacion.pdf   preguntas probables y guion de la demo (uso interno)
│   ├── figuras/                imágenes del informe
│   └── construir_pdf.py        script que generó los PDF a partir de archivos .md (esos .md no se incluyen)
├── .streamlit/config.toml  configuración de Streamlit (así no pide un correo al iniciar)
├── iniciar_app.bat         abre el backend y el frontend (Windows)
├── abrir_jupyter.bat       abre los cuadernos en Jupyter Lab (Windows)
├── requirements.txt
└── README.md
```

## Datos

*Brazilian E-Commerce Public Dataset by Olist*: https://www.kaggle.com/datasets/olistbr/brazilian-ecommerce (licencia CC BY-NC-SA 4.0, descargado el 15-11-2026).

Descarga el zip y copia los 9 archivos CSV en `data/raw/`.

## Instalación (Windows, Python 3.14)

```
py -3.14 -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

## 1. Entrenar los modelos (cuadernos)

Los modelos ya entrenados están en `models/`, así que este paso solo hace falta para volver a entrenarlos. Los cuadernos se ejecutan **en orden**: 01 → 02 → 03 → 04.

- **Jupyter Lab:** doble clic en `abrir_jupyter.bat`.
- **VS Code:** abre la carpeta `proyecto`; el entorno `.venv` queda seleccionado por `.vscode/settings.json`.
- **Terminal:**

```
for %f in (01_union_y_eda 02_regresion_dias_entrega 03_clasificacion_tarde 04_serie_pedidos_diarios) do .venv\Scripts\jupyter nbconvert --to notebook --execute --inplace notebooks\%f.ipynb
```

## 2. Usar la aplicación

**Opción rápida:** doble clic en `iniciar_app.bat`. Se abren dos ventanas (backend y frontend) y el navegador con la página.

**Opción manual**, en dos terminales desde la carpeta del proyecto:

```
.venv\Scripts\python -m uvicorn main:app --app-dir backend --port 8000
.venv\Scripts\python -m streamlit run frontend\app.py --server.headless true
```

- Página web: http://localhost:8501
- Documentación interactiva de la API: http://localhost:8000/docs

## 3. Probar el backend

```
.venv\Scripts\python backend\prueba_backend.py
```

Comprueba que la API responde a un pedido válido, que rechaza datos incorrectos con el código 422 y un mensaje claro, y que calcula las variables (estados, distancia, mismo estado) igual que el cuaderno 01.

## La API

| Método | Ruta | Qué hace |
| --- | --- | --- |
| GET | `/salud` | indica si el servidor funciona y qué modelos cargó |
| GET | `/opciones` | listas del formulario (categorías, formas de pago) y valores típicos |
| POST | `/predecir` | recibe un pedido y devuelve las predicciones de los tres modelos |

Ejemplo de pedido para `POST /predecir`:

```json
{
  "cep_cliente": "20040", "cep_vendedor": "01310", "categoria": "bed_bath_table",
  "cantidad": 1, "precio_unitario": 120.0, "flete_total": 18.5, "peso_unitario_g": 1200,
  "largo_cm": 30, "alto_cm": 15, "ancho_cm": 20, "tipo_pago": "credit_card", "cuotas": 3,
  "dias_prometidos": 20, "fecha_compra": "2018-06-13T15:00:00", "dias_pronostico": 7
}
```

La respuesta trae cuatro partes: `entrega` (días estimados, rango y fecha), `retraso` (probabilidad, nivel de riesgo y umbral), `demanda` (pedidos esperados por día con su rango) y `variables_calculadas` (lo que el backend calculó a partir de los datos).

Si los datos no cumplen las reglas (por ejemplo, un código postal con letras o un precio negativo), la API responde **422** con la lista de problemas en español. Si falla algo interno, responde **500**.

## Ejecutar los cuadernos en Google Colab

1. En *Mi unidad* de Google Drive crea una carpeta llamada `proyecto` y sube dentro las carpetas `data` (con los CSV en `data/raw`) y `notebooks`. No subas `.venv`.
2. En Drive, haz clic derecho sobre un cuaderno → *Abrir con* → *Google Colaboratory*.
3. *Entorno de ejecución* → *Ejecutar todas*, y autoriza el acceso a Drive cuando lo pida.

Si la carpeta está en otra ubicación (por ejemplo, una unidad compartida), cambia la variable `BASE` en la primera celda de código.

## Versiones

Los modelos se guardaron con **scikit-learn 1.9.1** y **statsmodels 0.15.0**. Para abrirlos, la aplicación necesita esas mismas versiones, que ya quedan fijadas en `requirements.txt`. Si se vuelven a entrenar en otro entorno (por ejemplo, en Colab), hay que usar en la aplicación las versiones de ese entorno.
