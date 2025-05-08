import json

from app.data.model import designation, icrs, interface, redshift


class CatalogObjectEncoder(json.JSONEncoder):
    def default(self, obj):
        if not isinstance(obj, interface.CatalogObject):
            return json.JSONEncoder.default(self, obj)

        data = obj.layer0_data()
        data["catalog"] = obj.catalog().value

        return data


class Layer0CatalogObjectDecoder(json.JSONDecoder):
    def __init__(self, *args, **kwargs):
        super().__init__(object_hook=self.object_hook, **kwargs)

    def object_hook(self, obj):
        if "catalog" not in obj:
            return obj

        catalog = interface.RawCatalog(obj.pop("catalog"))

        return new_catalog_object(catalog, **obj)


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
