import sys
from pathlib import Path

from astropy import table
from astropy.io import fits

sys.path.insert(0, str(Path(__file__).parent / ".."))

import pandas
import structlog

from app.data import model
from app.data.repositories.layer2 import filters, params

logger = structlog.get_logger()


def example_query(repo):
    catalogs = [model.RawCatalog.ICRS, model.RawCatalog.DESIGNATION]

    search_types = {
        "icrs": filters.ICRSCoordinatesInRadiusFilter(1.0),
        "designation": filters.DesignationEqualsFilter("NGC 1234"),
    }

    search_params = {
        "obj1": params.ICRSSearchParams(ra=180.0, dec=0.0),
        "obj2": params.DesignationSearchParams("NGC 5678"),
    }

    results = repo.query_batch(
        catalogs=catalogs, search_types=search_types, search_params=search_params, limit=10, offset=0
    )

    print(f"Found {len(results)} objects")
    for object_id, layer2_objects in results.items():
        print(f"Object {object_id}: {len(layer2_objects)} matches")
        for obj in layer2_objects:
            print(f"  PGC {obj.pgc}: {len(obj.data)} catalog entries")


def get_objects(fits_file_path: str) -> pandas.DataFrame:
    with fits.open(fits_file_path) as hdul:
        table_data = hdul[1].data

        tbl = table.Table(table_data)
        df = tbl.to_pandas()

        print(f"Successfully loaded {len(df)} rows with {len(df.columns)} columns")
        print(f"Column names: {list(df.columns)}")

        return df


fast_objects = get_objects("experiments/data/fast.fits")

print(fast_objects.head())

# storage_config = postgres.PgStorageConfig(
#     endpoint="dm2.sao.ru", port=5432, dbname="hyperleda", user="hyperleda", password="password"
# )

# storage = postgres.PgStorage(storage_config, logger)
# storage.connect()

# layer2_repo = repositories.Layer2Repository(storage, logger)

# try:
#     example_query(layer2_repo)
# finally:
#     storage.disconnect()
