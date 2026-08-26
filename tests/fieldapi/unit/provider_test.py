import pathlib
import tempfile
import unittest
from unittest import mock

import numpy as np

from app.fieldapi import config as fieldapi_config
from app.fieldapi.presentation import interface
from app.fieldapi.providers import registry, sfd


class SFDProviderTest(unittest.TestCase):
    def test_sfd_files_present(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            map_dir = pathlib.Path(tmpdir)
            self.assertFalse(sfd.sfd_files_present(map_dir))
            (map_dir / sfd.SFD_FILES[0]).write_bytes(b"x")
            self.assertFalse(sfd.sfd_files_present(map_dir))
            (map_dir / sfd.SFD_FILES[1]).write_bytes(b"y")
            self.assertTrue(sfd.sfd_files_present(map_dir))

    @mock.patch("dustmaps.sfd.SFDQuery")
    @mock.patch("dustmaps.sfd.fetch")
    @mock.patch("dustmaps.config.config", new_callable=dict)
    def test_prepare_downloads_when_missing(
        self,
        dustmaps_config: dict[str, str],
        fetch: mock.Mock,
        sfd_query: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = pathlib.Path(tmpdir)
            provider = sfd.SFDProvider()
            provider.prepare(data_dir)
            fetch.assert_called_once()
            self.assertEqual(dustmaps_config["data_dir"], str(data_dir))
            sfd_query.assert_called_once_with(map_dir=str(data_dir / sfd.SFD_MAP_DIR))

    @mock.patch("dustmaps.sfd.SFDQuery")
    @mock.patch("dustmaps.sfd.fetch")
    @mock.patch("dustmaps.config.config", new_callable=dict)
    def test_prepare_skips_download_when_present(
        self,
        dustmaps_config: dict[str, str],
        fetch: mock.Mock,
        sfd_query: mock.Mock,
    ) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            data_dir = pathlib.Path(tmpdir)
            map_dir = data_dir / sfd.SFD_MAP_DIR
            map_dir.mkdir(parents=True)
            for name in sfd.SFD_FILES:
                (map_dir / name).write_bytes(b"x")

            provider = sfd.SFDProvider()
            provider.prepare(data_dir)
            fetch.assert_not_called()
            sfd_query.assert_called_once_with(map_dir=str(map_dir))

    def test_sample_returns_values_in_order(self) -> None:
        query = mock.Mock(return_value=np.array([0.03, 0.12], dtype=np.float64))
        provider = sfd.SFDProvider(query=query)
        coordinates = [
            interface.SkyCoordinate(ra_deg=187.6, dec_deg=15.26),
            interface.SkyCoordinate(ra_deg=210.25, dec_deg=-3.10),
        ]
        self.assertEqual(provider.sample(coordinates), [0.03, 0.12])


class DatasetRegistryTest(unittest.TestCase):
    @mock.patch("app.fieldapi.providers.registry.PROVIDER_FACTORIES", {"sfd": lambda: _MockProvider()})
    def test_from_config_loads_enabled_datasets(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            datasets = [
                fieldapi_config.DatasetConfig(id="sfd", provider="sfd", name="SFD", version="1998"),
            ]
            dataset_registry = registry.DatasetRegistry.from_config(pathlib.Path(tmpdir), datasets)
            self.assertEqual([dataset.id for dataset in dataset_registry.list_datasets()], ["sfd"])

    @mock.patch("app.fieldapi.providers.registry.PROVIDER_FACTORIES", {"sfd": lambda: _MockProvider()})
    def test_sample_unknown_dataset_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            datasets = [
                fieldapi_config.DatasetConfig(id="sfd", provider="sfd", name="SFD", version="1998"),
            ]
            dataset_registry = registry.DatasetRegistry.from_config(pathlib.Path(tmpdir), datasets)
            with self.assertRaises(Exception) as ctx:
                dataset_registry.sample(
                    "missing",
                    [
                        interface.SkyCoordinate(
                            ra_deg=187.6,
                            dec_deg=15.26,
                        )
                    ],
                )
            self.assertIn("dataset", str(ctx.exception))


class _MockProvider(sfd.SFDProvider):
    def prepare(self, data_dir: pathlib.Path) -> None:
        _ = data_dir

    def sample(self, coordinates: list[interface.SkyCoordinate]) -> list[float]:
        _ = coordinates
        return [0.5]
