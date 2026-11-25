"""Página web (frontend) del sistema predictivo de entregas.

Muestra un formulario para escribir los datos de un pedido, los envía al backend (API) con una
petición HTTP y presenta las respuestas de los tres modelos.

Para iniciarla, desde la carpeta del proyecto y con el backend encendido:
    .venv\\Scripts\\python -m streamlit run frontend\\app.py
"""
import os
import re
from datetime import date, datetime, time

import altair as alt
import pandas as pd
import requests
import streamlit as st

API = os.environ.get("API_URL", "http://localhost:8000")  # dirección del backend
AZUL = "#2a78d6"  # el mismo azul de los gráficos de los cuadernos

FORMAS_PAGO = {"credit_card": "Tarjeta de crédito", "boleto": "Boleto bancario (pago en efectivo)",
               "debit_card": "Tarjeta de débito", "voucher": "Voucher (cupón)"}
CATEGORIAS_ES = {
    "bed_bath_table": "Cama, mesa y baño", "health_beauty": "Salud y belleza", "sports_leisure": "Deportes y ocio",
    "furniture_decor": "Muebles y decoración", "computers_accessories": "Computación y accesorios",
    "housewares": "Artículos para el hogar", "watches_gifts": "Relojes y regalos", "telephony": "Telefonía",
    "garden_tools": "Jardín y herramientas", "auto": "Automotriz", "toys": "Juguetes", "cool_stuff": "Artículos curiosos",
    "perfumery": "Perfumería", "baby": "Bebés", "electronics": "Electrónica", "stationery": "Papelería",
    "fashion_bags_accessories": "Bolsos y accesorios", "pet_shop": "Mascotas", "office_furniture": "Muebles de oficina",
    "consoles_games": "Consolas y videojuegos", "luggage_accessories": "Maletas y accesorios",
    "construction_tools_construction": "Construcción", "home_appliances": "Electrodomésticos",
    "musical_instruments": "Instrumentos musicales", "small_appliances": "Pequeños electrodomésticos",
    "books_general_interest": "Libros", "food": "Alimentos", "sin_categoria": "Sin categoría",
}
# Rutas de ejemplo con códigos postales reales del dataset: (código del vendedor, código del cliente)
EJEMPLOS = {
    "São Paulo → Río de Janeiro": ("01310", "20040"),
    "São Paulo → São Paulo (misma ciudad)": ("01310", "04538"),
    "São Paulo → Manaos (Amazonas, muy lejos)": ("01310", "69005"),
    "Curitiba → Maceió (Alagoas)": ("80010", "57020"),
    "Belo Horizonte → Porto Alegre": ("30130", "90010"),
}
NOMBRES_DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]

st.set_page_config(page_title="Predicción de entregas", page_icon=":material/local_shipping:", layout="wide")


# ---------------------------------------------------------------------------------------------
# Comunicación con el backend
# ---------------------------------------------------------------------------------------------
@st.cache_data(ttl=300, show_spinner=False)
def pedir(ruta):
    """GET al backend (se guarda 5 minutos para no repetir la consulta en cada clic)."""
    respuesta = requests.get(f"{API}{ruta}", timeout=10)
    respuesta.raise_for_status()
    return respuesta.json()


def nombre_categoria(codigo):
    return CATEGORIAS_ES.get(codigo, codigo.replace("_", " ").capitalize())


def usar_ejemplo():
    """Cuando se elige una ruta de ejemplo, copiamos sus códigos postales al formulario."""
    vendedor, cliente = EJEMPLOS[st.session_state["ejemplo"]]
    st.session_state["cep_vendedor"], st.session_state["cep_cliente"] = vendedor, cliente


# ---------------------------------------------------------------------------------------------
# Encabezado y estado del servidor
# ---------------------------------------------------------------------------------------------
st.title("Predicción de entregas para una tienda en línea")
st.caption("Proyecto final de ciencia de datos · datos reales de Olist (Brasil, 2017–2018)")

