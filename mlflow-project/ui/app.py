"""UI mínima que consume la API desplegada en Kubernetes."""
import os

import requests
import streamlit as st

API_URL = os.environ.get("API_URL", "http://adult-api:8000")

WORKCLASS = ["Private", "Self-emp-not-inc", "Self-emp-inc", "Federal-gov", "Local-gov",
             "State-gov", "Without-pay", "Never-worked", "Unknown"]
EDUCATION = ["Preschool", "1st-4th", "5th-6th", "7th-8th", "9th", "10th", "11th", "12th",
             "HS-grad", "Some-college", "Assoc-voc", "Assoc-acdm", "Bachelors", "Masters",
             "Prof-school", "Doctorate"]
MARITAL = ["Married-civ-spouse", "Never-married", "Divorced", "Separated", "Widowed",
           "Married-spouse-absent", "Married-AF-spouse"]
OCCUPATION = ["Exec-managerial", "Prof-specialty", "Tech-support", "Sales", "Craft-repair",
              "Adm-clerical", "Machine-op-inspct", "Transport-moving", "Handlers-cleaners",
              "Farming-fishing", "Protective-serv", "Other-service", "Priv-house-serv",
              "Armed-Forces", "Unknown"]
RELATIONSHIP = ["Husband", "Wife", "Own-child", "Not-in-family", "Other-relative", "Unmarried"]

st.set_page_config(page_title="Predicción de ingresos")
st.title("Predicción de ingresos (UCI Adult)")
st.caption(f"Consume la API en {API_URL}")

with st.form("solicitud"):
    izquierda, derecha = st.columns(2)
    solicitud = {
        "age": izquierda.number_input("Edad", 17, 100, 40),
        "workclass": izquierda.selectbox("Tipo de empleo", WORKCLASS),
        "education": izquierda.selectbox("Educación", EDUCATION, index=EDUCATION.index("Bachelors")),
        "marital_status": izquierda.selectbox("Estado civil", MARITAL),
        "occupation": derecha.selectbox("Ocupación", OCCUPATION),
        "relationship": derecha.selectbox("Rol en el hogar", RELATIONSHIP),
        "capital_gain": derecha.number_input("Ganancia de capital", 0, 100000, 0),
        "capital_loss": derecha.number_input("Pérdida de capital", 0, 5000, 0),
        "hours_per_week": derecha.number_input("Horas por semana", 1, 99, 45),
    }
    enviado = st.form_submit_button("Predecir")

if enviado:
    try:
        # Connection: close abre una conexión por petición, para que el Service pueda
        # repartirlas entre pods; con keep-alive se quedarían en uno solo.
        respuesta = requests.post(
            f"{API_URL}/predecir", json=solicitud, timeout=10,
            headers={"Connection": "close"},
        )
        respuesta.raise_for_status()
    except requests.RequestException as error:
        st.error(f"La API no respondió correctamente: {error}")
    else:
        datos = respuesta.json()
        st.subheader(">50K" if datos["prediccion"] == 1 else "<=50K")
        st.metric("Probabilidad de >50K", f"{datos['probabilidad']:.1%}")
        st.write(f"**Pod que respondió:** `{datos['pod']}`")
        st.write(f"**Modelo:** `{datos['modelo']}` v{datos['version_modelo']}")
        st.write(f"**Run:** `{datos['run_id']}`")
