        html = "<table style='border-collapse: collapse; width:100%;'>"

        # 🔥 ENCABEZADO AGRUPADO
        html += """
        <tr>
            <th colspan='2' style='border:1px solid #999; background:#f4b6b6; text-align:center; font-weight:bold;'>
                CATÁLOGOS INCORRECTOS
            </th>
            <th colspan='3' style='border:1px solid #999; background:#b6d7a8; text-align:center; font-weight:bold;'>
                COINCIDENCIAS ENCONTRADAS EN EL PLAN
            </th>
        </tr>
        """

        # 🔥 ENCABEZADOS NORMALES
        html += """
        <tr>
            <th style='border:1px solid #999;'>Catálogo</th>
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