try:
    opciones = pedir("/opciones")
    salud = pedir("/salud")
except requests.exceptions.RequestException:
    st.error(f"No pudimos conectarnos con el servidor (backend) en {API}. "
             "Revisa que esté encendido y vuelve a cargar la página.", icon=":material/cloud_off:")
    st.stop()

with st.sidebar:
    st.subheader("Estado del servidor")
    st.success("Backend conectado", icon=":material/check_circle:")
    modelos = salud["modelos"]
    st.markdown(
        f"**Regresión:** {modelos['regresion']['algoritmo']} · error promedio en la prueba: "
        f"{modelos['regresion']['mae_prueba_dias']:.1f} días\n\n"
        f"**Clasificación:** {modelos['clasificacion']['algoritmo']} · AUC en la prueba: "
        f"{modelos['clasificacion']['auc_prueba']:.2f}\n\n"
        f"**Serie de tiempo:** {modelos['serie_de_tiempo']['algoritmo']} · error promedio en la prueba: "
        f"{modelos['serie_de_tiempo']['mae_prueba_pedidos']:.0f} pedidos por día")
    st.caption(f"API: {API} · documentación en {API}/docs")

with st.expander("¿Cómo funciona?"):
    st.markdown(
        "1. Escribes los datos de un pedido en el formulario.\n"
        "2. Esta página los envía al **backend** (una API hecha con FastAPI).\n"
        "3. El backend calcula las mismas variables que usamos al entrenar (distancia, estados, día de la semana…) "
        "y consulta **tres modelos**: uno estima los días de entrega, otro el riesgo de retraso y otro la demanda de "
        "la tienda.\n"
        "4. Las respuestas vuelven en formato JSON y aquí las mostramos.")

# ---------------------------------------------------------------------------------------------
# Formulario
# ---------------------------------------------------------------------------------------------
valores = opciones["valores_tipicos"]
if "cep_vendedor" not in st.session_state:
    st.session_state["cep_vendedor"], st.session_state["cep_cliente"] = EJEMPLOS["São Paulo → Río de Janeiro"]

st.selectbox("Ruta de ejemplo (opcional)", list(EJEMPLOS), key="ejemplo", on_change=usar_ejemplo,
             help="Rellena los códigos postales con una ruta real del dataset.")

with st.form("pedido"):
    col1, col2, col3 = st.columns(3, gap="large")
    with col1:
        st.markdown("**1. ¿Desde dónde y hacia dónde?**")
        cep_vendedor = st.text_input("Código postal del vendedor (CEP)", key="cep_vendedor", max_chars=5,
                                     help="Los primeros 5 dígitos del código postal brasileño.")
        cep_cliente = st.text_input("Código postal del cliente (CEP)", key="cep_cliente", max_chars=5)
        dias_prometidos = st.number_input("Días de entrega que promete la tienda", min_value=1, max_value=120,
                                          value=int(valores["dias_prometidos"]))
        flete = st.number_input("Costo del envío (R$)", min_value=0.0, max_value=1000.0,
                                value=float(valores["flete_total"]), step=1.0)
    with col2:
        st.markdown("**2. ¿Qué se compra?**")
        categoria = st.selectbox("Categoría del producto", opciones["categorias"], format_func=nombre_categoria)
        cantidad = st.number_input("Cantidad de productos", min_value=1, max_value=20, value=1)
        precio = st.number_input("Precio por unidad (R$)", min_value=0.01, max_value=10000.0,
                                 value=float(valores["precio_unitario"]), step=1.0)
        peso = st.number_input("Peso por unidad (gramos)", min_value=1, max_value=50000,
                               value=int(valores["peso_unitario_g"]))
        c_largo, c_alto, c_ancho = st.columns(3)
        largo = c_largo.number_input("Largo (cm)", min_value=1, max_value=200, value=int(valores["largo_cm"]))
        alto = c_alto.number_input("Alto (cm)", min_value=1, max_value=200, value=int(valores["alto_cm"]))
        ancho = c_ancho.number_input("Ancho (cm)", min_value=1, max_value=200, value=int(valores["ancho_cm"]))
    with col3:
        st.markdown("**3. ¿Cómo y cuándo?**")
        tipo_pago = st.selectbox("Forma de pago", list(FORMAS_PAGO), format_func=FORMAS_PAGO.get)
        cuotas = st.number_input("Número de cuotas", min_value=1, max_value=24, value=1)
        c_dia, c_hora = st.columns(2)
        dia_compra = c_dia.date_input("Fecha de compra", value=date.today(), format="DD/MM/YYYY")
        hora_compra = c_hora.time_input("Hora", value=time(15, 0))
        dias_pronostico = st.slider("Días de demanda a pronosticar", min_value=1, max_value=28, value=14)
    enviado = st.form_submit_button("Calcular predicciones", type="primary", width="stretch")

