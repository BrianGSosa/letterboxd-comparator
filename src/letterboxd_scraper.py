import argparse
import csv
import re
import time
from pathlib import Path

import requests
from bs4 import BeautifulSoup


BASE_URL = "https://letterboxd.com/"


def get_watchlist(
    username: str,
    output_dir: str | Path = "data",
    delay_seconds: float = 1.0,
) -> Path:
    """Descarga la watchlist pública de un usuario y la guarda en CSV."""

    username = username.strip().strip("/")

    if not username or "/" in username:
        raise ValueError("Introduce un nombre de usuario válido de Letterboxd.")

    if delay_seconds < 0:
        raise ValueError("delay_seconds no puede ser negativo.")

    base_url = f"{BASE_URL}{username}/watchlist/"
    films_by_url = {}
    page_number = 1

    with requests.Session() as session:
        session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 Chrome/130.0 Safari/537.36"
            )
        })

        while True:
            if page_number == 1:
                url = base_url
            else:
                url = f"{base_url}page/{page_number}/"

            print(f"Consultando página {page_number}: {url}")

            try:
                response = session.get(url, timeout=20)
            except requests.RequestException as exc:
                raise RuntimeError(
                    f"Error al consultar la página {page_number}: {exc}"
                ) from exc

            if response.status_code == 404 and page_number > 1:
                break

            try:
                response.raise_for_status()
            except requests.HTTPError as exc:
                raise RuntimeError(
                    f"Letterboxd devolvió HTTP {response.status_code} "
                    f"al consultar {url}"
                ) from exc

            soup = BeautifulSoup(response.text, "lxml")
            page_films = []

            for item in soup.find_all(attrs={"data-item-link": True}):
                link = item.get("data-item-link", "")

                if not link.startswith("/film/"):
                    continue

                title = item.get("data-item-name", "").strip()
                if not title:
                    continue

                match = re.search(r"\((\d{4})\)\s*$", title)
                year = match.group(1) if match else ""

                page_films.append({
                    "title": title,
                    "year": year,
                    "url": BASE_URL.rstrip("/") + link,
                })

            # Verificar que recibimos una página de watchlist reconocible.
            is_watchlist_page = (
                soup.find("body", class_="watchlist") is not None
                or soup.find(class_="js-watchlist-content") is not None
                or soup.find(class_="js-watchlist-count") is not None
            )

            if page_number == 1 and not is_watchlist_page:
                raise RuntimeError(
                    "No se reconoció la estructura de la watchlist. "
                    "Comprueba el usuario y si Letterboxd ha cambiado su HTML."
                )

            new_films = 0

            for film in page_films:
                if film["url"] not in films_by_url:
                    films_by_url[film["url"]] = film
                    new_films += 1

            print(f"Películas encontradas en esta página: {len(page_films)}")

            if not page_films or new_films == 0:
                break

            page_number += 1

            if delay_seconds:
                time.sleep(delay_seconds)

    films = list(films_by_url.values())

    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    output_file = output_dir / f"{username}_watchlist.csv"

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
        writer.writerows(films)

    print(f"\nTotal de películas guardadas: {len(films)}")
    print(f"Archivo generado: {output_file.resolve()}")

    return output_file


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Descarga la watchlist pública de un usuario de Letterboxd."
    )
    parser.add_argument("username", help="Nombre de usuario de Letterboxd")
    parser.add_argument(
        "--output-dir",
        default="data",
        help="Carpeta donde guardar el CSV (por defecto: data)",
    )
    args = parser.parse_args()

    get_watchlist(args.username, output_dir=args.output_dir)
