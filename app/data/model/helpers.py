from app.data.model import designation, icrs, interface, nature, redshift

ALLOWED_CATALOG_OBJECTS = [
    designation.DesignationCatalogObject,
    icrs.ICRSCatalogObject,
    redshift.RedshiftCatalogObject,
    nature.NatureCatalogObject,
]

catalog_to_objtype = {t.catalog(): t for t in ALLOWED_CATALOG_OBJECTS}


def get_catalog_object_type(catalog: interface.RawCatalog) -> type[interface.CatalogObject]:
    if catalog in catalog_to_objtype:
        return catalog_to_objtype[catalog]

    raise ValueError(f"Unknown catalog: {catalog}")


def new_catalog_object(catalog: interface.RawCatalog, **kwargs) -> interface.CatalogObject:
    return get_catalog_object_type(catalog)(**kwargs)
