from dataclasses import dataclass

from pandas import DataFrame

from app.domain.model.layer0.layer_0_meta import Layer0Meta


@dataclass
class Layer0Model:
    """
    Data model for layer 0 data. Represents single income to DB. E.g. a table from some article, a dataset from other DB
    Args:
        id: Unique layer 0 data node id
        processed: True, if node processed, and data transformed further. False if not transformed, or changed after
            last transformation
        meta: Metadata, used to transform data further
        data: Data in form of table, to be processed
    """

    id: int
    processed: bool
    meta: Layer0Meta
    data: DataFrame
