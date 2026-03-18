import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from unidecode import unidecode
from PIL import Image

# ----------------------------
# LOGO
# ----------------------------
logo = Image.open("logo.png")
st.image(logo, width=400)

# ----------------------------
# ESTILOS (BOTÓN CORREGIDO)
# ----------------------------
page_bg_style = '''
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(to bottom right, #eaeaea, #ffffff);
    background-attachment: fixed;
}

[data-testid="stSidebar"] {
    background-color: #eaeaea;
}

h1, h2, h3, h4, h5, h6, p, label {
    color: #a81e35;
}

/* BOTÓN */
.stButton > button {
    background-color: #a81e35 !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 8px 16px !important;
    font-weight: bold !important;
    color: white !important; /* 🔥 clave */
}

/* 🔥 FORZAR TEXTO (TODAS LAS CAPAS) */
.stButton > button * {
    color: white !important;
    fill: white !important;
}

/* HOVER */
.stButton > button:hover {
    background-color: #000000 !important;
    color: white !important;
}

.stButton > button:hover * {
    color: white !important;
}
</style>
'''
st.markdown(page_bg_style, unsafe_allow_html=True)

# ----------------------------
# NORMALIZAR
# ----------------------------
def normalizar(txt):
    txt = str(txt)
    txt = txt.replace("\n", " ").replace("\r", " ")
    txt = unidecode(txt.lower().strip())
    txt = re.sub(r'\s+', ' ', txt)
    return txt

# ----------------------------
# EXTRAER CÓDIGOS PDF
# ----------------------------
def extraer_codigos_pdf(pdf_bytes):
    registros = []
    patron_codigo = r'\b\d{6}[A-Z0-9]{2,4}\b'

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pagina in pdf.pages:
            texto = pagina.extract_text()
            if not texto:
                continue

            codigos = re.findall(patron_codigo, texto)

            for c in codigos:
                registros.append({"catalogo": c})

    if not registros:
        return pd.DataFrame(columns=["catalogo"])

    return pd.DataFrame(registros)

# ----------------------------
# UI
# ----------------------------
st.title("📘 Validación: Informe Académico")
st.markdown("**Leyenda:** 🔴 Curso no coincide | 🟢 Coincidencias EXACTAS en Planes 2026")

# ----------------------------
# CARGAR EXCEL
# ----------------------------
try:
    df_base = pd.read_excel("planes_cursos_2026_v03.xlsx")
    df_base.columns = df_base.columns.str.strip()
    df_base["catalogo_norm"] = df_base["Catálogo"].apply(normalizar)
    st.success("✅ Base de datos cargada correctamente")
except:
    st.error("No se encontró el Excel.")
    st.stop()

# ----------------------------
# FILTROS
# ----------------------------
subgrados = sorted(df_base["Subgrado"].dropna().unique())
subgrado = st.selectbox("Seleccione Subgrado", [""] + subgrados)

carrera = ""
if subgrado:
    carreras = sorted(df_base[df_base["Subgrado"]==subgrado]["Descr"].dropna().unique())
    carrera = st.selectbox("Seleccione Carrera", [""] + list(carreras))

# ----------------------------
# PDF
# ----------------------------
pdf_file = st.file_uploader("Sube PDF", type=["pdf"])

# ----------------------------
# BOTÓN
# ----------------------------
if st.button("Validar Catálogos del informe"):

    if not subgrado or not carrera or pdf_file is None:
        st.error("Completa todos los campos")
        st.stop()

    pdf_bytes = pdf_file.getvalue()
    df_pdf = extraer_codigos_pdf(pdf_bytes)

    if df_pdf.empty:
        st.error("No se detectaron códigos")
        st.stop()

    df_pdf["catalogo_norm"] = df_pdf["catalogo"].apply(normalizar)

    # 🔥 BASE FILTRADA
    base = df_base[
        (df_base["Subgrado"]==subgrado) &
        (df_base["Descr"]==carrera)
    ].copy()

    # 🔥 ERRORES
    errores = df_pdf[
        ~df_pdf["catalogo_norm"].isin(base["catalogo_norm"])
    ]

    # ----------------------------
    # RESULTADOS
    # ----------------------------
    if errores.empty:
        st.success("✅ Todo coincide correctamente")
    else:
        st.warning(f"⚠️ {len(errores)} cursos no pertenecen a la carrera")

        html = "<table style='border-collapse: collapse; width:100%;'>"
        html += "<tr><th style='border:1px solid black;'>Código PDF</th>"
        html += "<th style='border:1px solid black;'>Curso (Correcto)</th>"
        html += "<th style='border:1px solid black;'>Coincidencias EXACTAS</th></tr>"

        for _, row in errores.iterrows():

            codigo = row["catalogo"]

            # 🔥 CURSO DESDE TODO EL EXCEL
            curso_df = df_base[
                df_base["catalogo_norm"] == row["catalogo_norm"]
            ]["Nom_Largo"]

            if not curso_df.empty:
                curso_real = curso_df.iloc[0]
            else:
                curso_real = "No encontrado"

            # 🔥 COINCIDENCIAS EN BASE FILTRADA
            matches = base[
                base["Nom_Largo"] == curso_real
            ]

            sugerencias_html = "<table style='width:100%;'>"
            sugerencias_html += "<tr><th>Plan</th><th>Código</th><th>Curso</th></tr>"

            for _, r in matches.iterrows():
                sugerencias_html += "<tr>"
                sugerencias_html += f"<td>{r.get('Plan Acad','')}</td>"
                sugerencias_html += f"<td>{r.get('Catálogo','')}</td>"
                sugerencias_html += f"<td>{r.get('Nom_Largo','')}</td>"
                sugerencias_html += "</tr>"

            sugerencias_html += "</table>"

            html += "<tr>"
            html += f"<td style='background:#ffc7ce;'>{codigo}</td>"
            html += f"<td style='background:#ffc7ce;'>{curso_real}</td>"
            html += f"<td style='background:#c6efce;'>{sugerencias_html}</td>"
            html += "</tr>"

        html += "</table>"

        st.markdown(html, unsafe_allow_html=True)
