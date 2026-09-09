from pathlib import Path

from geocoder import LocalPlaceIndex


def test_finds_alias_and_does_not_duplicate_place() -> None:
    index = LocalPlaceIndex(Path(__file__).parents[1] / "places_ukraine.json")
    places = index.find_in_text("БПЛА летить на Фастова, курс західний")
    assert [place.name for place in places] == ["фастів"]


def test_finds_multiword_place() -> None:
    index = LocalPlaceIndex(Path(__file__).parents[1] / "places_ukraine.json")
    places = index.find_in_text("Загроза в районі Білої Церкви")
    assert places[0].name == "біла церква"