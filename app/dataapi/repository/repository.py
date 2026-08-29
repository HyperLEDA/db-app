from collections.abc import Mapping
from typing import Any

from app.data import model
from app.dataapi.repository import model as repo_model
from app.lib import concurrency
from app.lib.storage import postgres


class Repository:
    def __init__(self, storage: postgres.PgStorage) -> None:
        self._storage = storage

    def _query_designations(self, pgcs: list[int]) -> dict[int, repo_model.DesignationCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, design FROM layer2.designation WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        return {int(row["pgc"]): repo_model.DesignationCatalog(name=str(row["design"])) for row in rows}

    def _query_icrs(self, pgcs: list[int]) -> dict[int, repo_model.ICRSCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, ra, e_ra, dec, e_dec FROM layer2.icrs WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        result: dict[int, repo_model.ICRSCatalog] = {}
        for row in rows:
            if all(row.get(k) is not None for k in ("ra", "e_ra", "dec", "e_dec")):
                result[int(row["pgc"])] = repo_model.ICRSCatalog(
                    ra=float(row["ra"]),
                    e_ra=float(row["e_ra"]),
                    dec=float(row["dec"]),
                    e_dec=float(row["e_dec"]),
                )
        return result

    def _query_redshift(self, pgcs: list[int]) -> dict[int, repo_model.RedshiftCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, cz, e_cz FROM layer2.cz WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        return {
            int(row["pgc"]): repo_model.RedshiftCatalog(cz=float(row["cz"]), e_cz=float(row["e_cz"]))
            for row in rows
            if row.get("cz") is not None and row.get("e_cz") is not None
        }

    def _query_nature(self, pgcs: list[int]) -> dict[int, repo_model.NatureCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, type_name FROM layer2.nature WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        return {
            int(row["pgc"]): repo_model.NatureCatalog(type_name=str(row["type_name"]))
            for row in rows
            if row.get("type_name") is not None
        }

    def _query_additional_designations(self, pgcs: list[int]) -> dict[int, repo_model.AdditionalDesignationsCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, design, code, year, author, title FROM layer2.designations "
            "WHERE pgc = ANY(%s) ORDER BY pgc, design",
            params=[pgcs],
        )
        result: dict[int, list[repo_model.AdditionalDesignation]] = {}
        for row in rows:
            pgc = int(row["pgc"])
            ad = repo_model.AdditionalDesignation(
                name=str(row["design"]) if row.get("design") is not None else "",
                source=_source_from_row(row),
            )
            result.setdefault(pgc, []).append(ad)
        return {pgc: repo_model.AdditionalDesignationsCatalog(names=names) for pgc, names in result.items()}

    def _query_notes(self, pgcs: list[int]) -> dict[int, repo_model.NotesCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            "SELECT pgc, note, code, year, author, title FROM layer2.notes WHERE pgc = ANY(%s) ORDER BY pgc",
            params=[pgcs],
        )
        result: dict[int, list[repo_model.NoteEntry]] = {}
        for row in rows:
            pgc = int(row["pgc"])
            note = repo_model.NoteEntry(
                note=str(row["note"]) if row.get("note") is not None else "",
                source=_source_from_row(row),
            )
            result.setdefault(pgc, []).append(note)
        return {pgc: repo_model.NotesCatalog(notes=notes) for pgc, notes in result.items()}

    def _query_photometry_total(self, pgcs: list[int]) -> dict[int, repo_model.PhotometryTotalCatalog]:
        if not pgcs:
            return {}
        rows = self._storage.query(
            """
            SELECT p.pgc, p.band, p.magsys, p.method, p.wavelength, p.mag, p.e_mag,
                   b.photsys, b.name AS filter
            FROM layer2.photometry_total AS p
              JOIN photometry.calib_bands AS cb ON p.band = cb.id
              JOIN photometry.bands AS b ON cb.band = b.id
            WHERE p.pgc = ANY(%s)
            ORDER BY p.pgc, p.wavelength
            """,
            params=[pgcs],
        )
        result: dict[int, list[repo_model.PhotometryTotalMeasurement]] = {}
        for row in rows:
            pgc = int(row["pgc"])
            measurement = repo_model.PhotometryTotalMeasurement(
                band=str(row["band"]),
                magsys=str(row["magsys"]) if row.get("magsys") is not None else None,
                method=str(row["method"]),
                wavelength=float(row["wavelength"]),
                mag=float(row["mag"]),
                e_mag=float(row["e_mag"]) if row.get("e_mag") is not None else None,
                photsys=str(row["photsys"]),
                filter=str(row["filter"]),
            )
            result.setdefault(pgc, []).append(measurement)
        return {
            pgc: repo_model.PhotometryTotalCatalog(measurements=measurements) for pgc, measurements in result.items()
        }

    def query_pgc(
        self,
        catalogs: list[model.RawCatalog],
        pgc_numbers: list[int],
        limit: int,
        offset: int = 0,
    ) -> list[repo_model.Layer2Object]:
        if not catalogs or not pgc_numbers:
            return []

        pgcs_page = sorted(pgc_numbers)[offset : offset + limit]
        if not pgcs_page:
            return []

        errgr = concurrency.ErrorGroup()
        designation_task: concurrency.TaskResult[dict[int, repo_model.DesignationCatalog]] | None = None
        additional_designations_task: (
            concurrency.TaskResult[dict[int, repo_model.AdditionalDesignationsCatalog]] | None
        ) = None
        icrs_task: concurrency.TaskResult[dict[int, repo_model.ICRSCatalog]] | None = None
        redshift_task: concurrency.TaskResult[dict[int, repo_model.RedshiftCatalog]] | None = None
        nature_task: concurrency.TaskResult[dict[int, repo_model.NatureCatalog]] | None = None
        notes_task: concurrency.TaskResult[dict[int, repo_model.NotesCatalog]] | None = None
        photometry_total_task: concurrency.TaskResult[dict[int, repo_model.PhotometryTotalCatalog]] | None = None

        if model.RawCatalog.DESIGNATION in catalogs:
            designation_task = errgr.run(self._query_designations, pgcs_page)
        if model.RawCatalog.ADDITIONAL_DESIGNATIONS in catalogs:
            additional_designations_task = errgr.run(self._query_additional_designations, pgcs_page)
        if model.RawCatalog.ICRS in catalogs:
            icrs_task = errgr.run(self._query_icrs, pgcs_page)
        if model.RawCatalog.REDSHIFT in catalogs:
            redshift_task = errgr.run(self._query_redshift, pgcs_page)
        if model.RawCatalog.NATURE in catalogs:
            nature_task = errgr.run(self._query_nature, pgcs_page)
        if model.RawCatalog.NOTE in catalogs:
            notes_task = errgr.run(self._query_notes, pgcs_page)
        if model.RawCatalog.PHOTOMETRY__TOTAL in catalogs:
            photometry_total_task = errgr.run(self._query_photometry_total, pgcs_page)

        errgr.wait()

        designation_map = designation_task.result() if designation_task is not None else {}
        additional_designations_map = (
            additional_designations_task.result() if additional_designations_task is not None else {}
        )
        icrs_map = icrs_task.result() if icrs_task is not None else {}
        redshift_map = redshift_task.result() if redshift_task is not None else {}
        nature_map = nature_task.result() if nature_task is not None else {}
        notes_map = notes_task.result() if notes_task is not None else {}
        photometry_total_map = photometry_total_task.result() if photometry_total_task is not None else {}

        return [
            self._layer2_object_from_maps(
                pgc,
                catalogs,
                designation_map,
                additional_designations_map,
                icrs_map,
                redshift_map,
                nature_map,
                notes_map,
                photometry_total_map,
            )
            for pgc in pgcs_page
        ]

    def _layer2_object_from_maps(
        self,
        pgc: int,
        catalogs: list[model.RawCatalog],
        designation_map: dict[int, repo_model.DesignationCatalog],
        additional_designations_map: dict[int, repo_model.AdditionalDesignationsCatalog],
        icrs_map: dict[int, repo_model.ICRSCatalog],
        redshift_map: dict[int, repo_model.RedshiftCatalog],
        nature_map: dict[int, repo_model.NatureCatalog],
        notes_map: dict[int, repo_model.NotesCatalog],
        photometry_total_map: dict[int, repo_model.PhotometryTotalCatalog],
    ) -> repo_model.Layer2Object:
        designation = designation_map.get(pgc) if model.RawCatalog.DESIGNATION in catalogs else None
        additional_designations = (
            additional_designations_map.get(pgc) if model.RawCatalog.ADDITIONAL_DESIGNATIONS in catalogs else None
        )
        icrs = icrs_map.get(pgc) if model.RawCatalog.ICRS in catalogs else None
        redshift = redshift_map.get(pgc) if model.RawCatalog.REDSHIFT in catalogs else None
        nature = nature_map.get(pgc) if model.RawCatalog.NATURE in catalogs else None
        notes = notes_map.get(pgc) if model.RawCatalog.NOTE in catalogs else None
        photometry_total = photometry_total_map.get(pgc) if model.RawCatalog.PHOTOMETRY__TOTAL in catalogs else None

        return repo_model.Layer2Object(
            pgc=pgc,
            catalogs=repo_model.Catalogs(
                designation=designation,
                additional_designations=additional_designations,
                icrs=icrs,
                redshift=redshift,
                nature=nature,
                notes=notes,
                photometry_total=photometry_total,
            ),
        )


def _source_from_row(row: Mapping[str, Any]) -> repo_model.Source:
    author_val = row.get("author")
    authors = author_val if isinstance(author_val, list) else [str(author_val)] if author_val is not None else []
    return repo_model.Source(
        bibcode=str(row["code"]) if row.get("code") is not None else "",
        title=str(row["title"]) if row.get("title") is not None else "",
        authors=authors,
        year=int(row["year"]) if row.get("year") is not None else 0,
    )
