# ----------------------------
# BOTÓN
# ----------------------------
if st.button("Validar Catálogos del informe"):
    if not subgrado or not carrera or pdf_file is None:
        st.error("Debes seleccionar Subgrado, Carrera y subir un PDF")
    else:
        pdf_bytes = pdf_file.getvalue()
        df_pdf = extraer_codigos_pdf(pdf_bytes)

        if df_pdf.empty:
            st.error("❌ No se pudieron detectar cursos en el PDF.")
            st.stop()

        total_codigos = df_pdf["catalogo"].nunique()
        st.info(f"📊 Total de catálogos hallados: {total_codigos}")
        st.write("Detalle:", df_pdf["catalogo"].unique())

        df_pdf["catalogo_norm"] = df_pdf["catalogo"].apply(normalizar)

        base = df_base[
            (df_base["Subgrado"]==subgrado) & 
            (df_base["Descr"]==carrera)
        ].copy()

        base["catalogo_norm"] = base["Catálogo"].apply(normalizar)

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
            html += "<th style='border: 1px solid black;'>Curso (Correcto)</th>"
            html += "<th style='border: 1px solid black;'>Coincidencias EXACTAS</th></tr>"

            for _, row in errores.iterrows():

                codigo = row["catalogo"]

                # 🔥 AQUÍ ESTÁ LA CLAVE
                # buscar en Excel el curso correcto por código
                curso_real = base[
                    base["catalogo_norm"] == row["catalogo_norm"]
                ]["Nom_Largo"]

                curso_real = curso_real.iloc[0] if not curso_real.empty else "No encontrado"

                # coincidencias exactas (ahora sí reales)
                matches_exactos = base[
                    base["Nom_Largo"] == curso_real
                ]

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
                html += f"<td style='background:#ffc7ce;'>{codigo}</td>"
                html += f"<td style='background:#ffc7ce;'>{curso_real}</td>"
                html += f"<td style='background:#c6efce;'>{sugerencias_html}</td>"
                html += "</tr>"

            html += "</table>"
            st.markdown(html, unsafe_allow_html=True)
