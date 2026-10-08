from app.catalogs import layer1, layer2


def layer1_catalog_objects_equal(
    actual: layer1.CatalogObject,
    expected: layer1.CatalogObject,
) -> bool:
    if type(actual) is not type(expected):
        return False
    return actual.__dict__ == expected.__dict__


def layer2_catalog_objects_equal(
    actual: layer2.CatalogObject,
    expected: layer2.CatalogObject,
) -> bool:
    if type(actual) is not type(expected):
        return False
    return actual.to_row() == expected.to_row()


def assert_catalog_object_equal(
    actual: layer2.CatalogObject,
    expected: layer2.CatalogObject,
) -> None:
    assert layer2_catalog_objects_equal(actual, expected), f"catalog objects differ: {actual!r} != {expected!r}"


def assert_layer2_catalog_objects_equal(
    actual: list[layer2.Layer2Object],
    expected: list[layer2.Layer2Object],
) -> None:
    assert len(actual) == len(expected)
    for act, exp in zip(actual, expected, strict=True):
        assert act.pgc == exp.pgc
        assert len(act.data) == len(exp.data)
        for act_cat, exp_cat in zip(act.data, exp.data, strict=True):
            assert_catalog_object_equal(act_cat, exp_cat)