if enviado:
    # Validaciones antes de enviar: los campos numéricos ya tienen mínimos y máximos en el formulario
    errores = [f"El {quien} debe tener exactamente 5 números (ahora tiene «{cep}»)."
               for quien, cep in [("código postal del vendedor", cep_vendedor), ("código postal del cliente", cep_cliente)]
               if not re.fullmatch(r"\d{5}", cep.strip())]
    if errores:
        st.session_state.pop("resultado", None)  # no mostramos resultados de un pedido anterior
        for error in errores:
            st.error(error, icon=":material/error:")
    else:
        pedido = {
            "cep_cliente": cep_cliente.strip(), "cep_vendedor": cep_vendedor.strip(), "categoria": categoria,
            "cantidad": int(cantidad), "precio_unitario": float(precio), "flete_total": float(flete),
            "peso_unitario_g": float(peso), "largo_cm": float(largo), "alto_cm": float(alto), "ancho_cm": float(ancho),
            "tipo_pago": tipo_pago, "cuotas": int(cuotas), "dias_prometidos": float(dias_prometidos),
            "fecha_compra": datetime.combine(dia_compra, hora_compra).isoformat(), "dias_pronostico": int(dias_pronostico),
        }
        try:
            with st.spinner("Consultando los modelos..."):
                respuesta = requests.post(f"{API}/predecir", json=pedido, timeout=30)
        except requests.exceptions.RequestException:
            st.session_state.pop("resultado", None)
            st.error("No pudimos conectarnos con el servidor (backend). Revisa que esté encendido.",
                     icon=":material/cloud_off:")
        else:
            if respuesta.status_code == 200:
                st.session_state["resultado"] = respuesta.json()
                st.session_state["pedido_enviado"] = pedido
            elif respuesta.status_code == 422:
                detalle = respuesta.json().get("detail", "Datos inválidos")
                st.session_state.pop("resultado", None)
                for mensaje in (detalle if isinstance(detalle, list) else [detalle]):
                    st.error(mensaje, icon=":material/error:")
            else:
                st.session_state.pop("resultado", None)
                st.error(f"El servidor tuvo un problema (código {respuesta.status_code}). Intenta de nuevo.",
                         icon=":material/error:")

