import pathlib
import tempfile
import unittest
from unittest import mock

import numpy as np
import pydantic

from app.fieldapi import config as fieldapi_config
from app.fieldapi.providers import registry, sfd
from app.specs import fieldapi


def sfd_dataset_config(dataset_id: str = "sfd") -> fieldapi_config.DatasetConfig:
    return fieldapi_config.DatasetConfig(
        id=dataset_id,
        provider="sfd",
        name="SFD",
        version="1998",
        dimensions=2,
        quantity="ebv",
        unit="mag",
        description="Galactic dust reddening map",
        bibcode="1998ApJ...500..525S",
        storage=fieldapi_config.DatasetStorageConfig(
            dir="sfd",
            files=["SFD_dust_4096_ngp.fits", "SFD_dust_4096_sgp.fits"],
        ),
    )


class DatasetConfigTest(unittest.TestCase):
    def test_to_dataset_info(self) -> None:
        dataset = sfd_dataset_config()
        info = dataset.to_dataset_info()
        self.assertEqual(info.id, "sfd")
        self.assertEqual(info.bibcode, "1998ApJ...500..525S")

    def test_rejects_duplicate_dataset_ids(self) -> None:
        with self.assertRaises(pydantic.ValidationError):
            fieldapi_config.DatasetsConfig(
                data_dir=pathlib.Path("downloads/fieldapi"),
                enabled=[sfd_dataset_config("sfd"), sfd_dataset_config("sfd")],
            )


class SFDProviderTest(unittest.TestCase):
    def test_map_files_present(self) -> None:
        dataset = sfd_dataset_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            map_dir = pathlib.Path(tmpdir)
            self.assertFalse(sfd.map_files_present(map_dir, dataset.storage.files))
            (map_dir / dataset.storage.files[0]).write_bytes(b"x")
            self.assertFalse(sfd.map_files_present(map_dir, dataset.storage.files))
            (map_dir / dataset.storage.files[1]).write_bytes(b"y")
            self.assertTrue(sfd.map_files_present(map_dir, dataset.storage.files))

    @mock.patch("dustmaps.sfd.SFDQuery")
    @mock.patch("app.fieldapi.providers.sfd.download_sfd_files")
    def test_prepare_downloads_when_missing(
        self,
        download_sfd_files: mock.Mock,
        sfd_query: mock.Mock,
    ) -> None:
        dataset = sfd_dataset_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = pathlib.Path(tmpdir)
            map_dir = data_dir / dataset.storage.dir

            def create_files(map_dir_arg: pathlib.Path, files: list[str]) -> None:
                map_dir_arg.mkdir(parents=True, exist_ok=True)
                for name in files:
                    (map_dir_arg / name).write_bytes(b"x")

            download_sfd_files.side_effect = create_files

            provider = sfd.SFDProvider(dataset)
            provider.prepare(data_dir)
            download_sfd_files.assert_called_once_with(map_dir, dataset.storage.files)
            sfd_query.assert_called_once_with(map_dir=str(map_dir))

    @mock.patch("dustmaps.sfd.SFDQuery")
    @mock.patch("app.fieldapi.providers.sfd.download_sfd_files")
    def test_prepare_redownloads_on_load_failure(
        self,
        download_sfd_files: mock.Mock,
        sfd_query: mock.Mock,
    ) -> None:
        dataset = sfd_dataset_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = pathlib.Path(tmpdir)
            map_dir = data_dir / dataset.storage.dir
            map_dir.mkdir(parents=True)
            for name in dataset.storage.files:
                (map_dir / name).write_bytes(b"truncated")

            sfd_query.side_effect = [TypeError("buffer is too small"), mock.Mock()]

            provider = sfd.SFDProvider(dataset)
            provider.prepare(data_dir)

            download_sfd_files.assert_called_once_with(map_dir, dataset.storage.files)
            self.assertEqual(sfd_query.call_count, 2)

    @mock.patch("dustmaps.sfd.SFDQuery")
    @mock.patch("app.fieldapi.providers.sfd.download_sfd_files")
    def test_prepare_raises_when_files_missing_after_fetch(
        self,
        download_sfd_files: mock.Mock,
        sfd_query: mock.Mock,
    ) -> None:
        _ = download_sfd_files
        _ = sfd_query
        dataset = fieldapi_config.DatasetConfig(
            id="sfd",
            provider="sfd",
            name="SFD",
            version="1998",
            dimensions=2,
            quantity="ebv",
            unit="mag",
            description="Galactic dust reddening map",
            bibcode="1998ApJ...500..525S",
            storage=fieldapi_config.DatasetStorageConfig(
                dir="custom",
                files=["missing.fits"],
            ),
        )
        with tempfile.TemporaryDirectory() as tmpdir:
            provider = sfd.SFDProvider(dataset)
            with self.assertRaises(FileNotFoundError):
                provider.prepare(pathlib.Path(tmpdir))
            download_sfd_files.assert_called_once()

    @mock.patch("dustmaps.sfd.SFDQuery")
    @mock.patch("app.fieldapi.providers.sfd.download_sfd_files")
    def test_prepare_skips_download_when_present(
        self,
        download_sfd_files: mock.Mock,
        sfd_query: mock.Mock,
    ) -> None:
        dataset = sfd_dataset_config()
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = pathlib.Path(tmpdir)
            map_dir = data_dir / dataset.storage.dir
            map_dir.mkdir(parents=True)
            for name in dataset.storage.files:
                (map_dir / name).write_bytes(b"x")

            provider = sfd.SFDProvider(dataset)
            provider.prepare(data_dir)
            download_sfd_files.assert_not_called()
            sfd_query.assert_called_once_with(map_dir=str(map_dir))

    def test_sample_returns_values_in_order(self) -> None:
        query = mock.Mock(return_value=np.array([0.03, 0.12], dtype=np.float64))
        provider = sfd.SFDProvider(sfd_dataset_config(), query=query)
        coordinates = [
            fieldapi.SkyCoordinate(ra_deg=187.6, dec_deg=15.26),
            fieldapi.SkyCoordinate(ra_deg=210.25, dec_deg=-3.10),
        ]
        self.assertEqual(provider.sample(coordinates), [0.03, 0.12])


