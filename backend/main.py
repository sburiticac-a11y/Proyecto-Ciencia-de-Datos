"""API del sistema predictivo de entregas (Olist).

Recibe los datos de un pedido desde el frontend, calcula las mismas variables que usamos al
entrenar (cuaderno 01) y devuelve en formato JSON las respuestas de los tres modelos:

1. Regresión: cuántos días tardará en llegar el pedido.
2. Clasificación: qué tan probable es que llegue después de la fecha prometida.
3. Serie de tiempo: cuántos pedidos recibirá la tienda en los próximos días.

Para iniciarla, desde la carpeta del proyecto:
    .venv\\Scripts\\python -m uvicorn main:app --app-dir backend --port 8000
Documentación interactiva (para probarla desde el navegador): http://localhost:8000/docs
"""
import json
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from pathlib import Path
from typing import Literal

import joblib
import numpy as np
import pandas as pd
from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

MODELOS = Path(__file__).resolve().parent.parent / "models"
RECURSOS = {}  # aquí quedan los modelos y las tablas que se cargan al iniciar el servidor


# ---------------------------------------------------------------------------------------------
# Carga de los modelos (una sola vez, al iniciar)
# ---------------------------------------------------------------------------------------------
def leer_json(nombre):
    return json.loads((MODELOS / nombre).read_text(encoding="utf-8"))


def cargar_recursos():
    """Carga los tres modelos, sus descripciones y las tablas de apoyo."""
    RECURSOS["regresion"] = joblib.load(MODELOS / "regresion_dias_entrega.joblib")
    RECURSOS["meta_regresion"] = leer_json("regresion_dias_entrega.json")
    RECURSOS["clasificacion"] = joblib.load(MODELOS / "clasificacion_tarde.joblib")
    RECURSOS["meta_clasificacion"] = leer_json("clasificacion_tarde.json")
    RECURSOS["serie"] = joblib.load(MODELOS / "serie_pedidos.joblib")
    RECURSOS["meta_serie"] = leer_json("serie_pedidos.json")
    RECURSOS["geo"] = pd.read_csv(MODELOS / "geo_cep.csv", dtype={"cep_prefijo": str}).set_index("cep_prefijo")
    RECURSOS["opciones"] = leer_json("opciones.json")


@asynccontextmanager
async def ciclo_de_vida(app):
    cargar_recursos()  # al encender el servidor
    yield
    RECURSOS.clear()  # al apagarlo


app = FastAPI(title="API · Predicción de entregas (Olist)", version="1.0", lifespan=ciclo_de_vida,
              description="Recibe los datos de un pedido y devuelve las predicciones de los tres modelos del proyecto.")


# ---------------------------------------------------------------------------------------------
# Datos que recibe la API (FastAPI revisa automáticamente los tipos y los rangos)
# ---------------------------------------------------------------------------------------------
class Pedido(BaseModel):
    cep_cliente: str = Field(pattern=r"^\d{5}$", examples=["20040"],
                             description="Primeros 5 dígitos del código postal (CEP) del cliente")
    cep_vendedor: str = Field(pattern=r"^\d{5}$", examples=["01310"],
                              description="Primeros 5 dígitos del código postal (CEP) del vendedor")
    categoria: str = Field(examples=["bed_bath_table"], description="Categoría del producto")
    cantidad: int = Field(default=1, ge=1, le=20, description="Cantidad de productos")
    precio_unitario: float = Field(gt=0, le=10000, examples=[120.0], description="Precio de cada producto, en reales")
    flete_total: float = Field(ge=0, le=1000, examples=[18.5], description="Costo del envío, en reales")
    peso_unitario_g: float = Field(gt=0, le=50000, examples=[1200], description="Peso de cada producto, en gramos")
    largo_cm: float = Field(gt=0, le=200, examples=[30], description="Largo del paquete de cada producto, en cm")
    alto_cm: float = Field(gt=0, le=200, examples=[15], description="Alto del paquete de cada producto, en cm")
    ancho_cm: float = Field(gt=0, le=200, examples=[20], description="Ancho del paquete de cada producto, en cm")
    tipo_pago: Literal["credit_card", "boleto", "voucher", "debit_card"] = "credit_card"
    cuotas: int = Field(default=1, ge=1, le=24, description="Número de cuotas del pago")
    dias_prometidos: float = Field(ge=1, le=120, examples=[20], description="Días de entrega que promete la tienda")
    fecha_compra: datetime | None = Field(default=None, description="Fecha y hora de la compra (si no se envía, se usa la actual)")
    dias_pronostico: int = Field(default=14, ge=1, le=28, description="Cuántos días de demanda pronosticar")


