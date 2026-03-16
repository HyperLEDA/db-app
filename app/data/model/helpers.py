from app.data.model import designation, icrs, interface, nature, photometry, redshift


def get_catalog_object_type(catalog: interface.RawCatalog) -> type[interface.CatalogObject]:
    if catalog == interface.RawCatalog.DESIGNATION:
        return designation.DesignationCatalogObject
    if catalog == interface.RawCatalog.ICRS:
        return icrs.ICRSCatalogObject
    if catalog == interface.RawCatalog.REDSHIFT:
        return redshift.RedshiftCatalogObject
    if catalog == interface.RawCatalog.NATURE:
        return nature.NatureCatalogObject
    if catalog == interface.RawCatalog.PHOTOMETRY:
        return photometry.PhotometryCatalogObject

    raise ValueError(f"Unknown catalog: {catalog}")
