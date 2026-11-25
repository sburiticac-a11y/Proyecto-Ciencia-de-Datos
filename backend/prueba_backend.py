"""Pruebas automáticas del backend.

Ejecutar desde la carpeta del proyecto:
    .venv\\Scripts\\python backend\\prueba_backend.py

Comprueba tres cosas:
1. Que la API responde bien a un pedido válido.
2. Que rechaza los datos incorrectos con el código HTTP 422 y un mensaje claro.
3. Que calcula las variables (estados, distancia, mismo estado) igual que el cuaderno 01.
"""
import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd

warnings.filterwarnings("ignore", message="Using `httpx` with")  # aviso de Starlette que no afecta las pruebas
from fastapi.testclient import TestClient  # noqa: E402

sys.path.insert(0, str(Path(__file__).resolve().parent))
from main import RECURSOS, app, haversine_km  # noqa: E402

PEDIDO = {
    "cep_cliente": "20040", "cep_vendedor": "01310", "categoria": "bed_bath_table", "cantidad": 1,
    "precio_unitario": 120.0, "flete_total": 18.5, "peso_unitario_g": 1200, "largo_cm": 30, "alto_cm": 15,
    "ancho_cm": 20, "tipo_pago": "credit_card", "cuotas": 3, "dias_prometidos": 20,
    "fecha_compra": "2018-06-13T15:00:00", "dias_pronostico": 7,
}

with TestClient(app) as cliente:  # "with" enciende el servidor de prueba y carga los modelos
    # 1. Respuestas correctas
    salud = cliente.get("/salud")
    assert salud.status_code == 200, salud.text
    print("GET /salud ->", salud.json()["modelos"])

    respuesta = cliente.post("/predecir", json=PEDIDO)
    assert respuesta.status_code == 200, respuesta.text
    datos = respuesta.json()
    print("POST /predecir ->", {k: datos[k] for k in ["entrega", "retraso"]})
    print("   demanda:", datos["demanda"]["total"], "pedidos en 7 días desde", datos["demanda"]["desde"])
    print("   variables calculadas:", datos["variables_calculadas"])

    casos = {
        "código postal con letras": {**PEDIDO, "cep_cliente": "2A040"},
        "código postal que no existe": {**PEDIDO, "cep_cliente": "00000"},
        "categoría inventada": {**PEDIDO, "categoria": "naves_espaciales"},
        "precio negativo": {**PEDIDO, "precio_unitario": -5},
        "forma de pago inválida": {**PEDIDO, "tipo_pago": "bitcoin"},
        "falta un campo obligatorio": {k: v for k, v in PEDIDO.items() if k != "dias_prometidos"},
    }
    for nombre, cuerpo in casos.items():
        r = cliente.post("/predecir", json=cuerpo)
        assert r.status_code == 422, f"{nombre}: esperaba 422 y llegó {r.status_code}"
        print(f"422 OK · {nombre}: {r.json()['detail']}")

    # 3. Reproducibilidad: las variables del backend deben ser iguales a las del cuaderno 01
    archivo = Path(__file__).resolve().parent.parent / "data" / "processed" / "pedidos_entregados.csv"
    if archivo.exists():
        muestra = pd.read_csv(archivo, dtype={"customer_zip_code_prefix": str, "seller_zip_code_prefix": str})
        muestra = muestra.dropna(subset=["distancia_km"]).sample(2000, random_state=42)
        geo = RECURSOS["geo"]
        cli = geo.loc[muestra["customer_zip_code_prefix"]].reset_index(drop=True)
        ven = geo.loc[muestra["seller_zip_code_prefix"]].reset_index(drop=True)
        distancia = haversine_km(cli["lat"], cli["lng"], ven["lat"], ven["lng"])
        assert np.allclose(distancia, muestra["distancia_km"].to_numpy()), "La distancia no coincide"
        assert (cli["estado"].to_numpy() == muestra["customer_state"].to_numpy()).all(), "El estado del cliente no coincide"
        assert (ven["estado"].to_numpy() == muestra["seller_state"].to_numpy()).all(), "El estado del vendedor no coincide"
        mismo = (cli["estado"] == ven["estado"]).astype(int).to_numpy()
        assert (mismo == muestra["mismo_estado"].to_numpy()).all(), "mismo_estado no coincide"
        print(f"Reproducibilidad OK: estados, distancia y mismo_estado iguales al cuaderno 01 en {len(muestra)} pedidos")
    else:
        print("(No se encontró data/processed/pedidos_entregados.csv; se omite la prueba de reproducibilidad)")

print("\nTodas las pruebas pasaron.")
