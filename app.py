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
# FONDO DEGRADADO MODERNO
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

.stButton>button {
    background-color: #a81e35 !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 0.35em 0.75em !important;
    font-weight: bold !important;
    color: #ffffff !important;
}

.stButton>button:hover {
    background-color: #000000 !important;
    color: #ffffff !important;
}

.stButton>button * {
    all: unset;
    color: #ffffff !important;
    font-weight: bold !important;
    font-family: inherit !important;
    text-align: center;
    display: inline-block;
}
</style>
'''

st.markdown(page_bg_style, unsafe_allow_html=True)

# ----------------------------
# FUNCIONES AUXILIARES
# ----------------------------
def normalizar(txt):
    txt = str(txt)
    txt = txt.replace("\n", " ").replace("\r", " ")
    txt = unidecode(txt.lower().strip())
    txt = re.sub(r'\s+', ' ', txt)
    return txt


# 🔥 FUNCIÓN CORRECTA (TABLAS)
def extraer_codigos_pdf(pdf_bytes):
    registros = []
    patron_codigo = r'\b\d{6}[A-Z0-9]{2,4}\b'

    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pagina in pdf.pages:

            tablas = pagina.extract_tables()

            for tabla in tablas:
                for fila in tabla:

                    if not fila:
                        continue

                    # limpiar celdas
                    fila = [str(c).strip() if c else "" for c in fila]

                    for i, celda in enumerate(fila):
                        if re.match(patron_codigo, celda):

                            codigo = celda

                            # tomar columna derecha como curso
                            curso = ""
                            if i + 1 < len(fila):
                                curso = fila[i + 1]

                            # limpiar números tipo créditos
                            curso = re.sub(r'\b\d+\b', '', curso)
                            curso = re.sub(r'\s+', ' ', curso).strip()

                            if curso:
                                registros.append({
                                    "catalogo": codigo,
                                    "curso": curso
                                })

    return pd.DataFrame(registros)


# ----------------------------
# TÍTULO
# ----------------------------
st.title("📘 Validación: Informe Académico")
st.markdown("**Leyenda:** 🔴 Curso no coincide | 🟢 Coincidencias EXACTAS en Planes 2026")

# ----------------------------
# CARGAR EXCEL
# ----------------------------
try:
    df_base = pd.read_excel("planes_cursos_2026_v03.xlsx")
    df_base.columns = df_base.columns.str.strip()
    st.success("✅ Base de datos cargada correctamente")
except FileNotFoundError:
    st.error("No se encontró 'planes_cursos_2026_v03.xlsx'.")
    st.stop()

# ----------------------------
# SELECTORES
# ----------------------------
subgrados = sorted(df_base["Subgrado"].dropna().unique())
subgrado = st.selectbox("Seleccione Subgrado", [""] + subgrados)

carrera = ""
if subgrado:
    carreras = sorted(df_base[df_base["Subgrado"]==subgrado]["Descr"].dropna().unique())
    carrera = st.selectbox("Seleccione Carrera", [""] + list(carreras))

# ----------------------------
# SUBIR PDF
# ----------------------------
pdf_file = st.file_uploader(
    "📂 Selecciona o arrastra tu PDF aquí",
    type=["pdf"]
)

# ----------------------------
# BOTÓN
# ----------------------------
if st.button("Validar Catálogos del informe"):
    if not subgrado or not carrera or pdf_file is None:
        st.error("Debes seleccionar Subgrado, Carrera y subir un PDF")
    else:
        pdf_bytes = pdf_file.getvalue()
        df_pdf = extraer_codigos_pdf(pdf_bytes)

        total_codigos = df_pdf["catalogo"].nunique()
        st.info(f"📊 Total de catálogos hallados: {total_codigos}")
        st.write("Detalle:", df_pdf["catalogo"].unique())

        df_pdf["catalogo_norm"] = df_pdf["catalogo"].apply(normalizar)
        df_pdf["curso_norm"] = df_pdf["curso"].apply(normalizar)

        base = df_base[
            (df_base["Subgrado"]==subgrado) & 
            (df_base["Descr"]==carrera)
        ].copy()

        base["catalogo_norm"] = base["Catálogo"].apply(normalizar)
        base["curso_norm"] = base["Nom_Largo"].apply(normalizar)

        merge = df_pdf.merge(
            base,
            on="catalogo_norm",
            how="left",
            indicator=True
        )

        errores = merge[merge["_merge"]=="left_only"]

        if errores.empty:
            st.success("✅ Todo coincide correctamente")
        else:
            st.warning(f"⚠️ Se detectaron {len(errores)} discrepancias")

            html = "<table style='border-collapse: collapse; width:100%;'>"
            html += "<tr><th style='border: 1px solid black;'>Código PDF</th>"
            html += "<th style='border: 1px solid black;'>Curso PDF</th>"
            html += "<th style='border: 1px solid black;'>Coincidencias EXACTAS</th></tr>"

            for _, row in errores.iterrows():
                curso_pdf = normalizar(row["curso"])

                matches_exactos = base[base["curso_norm"] == curso_pdf]

                sugerencias_html = "<table style='border-collapse: collapse; width:100%;'>"
                sugerencias_html += "<tr><th>Plan</th><th>Código</th><th>Curso</th></tr>"

                for _, r in matches_exactos.iterrows():
                    sugerencias_html += "<tr>"
                    sugerencias_html += f"<td>{r.get('Plan Acad','')}</td>"
                    sugerencias_html += f"<td>{r.get('Catálogo','')}</td>"
                    sugerencias_html += f"<td>{r.get('Nom_Largo','')}</td>"
                    sugerencias_html += "</tr>"

                sugerencias_html += "</table>"

                html += "<tr>"
                html += f"<td style='background:#ffc7ce;'>{row['catalogo']}</td>"
                html += f"<td style='background:#ffc7ce;'>{row['curso']}</td>"
                html += f"<td style='background:#c6efce;'>{sugerencias_html}</td>"
                html += "</tr>"

            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)
