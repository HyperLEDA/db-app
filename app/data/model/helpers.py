from app.data.model import (
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

_CATALOG_OBJECT_TYPES: dict[interface.RawCatalog, type[interface.CatalogObject]] = {
    interface.RawCatalog.DESIGNATION: designation.DesignationCatalogObject,
    interface.RawCatalog.ICRS: icrs.ICRSCatalogObject,
    interface.RawCatalog.REDSHIFT: redshift.RedshiftCatalogObject,
    interface.RawCatalog.NATURE: nature.NatureCatalogObject,
    interface.RawCatalog.PHOTOMETRY__TOTAL: photometry.PhotometryTotalCatalogObject,
    interface.RawCatalog.PHOTOMETRY__ISOPHOTAL: photometry.PhotometryIsophotalCatalogObject,
    interface.RawCatalog.GEOMETRY: geometry.GeometryCatalogObject,
    interface.RawCatalog.SPECTROSCOPY__INTEGRATED_FLUX_DENSITY: (
        spectroscopy.SpectroscopyIntegratedFluxDensityCatalogObject
    ),
    interface.RawCatalog.SPECTROSCOPY__ENERGY_FLUX: spectroscopy.SpectroscopyEnergyFluxCatalogObject,
    interface.RawCatalog.KINEMATICS__LINE_WIDTH: kinematics.KinematicsLineWidthCatalogObject,
    interface.RawCatalog.DISTANCE: distance.DistanceCatalogObject,
    interface.RawCatalog.MORPHOLOGY__T: morphology.MorphologyTCatalogObject,
    interface.RawCatalog.MORPHOLOGY__FEATURES: morphology.MorphologyFeaturesCatalogObject,
    interface.RawCatalog.MORPHOLOGY__EXTRA: morphology.MorphologyExtraCatalogObject,
    interface.RawCatalog.MORPHOLOGY__SPIRAL_WINDING: morphology.MorphologySpiralWindingCatalogObject,
    interface.RawCatalog.NOTE: note.NoteCatalogObject,
}


def get_catalog_object_type(catalog: interface.RawCatalog) -> type[interface.CatalogObject]:
    try:
        return _CATALOG_OBJECT_TYPES[catalog]
    except KeyError as e:
        raise ValueError(f"Unknown catalog: {catalog}") from e