# Nombres en español para los mensajes de error
NOMBRES_CAMPOS = {
    "cep_cliente": "Código postal del cliente", "cep_vendedor": "Código postal del vendedor",
    "categoria": "Categoría", "cantidad": "Cantidad", "precio_unitario": "Precio por unidad",
    "flete_total": "Costo del envío", "peso_unitario_g": "Peso por unidad", "largo_cm": "Largo",
    "alto_cm": "Alto", "ancho_cm": "Ancho", "tipo_pago": "Forma de pago", "cuotas": "Cuotas",
    "dias_prometidos": "Días prometidos", "fecha_compra": "Fecha de compra", "dias_pronostico": "Días a pronosticar",
}


def traducir_error(error):
    """Convierte un error de validación de FastAPI en un mensaje claro en español."""
    limite = error.get("ctx", {})
    mensajes = {
        "missing": "es obligatorio",
        "string_pattern_mismatch": "debe tener exactamente 5 dígitos",
        "greater_than": f"debe ser mayor que {limite.get('gt')}",
        "greater_than_equal": f"debe ser mayor o igual a {limite.get('ge')}",
        "less_than_equal": f"debe ser menor o igual a {limite.get('le')}",
        "literal_error": "no es una opción válida",
        "int_parsing": "debe ser un número entero",
        "int_from_float": "debe ser un número entero",
        "float_parsing": "debe ser un número",
        "datetime_parsing": "no tiene un formato de fecha válido",
        "datetime_from_date_parsing": "no tiene un formato de fecha válido",
    }
    campo = str(error["loc"][-1])
    return f"{NOMBRES_CAMPOS.get(campo, campo)}: {mensajes.get(error['type'], error['msg'])}"


@app.exception_handler(RequestValidationError)
async def errores_de_validacion(request: Request, exc: RequestValidationError):
    """Si los datos no cumplen las reglas, responde 422 con la lista de problemas en español."""
    return JSONResponse(status_code=422, content={"detail": [traducir_error(e) for e in exc.errors()]})


# ---------------------------------------------------------------------------------------------
# Preparación de los datos: las mismas variables que calculamos en el cuaderno 01
# ---------------------------------------------------------------------------------------------
def haversine_km(lat1, lng1, lat2, lng2):
    """Distancia en línea recta (km) entre dos puntos de la Tierra. Es la misma fórmula del cuaderno 01."""
    lat1, lng1, lat2, lng2 = map(np.radians, (lat1, lng1, lat2, lng2))
    a = np.sin((lat2 - lat1) / 2) ** 2 + np.cos(lat1) * np.cos(lat2) * np.sin((lng2 - lng1) / 2) ** 2
    return 2 * 6371 * np.arcsin(np.sqrt(a))


def construir_entrada(pedido: Pedido):
    """Convierte lo que escribe el usuario en las variables que usan los modelos."""
    geo = RECURSOS["geo"]
    for quien, cep in [("cliente", pedido.cep_cliente), ("vendedor", pedido.cep_vendedor)]:
        if cep not in geo.index:
            raise HTTPException(status_code=422,
                                detail=f"No encontramos el código postal del {quien} ({cep}). Revisa los 5 dígitos.")
    if pedido.categoria not in RECURSOS["opciones"]["categorias"]:
        raise HTTPException(status_code=422, detail=f"La categoría '{pedido.categoria}' no existe en nuestros datos.")

    cliente, vendedor = geo.loc[pedido.cep_cliente], geo.loc[pedido.cep_vendedor]
    fecha = pedido.fecha_compra or datetime.now()
    variables = {
        "customer_state": str(cliente["estado"]),
        "seller_state": str(vendedor["estado"]),
        "categoria": pedido.categoria,
        "tipo_pago": pedido.tipo_pago,
        "dia_semana": fecha.weekday(),
        "distancia_km": float(haversine_km(cliente["lat"], cliente["lng"], vendedor["lat"], vendedor["lng"])),
        "mismo_estado": int(cliente["estado"] == vendedor["estado"]),
        "dias_prometidos": pedido.dias_prometidos,
        "flete_total": pedido.flete_total,
        "precio_total": pedido.precio_unitario * pedido.cantidad,
        "peso_total_g": pedido.peso_unitario_g * pedido.cantidad,
        "volumen_total_cm3": pedido.largo_cm * pedido.alto_cm * pedido.ancho_cm * pedido.cantidad,
        "n_items": pedido.cantidad,
        "n_vendedores": 1,
        "cuotas": pedido.cuotas,
        "hora": fecha.hour,
    }
    return pd.DataFrame([variables]), variables, fecha


