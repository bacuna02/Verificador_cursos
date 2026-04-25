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
    background-attachment: fixed;
}

[data-testid="stSidebar"] {
    background-color: #eaeaea;
}

h1, h2, h3, h4, h5, h6, p, label {
    color: #a81e35;
}

.stButton > button {
    background-color: #a81e35 !important;
    border-radius: 8px !important;
    border: none !important;
    padding: 8px 16px !important;
    font-weight: bold !important;
    color: white !important;
}

.stButton > button * {
    color: white !important;
    fill: white !important;
}

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

# ----------------------------
# CARGAR EXCEL
# ----------------------------
try:
    df_base = pd.read_excel("planes_cursos_2026_v03.xlsx")
    df_base.columns = df_base.columns.str.strip()
    df_base["catalogo_norm"] = df_base["Catálogo"].apply(normalizar)
    df_base["nom_largo_norm"] = df_base["Nom_Largo"].apply(normalizar)
    st.success("✅ Base de Planes 2026 cargada correctamente")
except:
    st.error("No se encontró el Excel.")
    st.stop()

# ----------------------------
# FILTROS
# ----------------------------
subgrados = sorted(df_base["Subgrado"].dropna().unique())
subgrado = st.selectbox("Seleccione Subgrado:", [""] + subgrados)

carrera = ""
if subgrado:
    carreras = sorted(df_base[df_base["Subgrado"]==subgrado]["Descr"].dropna().unique())
    carrera = st.selectbox("Seleccione Carrera:", [""] + list(carreras))

# ----------------------------
# PDF
# ----------------------------
pdf_file = st.file_uploader("Carga el Informe de Convalidación:", type=["pdf"])

# ----------------------------
# BOTÓN
# ----------------------------
if st.button("Validar Catálogos"):

    if not subgrado or not carrera or pdf_file is None:
        st.error("Completa todos los campos")
        st.stop()

    pdf_bytes = pdf_file.getvalue()
    df_pdf = extraer_codigos_pdf(pdf_bytes)

    if df_pdf.empty:
        st.error("No se detectaron códigos")
        st.stop()

    df_pdf["catalogo_norm"] = df_pdf["catalogo"].apply(normalizar)

    total_catalogos = df_pdf["catalogo"].nunique()

    base = df_base[
        (df_base["Subgrado"]==subgrado) &
        (df_base["Descr"]==carrera)
    ].copy()

    errores = df_pdf[
        ~df_pdf["catalogo_norm"].isin(base["catalogo_norm"])
    ]

    resultados_finales = []

    # ----------------------------
    # RESULTADOS
    # ----------------------------
    if errores.empty:
        st.success(f"✅ Se identificaron {total_catalogos} catálogos y todos corresponden correctamente")
    else:
        st.warning(f"⚠️ Se identificaron {total_catalogos} catálogos, de los cuales {len(errores)} no corresponden")

html = "<table style='border-collapse: collapse; width:100%;'>"

# 🔥 NUEVA FILA AGRUPADA
html += """
<tr>
    <th colspan='2' style='border:1px solid #999; background:#f4b6b6; text-align:center;'>
        CATÁLOGOS INCORRECTOS
    </th>
    <th colspan='3' style='border:1px solid #999; background:#b6d7a8; text-align:center;'>
        COINCIDENCIAS ENCONTRADAS EN EL PLAN
    </th>
</tr>
"""

# 🔥 ENCABEZADOS NORMALES
html += """
<tr>
    <th style='border:1px solid #999;'>Código PDF</th>
    <th style='border:1px solid #999;'>Curso</th>
    <th style='border:1px solid #999;'>Plan</th>
    <th style='border:1px solid #999;'>Catálogo</th>
    <th style='border:1px solid #999;'>Curso</th>
</tr>
"""

        for _, row in errores.iterrows():

            codigo = row["catalogo"]

            curso_df = df_base[
                df_base["catalogo_norm"] == row["catalogo_norm"]
            ]["Nom_Largo"]

            curso_real = curso_df.iloc[0] if not curso_df.empty else "No encontrado"

            matches = base[
                base["Nom_Largo"] == curso_real
            ]

            n = len(matches)

            if n == 0:
                html += f"""
                <tr>
                    <td style='border:1px solid #999; background:#ffc7ce;'>{codigo}</td>
                    <td style='border:1px solid #999; background:#ffc7ce;'>{curso_real}</td>
                    <td colspan='3' style='border:1px solid #999;'>Sin coincidencias</td>
                </tr>
                """
                continue

            first = True
            for _, r in matches.iterrows():

                resultados_finales.append({
                    "Plan": r.get("Plan Acad", ""),
                    "Catálogo": r.get("Catálogo", ""),
                    "Curso": r.get("Nom_Largo", "")
                })

                if first:
                    html += "<tr>"
                    html += f"<td rowspan='{n}' style='border:1px solid #999; background:#ffc7ce;'>{codigo}</td>"
                    html += f"<td rowspan='{n}' style='border:1px solid #999; background:#ffc7ce;'>{curso_real}</td>"
                    html += f"<td style='border:1px solid #999; background:#c6efce;'>{r.get('Plan Acad','')}</td>"
                    html += f"<td style='border:1px solid #999; background:#c6efce;'>{r.get('Catálogo','')}</td>"
                    html += f"<td style='border:1px solid #999; background:#c6efce;'>{r.get('Nom_Largo','')}</td>"
                    html += "</tr>"
                    first = False
                else:
                    html += "<tr>"
                    html += f"<td style='border:1px solid #999; background:#c6efce;'>{r.get('Plan Acad','')}</td>"
                    html += f"<td style='border:1px solid #999; background:#c6efce;'>{r.get('Catálogo','')}</td>"
                    html += f"<td style='border:1px solid #999; background:#c6efce;'>{r.get('Nom_Largo','')}</td>"
                    html += "</tr>"

        html += "</table>"

        st.markdown(html, unsafe_allow_html=True)

    # ----------------------------
    # TEXTO PARA COPIAR
    # ----------------------------
    if resultados_finales:
        df_final = pd.DataFrame(resultados_finales).drop_duplicates()

        st.markdown("### 📋 Listo para pegar en Zendesk :")

        texto_copiable = df_final.to_csv(sep="\t", index=False)

        st.text_area(
            "",
            texto_copiable,
            height=200
        )

        st.caption("Selecciona todo (Ctrl + A) y copia (Ctrl + C)")
