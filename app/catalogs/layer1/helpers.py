from app.catalogs.layer1 import (
    designation,
    distance,
    geometry,
    icrs,
    interface,
    kinematics,
    morphology,
    nature,
    note,
    photometry,
    redshift,
    spectroscopy,
)

_CATALOG_OBJECT_TYPES: dict[interface.Catalog, type[interface.CatalogObject]] = {
    interface.Catalog.DESIGNATION: designation.DesignationCatalogObject,
    interface.Catalog.ICRS: icrs.ICRSCatalogObject,
    interface.Catalog.REDSHIFT: redshift.RedshiftCatalogObject,
    interface.Catalog.NATURE: nature.NatureCatalogObject,
    interface.Catalog.PHOTOMETRY__TOTAL: photometry.PhotometryTotalCatalogObject,
    interface.Catalog.PHOTOMETRY__ISOPHOTAL: photometry.PhotometryIsophotalCatalogObject,
    interface.Catalog.GEOMETRY: geometry.GeometryCatalogObject,
    interface.Catalog.SPECTROSCOPY__INTEGRATED_FLUX_DENSITY: (
        spectroscopy.SpectroscopyIntegratedFluxDensityCatalogObject
    ),
    interface.Catalog.SPECTROSCOPY__ENERGY_FLUX: spectroscopy.SpectroscopyEnergyFluxCatalogObject,
    interface.Catalog.KINEMATICS__LINE_WIDTH: kinematics.KinematicsLineWidthCatalogObject,
    interface.Catalog.DISTANCE: distance.DistanceCatalogObject,
    interface.Catalog.MORPHOLOGY__T: morphology.MorphologyTCatalogObject,
    interface.Catalog.MORPHOLOGY__FEATURES: morphology.MorphologyFeaturesCatalogObject,
    interface.Catalog.MORPHOLOGY__EXTRA: morphology.MorphologyExtraCatalogObject,
    interface.Catalog.MORPHOLOGY__SPIRAL_WINDING: morphology.MorphologySpiralWindingCatalogObject,
    interface.Catalog.NOTE: note.NoteCatalogObject,
}


def get_catalog_object_type(catalog: interface.Catalog) -> type[interface.CatalogObject]:
    try:
        return _CATALOG_OBJECT_TYPES[catalog]
    except KeyError as e:
        raise ValueError(f"Unknown catalog: {catalog}") from e
