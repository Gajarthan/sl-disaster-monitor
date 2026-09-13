"""Verify the district dictionary and distributable geographic boundaries."""

import json
from collections import Counter
from pathlib import Path


DATA = Path(__file__).resolve().parents[1] / "data"
EXPECTED = {
    "Western": {"Colombo", "Gampaha", "Kalutara"},
    "Central": {"Kandy", "Matale", "Nuwara Eliya"},
    "Southern": {"Galle", "Matara", "Hambantota"},
    "Northern": {"Jaffna", "Kilinochchi", "Mannar", "Mullaitivu", "Vavuniya"},
    "Eastern": {"Ampara", "Batticaloa", "Trincomalee"},
    "North Western": {"Kurunegala", "Puttalam"},
    "North Central": {"Anuradhapura", "Polonnaruwa"},
    "Uva": {"Badulla", "Moneragala"},
    "Sabaragamuwa": {"Ratnapura", "Kegalle"},
}


def read_data(filename):
    path = DATA / filename
    assert path.is_file(), f"Missing geographic asset: {filename}"
    return json.loads(path.read_text(encoding="utf-8"))


def test_all_districts_and_provinces_have_correct_mapping():
    districts = read_data("districts.json")["districts"]
    assert len(districts) == 25
    assert len({district["name"] for district in districts}) == 25
    assert {district["province"] for district in districts} == set(EXPECTED)
    for province, names in EXPECTED.items():
        assert {d["name"] for d in districts if d["province"] == province} == names


def test_district_aliases_include_each_language_without_ambiguity():
    districts = read_data("districts.json")["districts"]
    owners = {}
    for district in districts:
        aliases = district["aliases"]
        assert set(aliases) == {"en", "si", "ta"}
        assert district["name"] in aliases["en"]
        for language, names in aliases.items():
            assert names and all(isinstance(name, str) and name.strip() for name in names)
            if language == "si":
                assert any("\u0d80" <= char <= "\u0dff" for name in names for char in name)
            if language == "ta":
                assert any("\u0b80" <= char <= "\u0bff" for name in names for char in name)
            for name in names:
                key = name.casefold().strip()
                assert owners.setdefault(key, district["name"]) == district["name"]


def test_boundaries_match_dictionary_and_have_realistic_polygon_geometry():
    districts = read_data("districts.json")["districts"]
    boundaries = read_data("districts.geojson")
    assert boundaries["type"] == "FeatureCollection"
    features = boundaries["features"]
    assert len(features) == 25
    assert Counter(f["properties"]["name"] for f in features) == Counter(d["name"] for d in districts)
    mapping = {d["name"]: d["province"] for d in districts}
    for feature in features:
        assert feature["type"] == "Feature"
        assert feature["properties"]["province"] == mapping[feature["properties"]["name"]]
        geometry = feature["geometry"]
        assert geometry["type"] in {"Polygon", "MultiPolygon"}
        polygons = [geometry["coordinates"]] if geometry["type"] == "Polygon" else geometry["coordinates"]
        assert polygons
        vertex_count = 0
        for polygon in polygons:
            assert polygon
            for ring in polygon:
                assert len(ring) >= 4
                assert ring[0] == ring[-1]
                assert len({tuple(point) for point in ring}) >= 3
                vertex_count += len(ring)
                for point in ring:
                    assert len(point) == 2
                    longitude, latitude = point
                    assert 79 < longitude < 83
                    assert 5 < latitude < 11
        assert vertex_count > 20, "District boundaries must not be placeholder boxes"


def test_geography_attribution_and_download_size():
    attribution = (DATA / "GEOGRAPHY.md").read_text(encoding="utf-8")
    assert "ODbL" in attribution
    assert "OpenStreetMap" in attribution
    assert "9469f09" in attribution
    assert (DATA / "districts.geojson").stat().st_size < 2_000_000


def test_all_provinces_have_multilingual_aliases():
    provinces = read_data("districts.json")["provinces"]
    assert len(provinces) == 9
    assert {p["name"] for p in provinces} == set(EXPECTED)
    for province in provinces:
        assert set(province["aliases"]) == {"en", "si", "ta"}
        assert all(province["aliases"].values())
        assert province["name"] + " Province" in province["aliases"]["en"]