def _mock_provider_factory(config: fieldapi_config.DatasetConfig) -> sfd.SFDProvider:
    return _MockProvider(config)


class _MockProvider(sfd.SFDProvider):
    def prepare(self, data_dir: pathlib.Path) -> None:
        _ = data_dir

    def sample(self, coordinates: list[fieldapi.SkyCoordinate]) -> list[float]:
        _ = coordinates
        return [0.5]


class DatasetRegistryTest(unittest.TestCase):
    @mock.patch("app.fieldapi.providers.registry.PROVIDER_FACTORIES", {"sfd": _mock_provider_factory})
    def test_from_config_loads_enabled_datasets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            datasets = [sfd_dataset_config()]
            dataset_registry = registry.DatasetRegistry.from_config(pathlib.Path(tmpdir), datasets)
            self.assertEqual([dataset.id for dataset in dataset_registry.list_datasets()], ["sfd"])
            self.assertEqual(dataset_registry.list_datasets()[0].bibcode, "1998ApJ...500..525S")

    @mock.patch("app.fieldapi.providers.registry.PROVIDER_FACTORIES", {"sfd": _mock_provider_factory})
    def test_from_config_with_empty_enabled_list(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            dataset_registry = registry.DatasetRegistry.from_config(pathlib.Path(tmpdir), [])
            self.assertEqual(dataset_registry.list_datasets(), [])

    @mock.patch("app.fieldapi.providers.registry.PROVIDER_FACTORIES", {"sfd": _mock_provider_factory})
    def test_sample_unknown_dataset_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            datasets = [sfd_dataset_config()]
            dataset_registry = registry.DatasetRegistry.from_config(pathlib.Path(tmpdir), datasets)
            with self.assertRaises(Exception) as ctx:
                dataset_registry.sample(
                    "missing",
                    [
                        fieldapi.SkyCoordinate(
                            ra_deg=187.6,
                            dec_deg=15.26,
                        )
                    ],
                )
            self.assertIn("dataset", str(ctx.exception))
