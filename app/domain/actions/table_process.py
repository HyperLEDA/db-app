from app import commands
from app.domain import model as domain_model


def table_process(depot: commands.Depot, r: domain_model.TableProcessRequest) -> domain_model.TableProcessResponse:
    return domain_model.TableProcessResponse()
