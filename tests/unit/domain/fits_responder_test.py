import unittest

import numpy as np
from astropy.io import fits as astropy_fits

from app.data import model
from app.domain.responders import fits_responder


class ExtractObjectDataTest(unittest.TestCase):
    def setUp(self):
        self.objects = [
            model.Layer2Object(
                pgc=1234,
                data=[
                    model.DesignationCatalogObject(design="Galaxy1"),
                    model.ICRSCatalogObject(ra=12.5, e_ra=0.1, dec=34.5, e_dec=0.1),
                    model.RedshiftCatalogObject(cz=11.8, e_cz=0.2),
                ],
            ),
            model.Layer2Object(
                pgc=5678,
                data=[
                    model.DesignationCatalogObject(design="Galaxy2"),
                    model.ICRSCatalogObject(ra=13.2, e_ra=0.1, dec=35.6, e_dec=0.1),
                    model.RedshiftCatalogObject(cz=12.1, e_cz=0.2),
                ],
            ),
        ]

    def test_data_structure(self):
        data_dict = fits_responder.extract_object_data(self.objects)

        self.assertIn("PGC", data_dict)
        self.assertIn("designation_design", data_dict)
        self.assertIn("icrs_ra", data_dict)
        self.assertIn("icrs_e_ra", data_dict)
        self.assertIn("icrs_dec", data_dict)
        self.assertIn("icrs_e_dec", data_dict)
        self.assertIn("redshift_cz", data_dict)
        self.assertIn("redshift_e_cz", data_dict)

    def test_data_types(self):
        data_dict = fits_responder.extract_object_data(self.objects)

        self.assertIsInstance(data_dict["PGC"], np.ndarray)
        self.assertIsInstance(data_dict["designation_design"], np.ndarray)
        self.assertIsInstance(data_dict["icrs_ra"], np.ndarray)
        self.assertIsInstance(data_dict["icrs_e_ra"], np.ndarray)
        self.assertIsInstance(data_dict["icrs_dec"], np.ndarray)
        self.assertIsInstance(data_dict["icrs_e_dec"], np.ndarray)
        self.assertIsInstance(data_dict["redshift_cz"], np.ndarray)
        self.assertIsInstance(data_dict["redshift_e_cz"], np.ndarray)

    def test_data_values(self):
        data_dict = fits_responder.extract_object_data(self.objects)

        self.assertListEqual(list(data_dict["PGC"]), [1234, 5678])
        self.assertListEqual(list(data_dict["designation_design"]), [b"Galaxy1", b"Galaxy2"])
        self.assertTrue(np.allclose(data_dict["icrs_ra"], [12.5, 13.2]))
        self.assertTrue(np.allclose(data_dict["icrs_e_ra"], [0.1, 0.1]))
        self.assertTrue(np.allclose(data_dict["icrs_dec"], [34.5, 35.6]))
        self.assertTrue(np.allclose(data_dict["icrs_e_dec"], [0.1, 0.1]))
        self.assertTrue(np.allclose(data_dict["redshift_cz"], [11.8, 12.1]))
        self.assertTrue(np.allclose(data_dict["redshift_e_cz"], [0.2, 0.2]))


class CreateFitsHdulTest(unittest.TestCase):
    def setUp(self):
        self.objects = [
            model.Layer2Object(
                pgc=1234,
                data=[
                    model.DesignationCatalogObject(design="Galaxy1"),
                    model.ICRSCatalogObject(ra=12.5, e_ra=0.1, dec=34.5, e_dec=0.1),
                ],
            )
        ]

    def test_hdul_structure(self):
        hdul = fits_responder.create_fits_hdul(self.objects)

        self.assertIsInstance(hdul, astropy_fits.HDUList)
        self.assertEqual(len(hdul), 2)
        self.assertIsInstance(hdul[0], astropy_fits.PrimaryHDU)
        self.assertIsInstance(hdul[1], astropy_fits.BinTableHDU)

    def test_table_columns(self):
        hdul = fits_responder.create_fits_hdul(self.objects)
        table = hdul[1]

        self.assertIn("PGC", table.columns.names)
        self.assertIn("designation_design", table.columns.names)
        self.assertIn("icrs_ra", table.columns.names)
        self.assertIn("icrs_e_ra", table.columns.names)
        self.assertIn("icrs_dec", table.columns.names)
        self.assertIn("icrs_e_dec", table.columns.names)


class FitsResponderTest(unittest.TestCase):
    def setUp(self):
        self.objects = [
            model.Layer2Object(
                pgc=1234,
                data=[
                    model.DesignationCatalogObject(design="Galaxy1"),
                    model.ICRSCatalogObject(ra=12.5, e_ra=0.1, dec=34.5, e_dec=0.1),
                ],
            )
        ]
        self.responder = fits_responder.FITSResponder()

    def test_build_response(self):
        fits_data = self.responder.build_response(self.objects)

        self.assertIsInstance(fits_data, bytes)
        self.assertGreater(len(fits_data), 0)
