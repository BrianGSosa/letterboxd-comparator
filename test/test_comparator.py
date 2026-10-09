import csv

import pytest

from src.letterboxd_comparator import compare_users


def create_watchlist(path, films):
    """Crea un CSV de prueba con películas ficticias."""
    path.parent.mkdir(parents=True, exist_ok=True)

    with path.open("w", newline="", encoding="utf-8-sig") as file:
        writer = csv.DictWriter(
            file,
            fieldnames=["title", "year", "url"],
        )
        writer.writeheader()
        writer.writerows(films)


def film(title, year, slug):
    return {
        "title": title,
        "year": str(year),
        "url": f"https://letterboxd.com/film/{slug}/",
    }


def test_finds_common_films_and_calculates_metrics(tmp_path):
    data_dir = tmp_path / "data"
    output_dir = tmp_path / "output"

    create_watchlist(
        data_dir / "ana_watchlist.csv",
        [
            film("Alien", 1979, "alien"),
            film("Arrival", 2016, "arrival"),
            film("Blade Runner", 1982, "blade-runner"),
        ],
    )

    create_watchlist(
        data_dir / "bruno_watchlist.csv",
        [
            film("Arrival", 2016, "arrival"),
            film("Alien", 1979, "alien"),
            film("Dune", 2021, "dune"),
        ],
    )

    result = compare_users(
        "ana",
        "bruno",
        data_dir=data_dir,
        output_dir=output_dir,
    )

    assert result["total_a"] == 3
    assert result["total_b"] == 3
    assert result["common_count"] == 2
    assert result["overlap_a_pct"] == pytest.approx(66.67)
    assert result["overlap_b_pct"] == pytest.approx(66.67)
    assert result["jaccard_pct"] == 50.0

    with open(result["output_file"], newline="", encoding="utf-8-sig") as file:
        rows = list(csv.DictReader(file))

    assert [row["title"] for row in rows] == ["Alien", "Arrival"]


def test_normalizes_duplicate_urls(tmp_path):
    data_dir = tmp_path / "data"

    create_watchlist(
        data_dir / "ana_watchlist.csv",
        [
            film("Alien", 1979, "alien"),
            {
                "title": "Alien",
                "year": "1979",
                "url": "https://letterboxd.com/film/alien",
            },
        ],
    )

    create_watchlist(
        data_dir / "bruno_watchlist.csv",
        [film("Alien", 1979, "alien")],
    )

    result = compare_users(
        "ana",
        "bruno",
        data_dir=data_dir,
        output_dir=tmp_path / "output",
    )

    assert result["total_a"] == 1
    assert result["total_b"] == 1
    assert result["common_count"] == 1
    assert result["jaccard_pct"] == 100.0


def test_empty_watchlists_return_zero_percentages(tmp_path):
    data_dir = tmp_path / "data"

    create_watchlist(data_dir / "ana_watchlist.csv", [])
    create_watchlist(data_dir / "bruno_watchlist.csv", [])

    result = compare_users(
        "ana",
        "bruno",
        data_dir=data_dir,
        output_dir=tmp_path / "output",
    )

    assert result["common_count"] == 0
    assert result["overlap_a_pct"] == 0.0
    assert result["overlap_b_pct"] == 0.0
    assert result["jaccard_pct"] == 0.0


def test_missing_watchlist_raises_error(tmp_path):
    data_dir = tmp_path / "data"
    data_dir.mkdir()

    create_watchlist(
        data_dir / "ana_watchlist.csv",
        [film("Alien", 1979, "alien")],
    )

    with pytest.raises(FileNotFoundError):
        compare_users(
            "ana",
            "bruno",
            data_dir=data_dir,
            output_dir=tmp_path / "output",
        )
