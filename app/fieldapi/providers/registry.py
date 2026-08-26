import pathlib
from collections.abc import Callable

from app.fieldapi import config as fieldapi_config
from app.fieldapi.presentation import interface
from app.fieldapi.providers import interface as provider_interface
from app.fieldapi.providers import sfd as sfd_provider
from app.lib.web import errors

ProviderFactory = Callable[[fieldapi_config.DatasetConfig], provider_interface.DatasetProvider]

PROVIDER_FACTORIES: dict[str, ProviderFactory] = {
    "sfd": sfd_provider.SFDProvider,
}


class DatasetRegistry:
    def __init__(
        self,
        providers: dict[str, provider_interface.DatasetProvider],
        metadata: dict[str, interface.DatasetInfo],
    ) -> None:
        self._providers = providers
        self._metadata = metadata

    @classmethod
    def from_config(
        cls,
        data_dir: pathlib.Path,
        datasets: list[fieldapi_config.DatasetConfig],
    ) -> "DatasetRegistry":
        providers: dict[str, provider_interface.DatasetProvider] = {}
        metadata: dict[str, interface.DatasetInfo] = {}

        for dataset in datasets:
            factory = PROVIDER_FACTORIES.get(dataset.provider)
            if factory is None:
                raise ValueError(f"Unknown provider: {dataset.provider}")

            provider = factory(dataset)
            provider.prepare(data_dir)
            providers[dataset.id] = provider
            metadata[dataset.id] = dataset.to_dataset_info()

        return cls(providers=providers, metadata=metadata)

    def list_datasets(self) -> list[interface.DatasetInfo]:
        return [self._metadata[dataset_id] for dataset_id in sorted(self._metadata)]

    def sample(self, dataset_id: str, coordinates: list[interface.SkyCoordinate]) -> list[float]:
        provider = self._providers.get(dataset_id)
        if provider is None:
            raise errors.NotFoundError("dataset", dataset_id)
        return provider.sample(coordinates)
