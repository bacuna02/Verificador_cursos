import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from unidecode import unidecode
from PIL import Image
import streamlit.components.v1 as components

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

    # 🔥 lista para resultados finales
    resultados_finales = []

    # ----------------------------
    # RESULTADOS
    # ----------------------------
    if errores.empty:
        st.success(f"✅ Se identificaron {total_catalogos} catálogos y todos corresponden correctamente")
    else:
        st.warning(f"⚠️ Se identificaron {total_catalogos} catálogos, de los cuales {len(errores)} no corresponden")

        html = "<table style='border-collapse: collapse; width:100%;'>"
        html += "<tr><th>Código PDF</th><th>Curso</th><th>Coincidencias EXACTAS</th></tr>"

        for _, row in errores.iterrows():

            codigo = row["catalogo"]

            curso_df = df_base[
                df_base["catalogo_norm"] == row["catalogo_norm"]
            ]["Nom_Largo"]

            curso_real = curso_df.iloc[0] if not curso_df.empty else "No encontrado"

            matches = base[
                base["Nom_Largo"] == curso_real
            ]

            sugerencias_html = "<table style='width:100%;'>"
            sugerencias_html += "<tr><th>Plan</th><th>Código</th><th>Curso</th></tr>"

            for _, r in matches.iterrows():

                # 🔥 guardar resultado final
                resultados_finales.append({
                    "Plan": r.get("Plan Acad", ""),
                    "Catálogo": r.get("Catálogo", ""),
                    "Curso": r.get("Nom_Largo", "")
                })

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

    # 🔥 RESULTADO FINAL SOLO PARA COPIAR
    if resultados_finales:
        df_final = pd.DataFrame(resultados_finales).drop_duplicates()

        st.markdown("### 📋 Copiar y pegar en Excel")

        texto_copiable = df_final.to_csv(sep="\t", index=False).strip()

st.markdown("### 📋 Copiar y pegar en Excel")

components.html(f"""
<textarea id="texto" style="width:100%; height:150px;">
{texto_copiable}
</textarea>

<br>

<button onclick="copiarTexto()" style="
    background-color:#a81e35;
    color:white;
    padding:10px 20px;
    border:none;
    border-radius:8px;
    font-weight:bold;
    cursor:pointer;
">
📋 Copiar al portapapeles
</button>

<script>
function copiarTexto() {{
    var copyText = document.getElementById("texto");
    copyText.select();
    copyText.setSelectionRange(0, 99999);
    document.execCommand("copy");

    alert("Copiado al portapapeles ✅");
}}
</script>
""", height=250)
