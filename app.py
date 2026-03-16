import streamlit as st
import pandas as pd
import pdfplumber
import io
import re
from unidecode import unidecode
from rapidfuzz import process, fuzz

# ----------------------------
# FUNCIONES AUXILIARES
# ----------------------------
def normalizar(txt):
    """Normaliza texto: minúsculas, sin acentos y sin espacios extra"""
    txt = str(txt)
    txt = unidecode(txt.lower().strip())
    txt = re.sub(r'\s+', ' ', txt)
    return txt

def extraer_codigos_pdf(pdf_bytes):
    """Extrae códigos y cursos de un PDF"""
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
                    registros.append({
                        "catalogo": codigo,
                        "curso": curso.strip()
                    })
    return pd.DataFrame(registros)

# ----------------------------
# TÍTULO
# ----------------------------
st.title("📘 Comparador de Cursos PDF vs Excel")
st.markdown("**Leyenda:** 🔴 Curso no coincide | 🟢 Posibles coincidencias Excel")

# ----------------------------
# CARGAR EXCEL FIJO
# ----------------------------
try:
    df_base = pd.read_excel("planes_cursos_2026_v03.xlsx")
    df_base.columns = df_base.columns.str.strip()
    st.success("✅ Base de datos cargada correctamente")
except FileNotFoundError:
    st.error("No se encontró 'planes_cursos_2026_v03.xlsx'. Asegúrate que esté en la misma carpeta que este archivo.")
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
        # Leer PDF
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
            sugerencias = []

            for _, row in errores.iterrows():
                curso_pdf = normalizar(row["curso"])
                posibles = process.extract(
                    curso_pdf,
                    base["curso_norm"],
                    scorer=fuzz.token_sort_ratio,
                    limit=3
                )
                sug = []
                for p in posibles:
                    fila = base[base["curso_norm"]==p[0]].iloc[0]
                    # Agregar salto de línea entre sugerencias
                    sug.append(f'{fila["Catálogo"]} - {fila["Nom_Largo"]}')
                sugerencias.append("\n".join(sug))  # <--- salto de línea vertical

            errores["Sugerencias"] = sugerencias
            resultado = errores[["catalogo","curso","Sugerencias"]].copy()
            resultado.columns = ["Código en PDF","Curso detectado PDF","Posibles coincidencias en Planes_2026"]

            # Colorear filas
            def color_filas(row):
                colores = []
                for col in row.index:
                    if col == "Posibles coincidencias Excel":
                        colores.append("background-color:#c6efce")  # verde claro
                    else:
                        colores.append("background-color:#ffc7ce")  # rojo
                return colores

            # Mostrar tabla coloreada
            st.dataframe(resultado.style.apply(color_filas, axis=1))
