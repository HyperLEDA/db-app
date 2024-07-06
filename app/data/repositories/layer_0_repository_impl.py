from app.data.mappers import domain_to_data
from app.data.mappers.data_to_domain import layer_0_mapper
from app.data.repositories import CommonRepository
from app.data.repositories import Layer0Repository as DataRepository
from app.domain.model import Layer0Model
from app.domain.model.params.layer_0_query_param import Layer0QueryParam
from app.domain.repositories.layer_0_repository import Layer0Repository


class Layer0RepositoryImpl(Layer0Repository):
    def __init__(self, data_repository: DataRepository, common_repository: CommonRepository):
        self._data_repository: DataRepository = data_repository
        self._common_repository: CommonRepository = common_repository

    async def create_update_instances(self, instances: list[Layer0Model]):
        pass

    async def create_instances(self, instances: list[Layer0Model]):
        with self._data_repository.with_tx() as tx:
            for instance in instances:
                bibliography = domain_to_data.layer_0_bibliography_mapper(instance)
                bibliography_id = self._common_repository.create_bibliography(
                    bibliography.bibcode, bibliography.year, bibliography.author, bibliography.title, tx
                )
                creation = domain_to_data.layer_0_creation_mapper(instance, bibliography_id)
                table_id = self._data_repository.create_table(creation, tx)
                raw = domain_to_data.layer_0_raw_mapper(instance, table_id)
                self._data_repository.insert_raw_data(raw, tx)

    async def fetch_data(self, param: Layer0QueryParam) -> list[Layer0Model]:
        with self._data_repository.with_tx() as tx:
            # TODO use some selection params to filter unneeded tables
            ids = self._data_repository.get_all_table_ids()

            to_domain = []
            for table_id in ids:
                meta = self._data_repository.fetch_metadata(table_id, tx)
                raw = self._data_repository.fetch_raw_data(table_id, tx=tx)
                bib = self._common_repository.get_source_by_id(meta.bibliography_id)
                to_domain.append(layer_0_mapper(meta, raw, bib))

        return to_domain
