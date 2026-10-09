import csv
from pathlib import Path
from urllib.parse import urlsplit


def _normalize_url(url: str) -> str:
    """Normaliza una URL de Letterboxd para comparar películas."""
    parsed = urlsplit(url.strip())
    return parsed.path.rstrip("/").lower()


def _load_watchlist(path: Path) -> dict:
    """Carga un CSV y elimina películas duplicadas por URL."""
    if not path.exists():
        raise FileNotFoundError(
            f"No se encontró el archivo {path}. "
            "Ejecuta primero el extractor para ese usuario."
        )

    films = {}

    with path.open("r", newline="", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        required_columns = {"title", "year", "url"}
        if not reader.fieldnames or not required_columns.issubset(
            reader.fieldnames
        ):
            raise ValueError(
                f"El archivo {path} debe contener las columnas "
                "title, year y url."
            )

        for row in reader:
            url = row.get("url", "").strip()
            title = row.get("title", "").strip()

            if not url or not title:
                continue

            key = _normalize_url(url)

            if key:
                films[key] = {
                    "title": title,
                    "year": row.get("year", "").strip(),
                    "url": url,
                }

    return films


def compare_users(
    user_a: str,
    user_b: str,
    data_dir: str | Path = "data",
    output_dir: str | Path = "data",
) -> dict:
    """Compara dos watchlists y guarda las películas compartidas."""

    user_a = user_a.strip()
    user_b = user_b.strip()

    if not user_a or not user_b or "/" in user_a or "/" in user_b:
        raise ValueError("Introduce dos nombres de usuario válidos.")

    data_dir = Path(data_dir)
    output_dir = Path(output_dir)

    films_a = _load_watchlist(data_dir / f"{user_a}_watchlist.csv")
    films_b = _load_watchlist(data_dir / f"{user_b}_watchlist.csv")

    common_keys = films_a.keys() & films_b.keys()

    common_films = sorted(
        (films_a[key] for key in common_keys),
        key=lambda film: (film["title"].casefold(), film["year"]),
    )

    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"comparison_{user_a}_vs_{user_b}.csv"

    with output_file.open(
        "w",
        newline="",
        encoding="utf-8-sig",
    ) as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["title", "year", "url"],
        )
        writer.writeheader()
        writer.writerows(common_films)

    total_a = len(films_a)
    total_b = len(films_b)
    common_count = len(common_films)
    union_count = len(films_a.keys() | films_b.keys())

    summary = {
        "user_a": user_a,
        "user_b": user_b,
        "total_a": total_a,
        "total_b": total_b,
        "common_count": common_count,
        "overlap_a_pct": round(100 * common_count / total_a, 2)
        if total_a else 0.0,
        "overlap_b_pct": round(100 * common_count / total_b, 2)
        if total_b else 0.0,
        "jaccard_pct": round(100 * common_count / union_count, 2)
        if union_count else 0.0,
        "output_file": str(output_file.resolve()),
    }

    print(f"\nComparación: {user_a} vs. {user_b}")
    print(f"Películas de {user_a}: {total_a}")
    print(f"Películas de {user_b}: {total_b}")
    print(f"Películas compartidas: {common_count}")
    print(f"Coincidencia respecto a {user_a}: {summary['overlap_a_pct']}%")
    print(f"Coincidencia respecto a {user_b}: {summary['overlap_b_pct']}%")
    print(f"Índice Jaccard: {summary['jaccard_pct']}%")
    print(f"Archivo generado: {output_file.resolve()}")

    return summary
