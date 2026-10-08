from app.catalogs.layer2 import (
    additional_designations,
    designation,
    icrs,
    interface,
    nature,
    note,
    photometry_total,
    redshift,
)

_CATALOG_OBJECT_TYPES: dict[interface.Catalog, type[interface.CatalogObject]] = {
    interface.Catalog.DESIGNATION: designation.DesignationCatalogObject,
    interface.Catalog.ADDITIONAL_DESIGNATIONS: additional_designations.AdditionalDesignationsCatalogObject,
    interface.Catalog.ICRS: icrs.ICRSCatalogObject,
    interface.Catalog.REDSHIFT: redshift.RedshiftCatalogObject,
    interface.Catalog.NATURE: nature.NatureCatalogObject,
    interface.Catalog.NOTE: note.NoteCatalogObject,
    interface.Catalog.PHOTOMETRY__TOTAL: photometry_total.PhotometryTotalCatalogObject,
}


def get_catalog_object_type(catalog: interface.Catalog) -> type[interface.CatalogObject]:
    try:
        return _CATALOG_OBJECT_TYPES[catalog]
    except KeyError as e:
        raise ValueError(f"Unknown catalog: {catalog}") from e
