import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from unidecode import unidecode
from rapidfuzz import process, fuzz

# ----------------------------
# FONDO DEGRADADO MODERNO
# ----------------------------
page_bg_style = '''
<style>
/* Fondo principal con degradado gris a blanco */
[data-testid="stAppViewContainer"] {
    background: linear-gradient(to bottom right, #eaeaea, #ffffff);
    background-attachment: fixed;
}

/* Sidebar con fondo gris uniforme */
[data-testid="stSidebar"] {
    background-color: #eaeaea;
}

/* Texto principal y títulos en rojo */
h1, h2, h3, h4, h5, h6, p, label {
    color: #a81e35;
}

/* Botones con estilo moderno en rojo y blanco */
.stButton>button {
    background-color: #a81e35 !important;  /* Fondo rojo vino */
    color: #ffffff !important;             /* Texto blanco */
    border-radius: 8px;
    border: none;
    padding: 0.35em 0.75em;
    font-weight: bold;
}

/* Hover de botón: rojo más oscuro (negro suave) */
.stButton>button:hover {
    background-color: #000000 !important;  /* Negro al pasar el mouse */
    color: #ffffff !important;             /* Mantener texto blanco */
}
</style>
'''
st.markdown(page_bg_style, unsafe_allow_html=True)

# ----------------------------
# FUNCIONES AUXILIARES
# ----------------------------
def normalizar(txt):
    txt = str(txt)
    txt = unidecode(txt.lower().strip())
    txt = re.sub(r'\s+', ' ', txt)
    return txt

def extraer_codigos_pdf(pdf_bytes):
    registros = []
    patron_codigo = r'\b\d{6}[A-Z0-9]{2,4}\b'
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        for pagina in pdf.pages:
            palabras = pagina.extract_words()
            for i, w in enumerate(palabras):
                texto = w["text"]
                if re.match(patron_codigo, texto):
                    codigo = texto
                    curso = ""
                    for j in range(1,6):
                        if i+j < len(palabras):
                            curso += " " + palabras[i+j]["text"]
                    registros.append({"catalogo": codigo, "curso": curso.strip()})
    return pd.DataFrame(registros)

# ----------------------------
# TÍTULO
# ----------------------------
st.title("📘 Validación: Informe Académico")
st.markdown("**Leyenda:** 🔴 Curso no coincide | 🟢 Posibles coincidencias En Planes 2026")

# ----------------------------
# CARGAR EXCEL FIJO
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
pdf_file = st.file_uploader("Sube el PDF con los cursos", type=["pdf"])

# ----------------------------
# BOTÓN COMPARAR
# ----------------------------
if st.button("Comparar"):
    if not subgrado or not carrera or pdf_file is None:
        st.error("Debes seleccionar Subgrado, Carrera y subir un PDF")
    else:
        pdf_bytes = pdf_file.getvalue()
        df_pdf = extraer_codigos_pdf(pdf_bytes)
        st.write("Códigos detectados en PDF:", df_pdf["catalogo"].unique())

        # Normalizar
        df_pdf["catalogo_norm"] = df_pdf["catalogo"].apply(normalizar)
        base = df_base[(df_base["Subgrado"]==subgrado) & (df_base["Descr"]==carrera)].copy()
        base["catalogo_norm"] = base["Catálogo"].apply(normalizar)
        base["curso_norm"] = base["Nom_Largo"].apply(normalizar)

        # Merge para detectar errores
        merge = df_pdf.merge(base, left_on="catalogo_norm", right_on="catalogo_norm", how="left", indicator=True)
        errores = merge[merge["_merge"]=="left_only"]

        if errores.empty:
            st.success("✅ Todo coincide correctamente")
        else:
            st.warning(f"⚠️ Se detectaron {len(errores)} discrepancias")

            # Crear tabla HTML principal
            html = "<table style='border-collapse: collapse; width:100%;'>"
            html += "<tr><th style='border: 1px solid black; text-align:center;'>Código en PDF</th>"
            html += "<th style='border: 1px solid black; text-align:center;'>Curso detectado PDF</th>"
            html += "<th style='border: 1px solid black; text-align:center;'>Posibles coincidencias En Planes_2026</th></tr>"

            for _, row in errores.iterrows():
                curso_pdf = normalizar(row["curso"])
                posibles = process.extract(
                    curso_pdf,
                    base["curso_norm"],
                    scorer=fuzz.token_sort_ratio,
                    limit=3
                )

                # Crear subtabla HTML
                sugerencias_list = []
                for p in posibles:
                    curso_norm = p[0]
                    matches = base[base["curso_norm"] == curso_norm]
                    for _, r in matches.iterrows():
                        plan_acad = r.get("Plan Acad", "Sin Plan")
                        catalogo = r.get("Catálogo", "Sin Catálogo")
                        nom_largo = r.get("Nom_Largo", "Sin Nombre")
                        entry = (plan_acad, catalogo, nom_largo)
                        if entry not in sugerencias_list:
                            sugerencias_list.append(entry)

                sugerencias_html = "<table style='border-collapse: collapse; width:100%;'>"
                sugerencias_html += "<tr><th style='border: 1px solid black; text-align:center;'>Plan Acad</th>"
                sugerencias_html += "<th style='border: 1px solid black; text-align:center;'>Catálogo</th>"
                sugerencias_html += "<th style='border: 1px solid black; text-align:center;'>Curso</th></tr>"

                for plan_acad, catalogo, nom_largo in sugerencias_list:
                    sugerencias_html += "<tr>"
                    sugerencias_html += f"<td style='border: 1px solid black; text-align:center;'>{plan_acad}</td>"
                    sugerencias_html += f"<td style='border: 1px solid black; text-align:center;'>{catalogo}</td>"
                    sugerencias_html += f"<td style='border: 1px solid black; text-align:left;'>{nom_largo}</td>"
                    sugerencias_html += "</tr>"

                sugerencias_html += "</table>"

                # Añadir fila principal con subtabla
                html += "<tr>"
                html += f"<td style='border: 1px solid black; text-align:center; background-color:#ffc7ce;'>{row['catalogo']}</td>"
                html += f"<td style='border: 1px solid black; text-align:center; background-color:#ffc7ce;'>{row['curso']}</td>"
                html += f"<td style='border: 1px solid black; background-color:#c6efce;'>{sugerencias_html}</td>"
                html += "</tr>"

            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)
