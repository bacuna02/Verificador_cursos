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
# ESTILOS
# ----------------------------
page_bg_style = '''
<style>
[data-testid="stAppViewContainer"] {
    background: linear-gradient(to bottom right, #eaeaea, #ffffff);
}

.stButton>button {
    background-color: #a81e35 !important;
    border-radius: 8px !important;
    color: white !important;
    font-weight: bold !important;
}
</style>
'''
st.markdown(page_bg_style, unsafe_allow_html=True)

# ----------------------------
# FUNCIONES
# ----------------------------
def normalizar(txt):
    txt = str(txt)
    txt = txt.replace("\n", " ").replace("\r", " ")
    txt = unidecode(txt.lower().strip())
    txt = re.sub(r'\s+', ' ', txt)
    return txt


# 🔥 FUNCIÓN CORRECTA (ANTI-SALTOS DE LÍNEA)
def extraer_codigos_pdf(pdf_bytes):
    registros = []
    patron_codigo = r'\b\d{6}[A-Z0-9]{2,4}\b'

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pagina in pdf.pages:

            texto = pagina.extract_text()
            if not texto:
                continue

            lineas = [l.strip() for l in texto.split("\n") if l.strip()]

            i = 0
            while i < len(lineas):
                linea = lineas[i]

                match = re.search(patron_codigo, linea)

                if match:
                    codigo = match.group()
                    curso = ""

                    j = i + 1
                    while j < len(lineas):
                        siguiente = lineas[j]

                        # detener si aparece otro código
                        if re.search(patron_codigo, siguiente):
                            break

                        # ignorar encabezados
                        if siguiente.lower() in ["plan", "código", "curso"]:
                            j += 1
                            continue

                        # ignorar líneas solo numéricas
                        if re.fullmatch(r'[\d\s]+', siguiente):
                            j += 1
                            continue

                        # 🔥 unir líneas del curso
                        curso += " " + siguiente
                        j += 1

                    curso = re.sub(r'\b\d+\b', '', curso)
                    curso = re.sub(r'\s+', ' ', curso).strip()

                    registros.append({
                        "catalogo": codigo,
                        "curso": curso
                    })

                    i = j
                else:
                    i += 1

    if not registros:
        return pd.DataFrame(columns=["catalogo", "curso"])

    return pd.DataFrame(registros)


# ----------------------------
# UI
# ----------------------------
st.title("📘 Validación: Informe Académico")

# ----------------------------
# CARGAR EXCEL
# ----------------------------
try:
    df_base = pd.read_excel("planes_cursos_2026_v03.xlsx")
    df_base.columns = df_base.columns.str.strip()
    st.success("✅ Base cargada")
except:
    st.error("Falta el Excel")
    st.stop()

# ----------------------------
# FILTROS
# ----------------------------
subgrado = st.selectbox("Subgrado", [""] + sorted(df_base["Subgrado"].dropna().unique()))

carrera = ""
if subgrado:
    carrera = st.selectbox(
        "Carrera",
        [""] + sorted(df_base[df_base["Subgrado"] == subgrado]["Descr"].dropna().unique())
    )

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

    df_pdf = extraer_codigos_pdf(pdf_file.getvalue())

    if df_pdf.empty:
        st.error("❌ No se detectaron cursos en el PDF")
        st.stop()

    st.write("Vista previa PDF detectado:")
    st.dataframe(df_pdf)

    df_pdf["catalogo_norm"] = df_pdf["catalogo"].apply(normalizar)
    df_pdf["curso_norm"] = df_pdf["curso"].apply(normalizar)

    base = df_base[
        (df_base["Subgrado"] == subgrado) &
        (df_base["Descr"] == carrera)
    ].copy()

    base["catalogo_norm"] = base["Catálogo"].apply(normalizar)
    base["curso_norm"] = base["Nom_Largo"].apply(normalizar)

    merge = df_pdf.merge(base, on="catalogo_norm", how="left", indicator=True)

    errores = merge[merge["_merge"] == "left_only"]

    st.write(f"📊 Total detectados: {df_pdf['catalogo'].nunique()}")

    if errores.empty:
        st.success("✅ Todo coincide")
    else:
        st.warning(f"⚠️ {len(errores)} discrepancias")

        st.dataframe(errores[["catalogo", "curso"]])
