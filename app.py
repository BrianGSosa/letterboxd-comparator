from pathlib import Path

import pandas as pd
import streamlit as st

from src.letterboxd_scraper import get_watchlist
from src.letterboxd_comparator import compare_users


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"

st.set_page_config(
    page_title="Letterboxd Watchlist Comparator",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 Letterboxd Watchlist Comparator")
st.write(
    "Compara las watchlists públicas de dos usuarios y explora las películas "
    "que tienen en común."
)

with st.sidebar:
    st.header("Configuración")
    delay_seconds = st.number_input(
        "Pausa entre peticiones (segundos)",
        min_value=0.0,
        max_value=10.0,
        value=1.0,
        step=0.5,
        help="Una pausa ayuda a evitar demasiadas peticiones seguidas a Letterboxd.",
    )
    st.caption("La comparación se ejecuta en tu PC.")

with st.form("compare_form"):
    col_a, col_b = st.columns(2)
    with col_a:
        user_a = st.text_input(
            "Primer usuario",
            placeholder="Ej. usuario1",
            help="Introduce el nombre de usuario, no la URL completa.",
        ).strip()
    with col_b:
        user_b = st.text_input(
            "Segundo usuario",
            placeholder="Ej. usuario2",
            help="Introduce el nombre de usuario, no la URL completa.",
        ).strip()

    submitted = st.form_submit_button(
        "Comparar watchlists",
        type="primary",
        use_container_width=True,
    )

if submitted:
    if not user_a or not user_b:
        st.error("Introduce los dos nombres de usuario.")
    elif user_a.casefold() == user_b.casefold():
        st.error("Debes introducir dos usuarios diferentes.")
    elif any(char in user_a + user_b for char in ("/", "\\", ":", "*", "?", '"', "<", ">", "|")):
        st.error("Los nombres de usuario contienen caracteres no válidos.")
    else:
        try:
            DATA_DIR.mkdir(parents=True, exist_ok=True)
            with st.status("Consultando Letterboxd y comparando las watchlists…", expanded=True) as status:
                st.write(f"Descargando la watchlist de **{user_a}**…")
                get_watchlist(
                    user_a,
                    output_dir=DATA_DIR,
                    delay_seconds=delay_seconds,
                )

                st.write(f"Descargando la watchlist de **{user_b}**…")
                get_watchlist(
                    user_b,
                    output_dir=DATA_DIR,
                    delay_seconds=delay_seconds,
                )

                st.write("Buscando películas compartidas…")
                result = compare_users(
                    user_a,
                    user_b,
                    data_dir=DATA_DIR,
                    output_dir=DATA_DIR,
                )

                output_file = Path(result["output_file"])
                df = pd.read_csv(output_file, encoding="utf-8-sig", dtype={"year": str})
                df = df.reindex(columns=["title", "year", "url"])
                df["year"] = df["year"].fillna("").astype(str).str.replace(r"\.0$", "", regex=True)
                st.session_state["comparison_df"] = df
                st.session_state["comparison_summary"] = result
                st.session_state["comparison_users"] = (user_a, user_b)
                st.session_state["comparison_file"] = str(output_file)
                status.update(label="Comparación completada", state="complete", expanded=False)
        except Exception as exc:
            st.error(f"No se pudo completar la comparación: {exc}")
            st.caption(
                "Comprueba que los nombres sean correctos, que las watchlists sean públicas "
                "y que tengas conexión a internet."
            )

if "comparison_df" in st.session_state:
    df = st.session_state["comparison_df"].copy()
    summary = st.session_state.get("comparison_summary", {})
    previous_users = st.session_state.get("comparison_users", ("Usuario 1", "Usuario 2"))

    st.divider()
    st.subheader(f"Resultados: {previous_users[0]} y {previous_users[1]}")

    metric_cols = st.columns(5)
    metric_cols[0].metric(f"Películas de {previous_users[0]}", summary.get("total_a", "—"))
    metric_cols[1].metric(f"Películas de {previous_users[1]}", summary.get("total_b", "—"))
    metric_cols[2].metric("Películas compartidas", summary.get("common_count", len(df)))
    metric_cols[3].metric(f"Coincidencia de {previous_users[0]}", f'{summary.get("overlap_a_pct", "—")}%')
    metric_cols[4].metric("Índice Jaccard", f'{summary.get("jaccard_pct", "—")}%')

    st.subheader("Explorar películas")
    controls = st.columns([2, 1, 1, 1])
    with controls[0]:
        search_text = st.text_input(
            "Buscar por título",
            placeholder="Escribe parte del título…",
        ).strip()
    with controls[1]:
        sort_option = st.selectbox(
            "Ordenar por",
            [
                "Título (A–Z)",
                "Título (Z–A)",
                "Año (más antiguo)",
                "Año (más reciente)",
            ],
        )
    with controls[2]:
        result_limit = st.selectbox(
            "Resultados visibles",
            [10, 25, 50, 100, "Todos"],
            index=1,
        )
    with controls[3]:
        years = sorted(
            {year for year in df["year"].tolist() if year and year.lower() != "nan"},
            reverse=True,
        )
        year_options = ["Todos"] + years + (["Sin año"] if (df["year"] == "").any() else [])
        selected_years = st.multiselect(
            "Filtrar por año",
            options=year_options,
            default=["Todos"],
        )

    filtered = df.copy()

    if search_text:
        filtered = filtered[
            filtered["title"].fillna("").str.contains(search_text, case=False, regex=False)
        ]

    if not selected_years or "Todos" in selected_years:
        pass
    else:
        selected_real_years = [year for year in selected_years if year != "Sin año"]
        year_mask = filtered["year"].isin(selected_real_years)
        if "Sin año" in selected_years:
            year_mask = year_mask | (filtered["year"] == "")
        filtered = filtered[year_mask]

    if sort_option == "Título (A–Z)":
        filtered = filtered.sort_values("title", key=lambda col: col.str.casefold(), ascending=True)
    elif sort_option == "Título (Z–A)":
        filtered = filtered.sort_values("title", key=lambda col: col.str.casefold(), ascending=False)
    elif sort_option == "Año (más antiguo)":
        filtered = filtered.assign(_year_num=pd.to_numeric(filtered["year"], errors="coerce"))
        filtered = filtered.sort_values(["_year_num", "title"], ascending=[True, True], na_position="last").drop(columns="_year_num")
    else:
        filtered = filtered.assign(_year_num=pd.to_numeric(filtered["year"], errors="coerce"))
        filtered = filtered.sort_values(["_year_num", "title"], ascending=[False, True], na_position="last").drop(columns="_year_num")

    st.write(f"**{len(filtered):,}** películas coinciden con la búsqueda y los filtros.")

    visible = filtered if result_limit == "Todos" else filtered.head(int(result_limit))
    st.dataframe(
        visible,
        use_container_width=True,
        hide_index=True,
        column_config={
            "title": st.column_config.TextColumn("Título"),
            "year": st.column_config.TextColumn("Año"),
            "url": st.column_config.LinkColumn("Letterboxd", display_text="Abrir película"),
        },
    )

    st.download_button(
        label="Descargar resultados filtrados en CSV",
        data=filtered.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"comparison_{previous_users[0]}_vs_{previous_users[1]}_filtered.csv",
        mime="text/csv",
        use_container_width=True,
        help="Descarga todas las películas que coinciden con la búsqueda y los filtros, no solo las filas visibles.",
    )

    with st.expander("¿Dónde se guardaron los archivos?"):
        st.write(f"Watchlists y comparación original: `{DATA_DIR}`")
        st.write(f"CSV original: `{st.session_state.get('comparison_file', '')}`")
else:
    st.info("Introduce dos usuarios y pulsa **Comparar watchlists** para comenzar.")
