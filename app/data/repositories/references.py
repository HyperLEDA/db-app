from dataclasses import dataclass
from typing import final

from app.lib.storage import postgres


@dataclass
class ReddeningCoefficient:
    filter: str
    lambda_eff: float
    a_ebv: float


@dataclass
class ReddeningPhotometricSystem:
    id: str
    description: str


@final
class ReferencesRepository(postgres.TransactionalPGRepository):
    def list_reddening_systems(self, r_v: str = "3.1") -> list[ReddeningPhotometricSystem]:
        rows = self._storage.query(
            """
            SELECT DISTINCT s.id, s.description
            FROM photometry.reddening r
            JOIN photometry.systems s ON s.id = r.photsys
            WHERE r.r_v = %s::photometry.r_v_type
            ORDER BY s.id
            """,
            params=[r_v],
        )
        return [
            ReddeningPhotometricSystem(
                id=row["id"],
                description=row["description"],
            )
            for row in rows
        ]

    def list_reddening(self, photsys: str, r_v: str = "3.1") -> list[ReddeningCoefficient]:
        rows = self._storage.query(
            """
            SELECT filter, lambda_eff, a_ebv
            FROM photometry.reddening
            WHERE photsys = %s AND r_v = %s::photometry.r_v_type
            ORDER BY lambda_eff
            """,
            params=[photsys, r_v],
        )
        return [
            ReddeningCoefficient(
                filter=row["filter"],
                lambda_eff=float(row["lambda_eff"]),
                a_ebv=float(row["a_ebv"]),
            )
            for row in rows
        ]
