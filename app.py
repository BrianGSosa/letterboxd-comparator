import argparse
from pathlib import Path

from src.letterboxd_scraper import get_watchlist
from src.letterboxd_comparator import compare_users


PROJECT_DIR = Path(__file__).resolve().parent
DATA_DIR = PROJECT_DIR / "data"


def main():
    parser = argparse.ArgumentParser(
        description=(
            "Descarga y compara las watchlists de dos usuarios de Letterboxd."
        )
    )

    parser.add_argument("user_a", help="Primer usuario de Letterboxd")
    parser.add_argument("user_b", help="Segundo usuario de Letterboxd")
    parser.add_argument(
        "--delay",
        type=float,
        default=1.0,
        help="Pausa entre peticiones de páginas, en segundos (por defecto: 1)",
    )

    args = parser.parse_args()

    if args.user_a.strip().casefold() == args.user_b.strip().casefold():
        parser.error("Debes introducir dos usuarios diferentes.")

    print("=" * 60)
    print("LETTERBOXD WATCHLIST COMPARATOR")
    print("=" * 60)

    print("\n[1/3] Extrayendo la watchlist del primer usuario...")
    get_watchlist(
        args.user_a,
        output_dir=DATA_DIR,
        delay_seconds=args.delay,
    )

    print("\n[2/3] Extrayendo la watchlist del segundo usuario...")
    get_watchlist(
        args.user_b,
        output_dir=DATA_DIR,
        delay_seconds=args.delay,
    )

    print("\n[3/3] Comparando las watchlists...")
    result = compare_users(
        args.user_a,
        args.user_b,
        data_dir=DATA_DIR,
        output_dir=DATA_DIR,
    )

    print("\nProceso finalizado.")
    print(f"Películas compartidas: {result['common_count']}")
    print(f"Resultado guardado en: {result['output_file']}")


if __name__ == "__main__":
    main()
