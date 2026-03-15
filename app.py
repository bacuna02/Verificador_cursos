import streamlit as st
import pandas as pd
import pdfplumber
import re
from unidecode import unidecode
from rapidfuzz import process, fuzz
import io

# Funciones auxiliares
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

# Título de la app
st.title("📘 Comparador de Cursos PDF vs Excel")

# Cargar Excel fijo
try:
    df_base = pd.read_excel("planes_cursos_2026_v03.xlsx")
    df_base.columns = df_base.columns.str.strip()
    st.success("✅ Base de datos cargada correctamente")
except FileNotFoundError:
    st.error("No se encontró planes_cursos_2026_v03.xlsx. Asegúrate que esté en la misma carpeta que este archivo.")
    st.stop()

# Selectores
subgrados = sorted(df_base["Subgrado"].dropna().unique())
subgrado = st.selectbox("Seleccione Subgrado", [""] + subgrados)

carrera = ""
if subgrado:
    carreras = sorted(df_base[df_base["Subgrado"]==subgrado]["Descr"].dropna().unique())
    carrera = st.selectbox("Seleccione Carrera", [""] + list(carreras))

# Subir PDF
pdf_file = st.file_uploader("Sube el PDF con los cursos", type=["pdf"])

# Botón Comparar
if st.button("Comparar"):
    if not subgrado or not carrera or pdf_file is None:
        st.error("Debes seleccionar Subgrado, Carrera y subir un PDF")
    else:
        base = df_base[(df_base["Subgrado"]==subgrado) & (df_base["Descr"]==carrera)].copy()
        df_pdf = extraer_codigos_pdf(pdf_file.read())
        df_pdf["catalogo_norm"] = df_pdf["catalogo"].apply(normalizar)
        base["catalogo_norm"] = base["Catálogo"].apply(normalizar)
        base["curso_norm"] = base["Nom_Largo"].apply(normalizar)

        merge = df_pdf.merge(base, left_on="catalogo_norm", right_on="catalogo_norm", how="left", indicator=True)
        errores = merge[merge["_merge"]=="left_only"]

        if errores.empty:
            st.success("✅ Todo coincide correctamente")
        else:
            st.warning("⚠️ Se detectaron discrepancias")
            sugerencias = []
            for _, row in errores.iterrows():
                curso_pdf = normalizar(row["curso"])
                posibles = process.extract(curso_pdf, base["curso_norm"], scorer=fuzz.token_sort_ratio, limit=3)
                sug = []
                for p in posibles:
                    fila = base[base["curso_norm"]==p[0]].iloc[0]
                    sug.append(f'{fila["Catálogo"]} - {fila["Nom_Largo"]}')
                sugerencias.append(", ".join(sug))
            errores["Sugerencias"] = sugerencias
            errores_display = errores[["catalogo","curso","Sugerencias"]]
            errores_display.columns = ["Código en PDF", "Curso detectado PDF", "Posibles coincidencias Excel"]
            st.dataframe(errores_display)