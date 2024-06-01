import datetime

from app import commands
from app.data import model as data_model
from app.domain import model as domain_model
from app.lib.exceptions import new_validation_error


def create_source(depot: commands.Depot, r: domain_model.CreateSourceRequest) -> domain_model.CreateSourceResponse:
    if r.bibcode is not None:
        try:
            publication = depot.clients.ads.query_simple(f'bibcode:"{r.bibcode}"')[0]

            r.title = publication["title"][0]
            r.authors = list(publication["author"])
            r.year = (
                datetime.datetime.strptime(publication["pubdate"], "%Y-%m-00").astimezone(datetime.timezone.utc).year
            )
        except RuntimeError as e:
            raise new_validation_error("no search results returned for bibcode from ADS") from e

    source_id = depot.common_repo.create_bibliography(
        data_model.Bibliography(bibcode=r.bibcode, year=r.year, author=r.authors, title=r.title)
    )

    return domain_model.CreateSourceResponse(id=source_id)
