from app import catalogs


def catalog_objects_equal(actual: catalogs.CatalogObject, expected: catalogs.CatalogObject) -> bool:
    if type(actual) is not type(expected):
        return False
    try:
        return actual.layer2_data() == expected.layer2_data()
    except NotImplementedError:
        return actual.__dict__ == expected.__dict__


def assert_catalog_object_equal(
    actual: catalogs.CatalogObject,
    expected: catalogs.CatalogObject,
) -> None:
    assert catalog_objects_equal(actual, expected), f"catalog objects differ: {actual!r} != {expected!r}"


def assert_layer2_catalog_objects_equal(
    actual: list[catalogs.Layer2CatalogObject],
    expected: list[catalogs.Layer2CatalogObject],
) -> None:
    assert len(actual) == len(expected)
    for act, exp in zip(actual, expected, strict=True):
        assert act.pgc == exp.pgc
        assert len(act.data) == len(exp.data)
        for act_cat, exp_cat in zip(act.data, exp.data, strict=True):
            assert_catalog_object_equal(act_cat, exp_cat)
