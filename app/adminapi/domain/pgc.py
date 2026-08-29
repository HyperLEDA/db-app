from typing import final

from app.adminapi import repository
from app.lib.web.errors import NotFoundError
from app.specs import adminapi as spec


@final
class PgcManager:
    def __init__(self, repo: repository.Repository) -> None:
        self._repo = repo

    def merge_pgcs(self, r: spec.MergePgcsRequest) -> spec.MergePgcsResponse:
        all_pgcs = [r.target_pgc, *r.source_pgcs]
        existing = self._repo.get_existing_pgcs(all_pgcs)
        if r.target_pgc not in existing:
            raise NotFoundError(entity_name="pgc", entity=str(r.target_pgc))
        for source_pgc in r.source_pgcs:
            if source_pgc not in existing:
                raise NotFoundError(entity_name="pgc", entity=str(source_pgc))

        with self._repo.with_tx():
            reassigned_records = self._repo.merge_pgcs(r.target_pgc, r.source_pgcs)

        return spec.MergePgcsResponse(
            target_pgc=r.target_pgc,
            merged_pgcs=list(r.source_pgcs),
            reassigned_records=reassigned_records,
        )