# ---------------------------------------------------------------------------------------------
# Resultados
# ---------------------------------------------------------------------------------------------
if "resultado" in st.session_state:
    resultado, pedido = st.session_state["resultado"], st.session_state["pedido_enviado"]
    entrega, retraso, demanda = resultado["entrega"], resultado["retraso"], resultado["demanda"]
    variables = resultado["variables_calculadas"]

    st.subheader("Resultados")
    c1, c2, c3 = st.columns(3, gap="medium")
    with c1, st.container(border=True):
        st.markdown("**Tiempo de entrega** · modelo de regresión")
        st.metric("Días estimados", f"{entrega['dias_estimados']:.1f} días")
        minimo, maximo = entrega["rango_dias"]
        st.markdown(f"Rango probable: entre **{minimo:.0f}** y **{maximo:.0f}** días")
        llegada = date.fromisoformat(entrega["fecha_estimada"])
        st.caption(f"Llegaría alrededor del {llegada:%d/%m/%Y}. La tienda prometió {pedido['dias_prometidos']:.0f} días.")
    with c2, st.container(border=True):
        st.markdown("**Riesgo de retraso** · modelo de clasificación")
        st.metric("Probabilidad de llegar tarde", f"{retraso['probabilidad']:.0%}")
        if retraso["nivel"] == "alto":
            st.error("Riesgo alto: el modelo predice que llegará tarde.", icon=":material/warning:")
        elif retraso["nivel"] == "medio":
            st.warning("Riesgo medio: más que el promedio, pero el modelo no lo marca como tarde.",
                       icon=":material/info:")
        else:
            st.success("Riesgo bajo: menos que el promedio de los pedidos.", icon=":material/check_circle:")
        st.caption(f"En promedio llega tarde el {retraso['promedio_general']:.1%} de los pedidos. "
                   f"El modelo dice «tarde» desde una probabilidad de {retraso['umbral']:.0%}.")
    with c3, st.container(border=True):
        st.markdown("**Demanda de la tienda** · modelo de serie de tiempo")
        st.metric(f"Pedidos esperados en {len(demanda['dias'])} días", f"{demanda['total']:,}".replace(",", "."))
        desde = date.fromisoformat(demanda["desde"])
        st.markdown(f"Promedio: **{demanda['total'] / len(demanda['dias']):.0f}** pedidos por día")
        st.caption(f"Desde el {desde:%d/%m/%Y}: los datos terminan el {opciones['ultima_fecha_datos']}, "
                   "así que el pronóstico empieza al día siguiente.")

    # Gráfico de la demanda con su rango probable (pase el mouse por los puntos para ver los valores)
    tabla = pd.DataFrame(demanda["dias"])
    tabla["fecha"] = pd.to_datetime(tabla["fecha"])
    base = alt.Chart(tabla).encode(x=alt.X("fecha:T", title="Fecha", axis=alt.Axis(format="%d/%m")))
    banda = base.mark_area(opacity=0.18, color=AZUL).encode(y=alt.Y("minimo:Q", title="Pedidos por día"), y2="maximo:Q")
    linea = base.mark_line(color=AZUL, strokeWidth=2).encode(y="pedidos:Q")
    puntos = base.mark_circle(color=AZUL, size=70, opacity=1).encode(
        y="pedidos:Q",
        tooltip=[alt.Tooltip("fecha:T", title="Fecha", format="%d/%m/%Y"),
                 alt.Tooltip("pedidos:Q", title="Pedidos esperados"),
                 alt.Tooltip("minimo:Q", title="Mínimo probable"),
                 alt.Tooltip("maximo:Q", title="Máximo probable")])
    st.altair_chart((banda + linea + puntos).properties(height=320, title="Pedidos esperados por día y rango probable"),
                    width="stretch")
    st.caption("La línea es el pronóstico y la franja es el rango donde quedó el 80% de los días en la prueba del modelo.")

    with st.expander("Lo que calculó el sistema con tus datos"):
        st.markdown(
            f"- Estado del vendedor: **{variables['estado_vendedor']}** · estado del cliente: **{variables['estado_cliente']}**"
            f" ({'mismo estado' if variables['mismo_estado'] else 'estados distintos'})\n"
            f"- Distancia en línea recta: **{variables['distancia_km']:.0f} km**\n"
            f"- Compra un **{NOMBRES_DIAS[variables['dia_semana']]}** a las **{variables['hora']}:00** horas\n"
            f"- Totales del pedido: R$ {variables['precio_total']:.2f} · {variables['peso_total_g']} g · "
            f"{variables['volumen_total_cm3']} cm³")
        st.caption("Son las mismas variables que calculamos al preparar los datos de entrenamiento (cuaderno 01).")

    with st.expander("Respuesta completa del backend (JSON)"):
        st.json(resultado)