# ---------------------------------------------------------------------------------------------
# Las tres predicciones
# ---------------------------------------------------------------------------------------------
def predecir_entrega(X, fecha):
    meta = RECURSOS["meta_regresion"]
    dias = float(RECURSOS["regresion"].predict(X[meta["categoricas"] + meta["numericas"]])[0])
    rango = meta["rango_error_dias"]
    return {"dias_estimados": round(dias, 1),
            "rango_dias": [round(max(1.0, dias + rango["p10"]), 1), round(max(1.0, dias + rango["p90"]), 1)],
            "fecha_estimada": (fecha + timedelta(days=dias)).date().isoformat()}


def predecir_retraso(X):
    meta = RECURSOS["meta_clasificacion"]
    prob = float(RECURSOS["clasificacion"].predict_proba(X[meta["categoricas"] + meta["numericas"]])[0, 1])
    if prob >= meta["umbral"]:
        nivel = "alto"
    elif prob >= meta["tasa_base"]:
        nivel = "medio"
    else:
        nivel = "bajo"
    return {"probabilidad": round(prob, 4), "llegara_tarde": prob >= meta["umbral"], "nivel": nivel,
            "umbral": meta["umbral"], "promedio_general": meta["tasa_base"]}


def pronosticar_demanda(dias):
    meta = RECURSOS["meta_serie"]
    banda = meta["rango_error_relativo"]
    pronostico = RECURSOS["serie"].forecast(dias)
    filas = [{"fecha": f.date().isoformat(), "pedidos": round(float(v)),
              "minimo": round(float(v) * (1 + banda["p10"])), "maximo": round(float(v) * (1 + banda["p90"]))}
             for f, v in pronostico.items()]
    return {"desde": filas[0]["fecha"], "total": sum(f["pedidos"] for f in filas), "dias": filas}


# ---------------------------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------------------------
@app.get("/")
def inicio():
    return {"mensaje": "API de predicción de entregas funcionando. Documentación en /docs"}


@app.get("/salud")
def salud():
    """Indica si el servidor funciona y qué modelos cargó, con su métrica principal en la prueba."""
    reg, cla, ser = RECURSOS["meta_regresion"], RECURSOS["meta_clasificacion"], RECURSOS["meta_serie"]
    return {
        "estado": "ok",
        "modelos": {
            "regresion": {"algoritmo": reg["modelo"], "mae_prueba_dias": reg["metricas_prueba"]["MAE"]},
            "clasificacion": {"algoritmo": cla["modelo"], "auc_prueba": cla["metricas_prueba"]["AUC"],
                              "f1_prueba": cla["metricas_prueba"]["F1"]},
            "serie_de_tiempo": {"algoritmo": ser["modelo"], "mae_prueba_pedidos": ser["metricas_prueba"]["MAE"]},
        },
        "version_sklearn": reg["version_sklearn"],
    }


@app.get("/opciones")
def opciones():
    """Listas para el formulario (categorías, formas de pago) y valores típicos para rellenarlo."""
    return RECURSOS["opciones"] | {"ultima_fecha_datos": RECURSOS["meta_serie"]["ultima_fecha"]}


@app.post("/predecir")
def predecir(pedido: Pedido):
    """Recibe un pedido y devuelve las respuestas de los tres modelos en un solo JSON."""
    X, variables, fecha = construir_entrada(pedido)
    try:
        entrega = predecir_entrega(X, fecha)
        retraso = predecir_retraso(X)
        demanda = pronosticar_demanda(pedido.dias_pronostico)
    except Exception as error:  # una falla inesperada de algún modelo
        raise HTTPException(status_code=500, detail=f"Error interno al calcular las predicciones: {error}") from error
    return {
        "entrega": entrega,
        "retraso": retraso,
        "demanda": demanda,
        "variables_calculadas": {
            "estado_cliente": variables["customer_state"],
            "estado_vendedor": variables["seller_state"],
            "distancia_km": round(variables["distancia_km"], 1),
            "mismo_estado": bool(variables["mismo_estado"]),
            "dia_semana": variables["dia_semana"],
            "hora": variables["hora"],
            "precio_total": round(variables["precio_total"], 2),
            "peso_total_g": round(variables["peso_total_g"]),
            "volumen_total_cm3": round(variables["volumen_total_cm3"]),
            "fecha_compra": fecha.isoformat(timespec="minutes"),
        },
    }
