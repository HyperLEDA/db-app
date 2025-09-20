from app.data.model import designation, icrs, interface, redshift


def get_catalog_object_type(catalog: interface.RawCatalog) -> type[interface.CatalogObject]:
    if catalog == interface.RawCatalog.DESIGNATION:
        return designation.DesignationCatalogObject
    if catalog == interface.RawCatalog.ICRS:
        return icrs.ICRSCatalogObject
    if catalog == interface.RawCatalog.REDSHIFT:
        return redshift.RedshiftCatalogObject

    raise ValueError(f"Unknown catalog: {catalog}")


def new_catalog_object(catalog: interface.RawCatalog, **kwargs) -> interface.CatalogObject:
    return get_catalog_object_type(catalog)(**kwargs)
