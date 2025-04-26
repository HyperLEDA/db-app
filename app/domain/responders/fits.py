import io

import numpy as np
from astropy.io import fits

from app.data import model
from app.domain.responders import interface


def _extract_object_data(objects: list[model.Layer2Object]) -> dict[str, np.ndarray]:
    data_dict = {}

    for obj in objects:
        if "PGC" not in data_dict:
            data_dict["PGC"] = []

        for catalog_obj in obj.data:
            catalog_name = catalog_obj.catalog().value
            catalog_data = catalog_obj.layer2_data()

            if isinstance(catalog_data, dict):
                for field, _ in catalog_data.items():
                    full_field_name = f"{catalog_name}_{field}"
                    if full_field_name not in data_dict:
                        data_dict[full_field_name] = []
            else:
                if catalog_name not in data_dict:
                    data_dict[catalog_name] = []

    for obj in objects:
        for field in data_dict:
            data_dict[field].append(None)

        data_dict["PGC"][-1] = obj.pgc

        for catalog_obj in obj.data:
            catalog_name = catalog_obj.catalog().value
            catalog_data = catalog_obj.layer2_data()

            if isinstance(catalog_data, dict):
                for field, value in catalog_data.items():
                    full_field_name = f"{catalog_name}_{field}"
                    data_dict[full_field_name][-1] = value
            else:
                data_dict[catalog_name][-1] = catalog_data

    for field, values in data_dict.items():
        if all(v is None for v in values):
            data_dict[field] = np.array([], dtype=np.float64)
        else:
            if all(isinstance(v, int | type(None)) for v in values):
                data_dict[field] = np.array(values, dtype=np.int32)
            elif all(isinstance(v, float | type(None)) for v in values):
                data_dict[field] = np.array(values, dtype=np.float64)
            elif all(isinstance(v, str | type(None)) for v in values):
                max_len = max(len(str(v)) for v in values if v is not None)
                data_dict[field] = np.array(values, dtype=f"S{max_len}")
            else:
                data_dict[field] = np.array(values, dtype=object)

    return data_dict


def _create_fits_hdul(objects: list[model.Layer2Object]) -> fits.HDUList:
    data_dict = _extract_object_data(objects)

    columns = []
    for field, array in data_dict.items():
        if len(array) == 0:
            continue

        if array.dtype.kind == "i":
            fits_format = "J"
        elif array.dtype.kind == "f":
            fits_format = "D"
        elif array.dtype.kind == "S":
            fits_format = f"A{array.dtype.itemsize}"
        else:
            fits_format = "A32"

        columns.append(fits.Column(name=field, format=fits_format, array=array))

    hdu = fits.BinTableHDU.from_columns(columns)

    primary_hdu = fits.PrimaryHDU()
    return fits.HDUList([primary_hdu, hdu])


class FITSResponder(interface.ObjectResponder):
    def build_response(self, objects: list[model.Layer2Object]) -> bytes:
        hdul = _create_fits_hdul(objects)

        with io.BytesIO() as f:
            hdul.writeto(f)
            return f.getvalue()
