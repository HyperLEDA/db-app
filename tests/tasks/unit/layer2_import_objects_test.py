from unittest import mock

import pytest
from astropy import table
from astropy import units as u

from app.lib import astronomy
from app.specs import fieldapi as fieldapi_spec
from app.tasks import layer2_import_objects

ERR_TYPES = {"!", "PoG"}


def _designations(*rows: tuple[int, str]) -> table.QTable:
    return table.QTable({"pgc": [pgc for pgc, _ in rows], "design": [name for _, name in rows]})


def _natures(*rows: tuple[int, str]) -> table.QTable:
    return table.QTable({"pgc": [pgc for pgc, _ in rows], "type_name": [name for _, name in rows]})


def _icrs(*rows: tuple[int, float, float, float, float]) -> table.QTable:
    deg = u.Unit("deg")
    return table.QTable(
        {
            "pgc": [row[0] for row in rows],
            "ra": [row[1] for row in rows] * deg,
            "e_ra": [row[2] for row in rows] * deg,
            "dec": [row[3] for row in rows] * deg,
            "e_dec": [row[4] for row in rows] * deg,
            "datatype": ["regular"] * len(rows),
        }
    )


def test_merges_designation_nature_and_icrs() -> None:
    rows, to_delete = layer2_import_objects.build_object_rows(
        [1],
        _designations((1, "NGC 1")),
        _natures((1, "G")),
        _icrs((1, 10.0, 0.1, 20.0, 0.2)),
        ERR_TYPES,
    )
    lon, lat, _, _ = astronomy.equatorial_to_lonlat(10.0, 20.0, 0.1, 0.2, "galactic")
    sgl, sgb, _, _ = astronomy.equatorial_to_lonlat(10.0, 20.0, 0.1, 0.2, "supergalactic")

    assert to_delete == []
    assert len(rows) == 1
    assert rows["name"][0] == "NGC 1"
    assert rows["objtype"][0] == "G"
    assert float(rows["ra"][0]) == pytest.approx(10.0)
    assert float(rows["dec"][0]) == pytest.approx(20.0)
    assert float(rows["e_ra"][0]) == pytest.approx(0.1)
    assert float(rows["e_dec"][0]) == pytest.approx(0.2)
    assert float(rows["l"][0]) == pytest.approx(lon)
    assert float(rows["b"][0]) == pytest.approx(lat)
    assert float(rows["sgl"][0]) == pytest.approx(sgl)
    assert float(rows["sgb"][0]) == pytest.approx(sgb)
    assert rows["ebv"][0] is None


def test_error_nature_is_removed() -> None:
    rows, to_delete = layer2_import_objects.build_object_rows(
        [1, 2],
        _designations((1, "NGC 1"), (2, "NGC 2")),
        _natures((1, "!"), (2, "PoG")),
        _icrs((1, 10.0, 0.1, 20.0, 0.2), (2, 11.0, 0.1, 21.0, 0.2)),
        ERR_TYPES,
    )
    assert len(rows) == 0
    assert to_delete == [1, 2]


def test_missing_nature_is_kept() -> None:
    rows, to_delete = layer2_import_objects.build_object_rows(
        [1],
        _designations((1, "NGC 1")),
        table.QTable({"pgc": [], "type_name": []}),
        _icrs((1, 10.0, 0.1, 20.0, 0.2)),
        ERR_TYPES,
    )
    assert to_delete == []
    assert rows["name"][0] == "NGC 1"
    assert rows["objtype"][0] is None


def test_missing_designation_is_removed() -> None:
    rows, to_delete = layer2_import_objects.build_object_rows(
        [1],
        table.QTable({"pgc": [], "design": []}),
        _natures((1, "G")),
        _icrs((1, 10.0, 0.1, 20.0, 0.2)),
        ERR_TYPES,
    )
    assert len(rows) == 0
    assert to_delete == [1]


def test_missing_coordinates_stay_null() -> None:
    rows, to_delete = layer2_import_objects.build_object_rows(
        [1],
        _designations((1, "NGC 1")),
        _natures((1, "G")),
        table.QTable({"pgc": [], "ra": [], "e_ra": [], "dec": [], "e_dec": [], "datatype": []}),
        ERR_TYPES,
    )
    assert to_delete == []
    assert rows["ra"][0] is None
    assert rows["l"][0] is None
    assert rows["ebv"][0] is None


def test_assign_ebv_samples_coordinates_and_clamps_negatives() -> None:
    rows, _ = layer2_import_objects.build_object_rows(
        [1, 2],
        _designations((1, "NGC 1"), (2, "NGC 2")),
        _natures((1, "G"), (2, "G")),
        _icrs((1, 10.0, 0.1, 20.0, 0.2)),
        ERR_TYPES,
    )
    client = mock.Mock()
    client.sample_sfd_ebv.return_value = [-0.02]
    layer2_import_objects.assign_ebv(rows, client)
    assert rows["ebv"][0] == 0.0
    assert rows["ebv"][1] is None
    client.sample_sfd_ebv.assert_called_once()
    sent = client.sample_sfd_ebv.call_args.args[0]
    assert len(sent) == 1
    assert sent[0] == fieldapi_spec.SkyCoordinate(ra_deg=10.0, dec_deg=20.0)


def test_sample_ebv_deduplicates_and_chunks() -> None:
    coordinates = [(i * 0.01, 0.0) for i in range(layer2_import_objects.EBV_CHUNK_SIZE + 1)]
    coordinates.append(coordinates[0])
    calls: list[int] = []

    def sample(chunk: list[fieldapi_spec.SkyCoordinate]) -> list[float]:
        calls.append(len(chunk))
        return [float(item.ra_deg) for item in chunk]

    client = mock.Mock()
    client.sample_sfd_ebv.side_effect = sample
    values = layer2_import_objects.sample_ebv(client, coordinates)

    assert calls == [layer2_import_objects.EBV_CHUNK_SIZE, 1]
    assert values[0] == pytest.approx(values[-1])
    assert values[1] == pytest.approx(0.01)
