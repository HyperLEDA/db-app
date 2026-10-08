from app import catalogs
from app.adminapi import model
from app.adminapi.domain import crossmatch


def test_includes_nature_when_present() -> None:
    record = model.Record(
        id="rec1",
        data=[
            catalogs.layer1.DesignationCatalogObject(design="NGC 1"),
            catalogs.layer1.NatureCatalogObject(type_name="G"),
        ],
    )

    result = crossmatch.catalogs_from_layer1(record)

    assert result.designation is not None
    assert result.designation.name == "NGC 1"
    assert result.nature is not None
    assert result.nature.type_name == "G"


def test_omits_nature_when_absent() -> None:
    record = model.Record(
        id="rec1",
        data=[catalogs.layer1.DesignationCatalogObject(design="NGC 1")],
    )

    result = crossmatch.catalogs_from_layer1(record)

    assert result.nature is None
