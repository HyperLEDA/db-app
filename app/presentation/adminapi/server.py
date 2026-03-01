import http
from typing import Annotated

import fastapi
import structlog
from fastapi.security import api_key

from app.lib.web import server
from app.presentation.adminapi import interface

api_key_header = api_key.APIKeyHeader(name="Authorization", auto_error=False)


class API:
    def __init__(self, actions: interface.Actions) -> None:
        self.actions = actions

    def add_data(
        self,
        request: interface.AddDataRequest,
        token: str = fastapi.Security(api_key_header),
    ) -> server.APIOkResponse[interface.AddDataResponse]:
        response = self.actions.add_data(request)
        return server.APIOkResponse(data=response)

    def create_source(
        self,
        request: interface.CreateSourceRequest,
        token: str = fastapi.Security(api_key_header),
    ) -> server.APIOkResponse[interface.CreateSourceResponse]:
        response = self.actions.create_source(request)
        return server.APIOkResponse(data=response)

    def create_table(
        self,
        request: interface.CreateTableRequest,
        token: str = fastapi.Security(api_key_header),
    ) -> server.APIOkResponse[interface.CreateTableResponse]:
        response, _ = self.actions.create_table(request)
        return server.APIOkResponse(data=response)

    def get_table(
        self, request: Annotated[interface.GetTableRequest, fastapi.Query()]
    ) -> server.APIOkResponse[interface.GetTableResponse]:
        response = self.actions.get_table(request)
        return server.APIOkResponse(data=response)

    def get_table_list(
        self, request: Annotated[interface.GetTableListRequest, fastapi.Query()]
    ) -> server.APIOkResponse[interface.GetTableListResponse]:
        response = self.actions.get_table_list(request)
        return server.APIOkResponse(data=response)

    def patch_table(
        self,
        request: interface.PatchTableRequest,
        token: str = fastapi.Security(api_key_header),
    ) -> server.APIOkResponse[interface.PatchTableResponse]:
        response = self.actions.patch_table(request)
        return server.APIOkResponse(data=response)

    def login(self, request: interface.LoginRequest) -> server.APIOkResponse[interface.LoginResponse]:
        response = self.actions.login(request)
        return server.APIOkResponse(data=response)

    def get_crossmatch_records(
        self, request: Annotated[interface.GetRecordsCrossmatchRequest, fastapi.Query()]
    ) -> server.APIOkResponse[interface.GetRecordsCrossmatchResponse]:
        response = self.actions.get_crossmatch_records(request)
        return server.APIOkResponse(data=response)

    def get_record_crossmatch(
        self, request: Annotated[interface.GetRecordCrossmatchRequest, fastapi.Query()]
    ) -> server.APIOkResponse[interface.GetRecordCrossmatchResponse]:
        response = self.actions.get_record_crossmatch(request)
        return server.APIOkResponse(data=response)

    def save_structured_data(
        self,
        request: interface.SaveStructuredDataRequest,
        token: str = fastapi.Security(api_key_header),
    ) -> server.APIOkResponse[interface.SaveStructuredDataResponse]:
        response = self.actions.save_structured_data(request)
        return server.APIOkResponse(data=response)

    def set_crossmatch_results(
        self,
        request: interface.SetCrossmatchResultsRequest,
        token: str = fastapi.Security(api_key_header),
    ) -> server.APIOkResponse[interface.SetCrossmatchResultsResponse]:
        response = self.actions.set_crossmatch_results(request)
        return server.APIOkResponse(data=response)


class Server(server.WebServer):
    def __init__(
        self,
        actions: interface.Actions,
        config: server.ServerConfig,
        logger: structlog.stdlib.BoundLogger,
    ) -> None:
        api = API(actions)

        routes: list[server.Route] = [
            server.Route(
                "/v1/table/data",
                http.HTTPMethod.POST,
                api.add_data,
                "Add new data to the table",
                """Inserts new data to the table.
Deduplicates rows based on their contents.
If two rows were identical this method will only insert the last one.""",
            ),
            server.Route(
                "/v1/source",
                http.HTTPMethod.POST,
                api.create_source,
                "New internal source entry",
                "Creates new source entry in the database for internal communication and unpublished articles.",
            ),
            server.Route(
                "/v1/table",
                http.HTTPMethod.POST,
                api.create_table,
                "Get or create schema for the table.",
                """Creates new schema for the table which can later be used to upload data.
**Important**: If the table with the specified name already exists, does nothing and returns ID
of the previously created table without any alterations.""",
            ),
            server.Route(
                "/v1/table",
                http.HTTPMethod.GET,
                api.get_table,
                "Retrieve table information",
                "Fetches details about a specific table using the provided table name",
            ),
            server.Route(
                "/v1/tables",
                http.HTTPMethod.GET,
                api.get_table_list,
                "List tables",
                "Returns a paginated list of tables matching the search query by name or description",
            ),
            server.Route(
                "/v1/table",
                http.HTTPMethod.PATCH,
                api.patch_table,
                "Patch table schema",
                """Patches the schema of the table. Allows updating column metadata (UCD, unit, description).
Only provided fields will be updated; omitted fields will remain unchanged.

**Example 1**: Update column metadata (UCD and unit):
```json
{
    "table_name": "my_table",
    "columns": {
        "ra": {
            "ucd": "pos.eq.ra",
            "unit": "hourangle"
        },
        "dec": {
            "ucd": "pos.eq.dec",
            "unit": "deg"
        }
    }
}
```

**Example 2**: Add a column description:
```json
{
    "table_name": "my_table",
    "columns": {
        "vmag": {
            "description": "Visual magnitude in the V band"
        }
    }
}
```""",
            ),
            server.Route(
                "/v1/login",
                http.HTTPMethod.POST,
                api.login,
                "Login",
                "Authenticates user and returns token",
            ),
            server.Route(
                "/v1/records/crossmatch",
                http.HTTPMethod.GET,
                api.get_crossmatch_records,
                "Get crossmatch records",
                """Retrieves crossmatch records for a specific table with optional filtering.""",
            ),
            server.Route(
                "/v1/records/crossmatch",
                http.HTTPMethod.POST,
                api.set_crossmatch_results,
                "Set crossmatch results",
                """Bulk write crossmatch results. Each entry contains only the fields needed for that status (no nulls).
At least one status block must be present.

**Example 1 – minimal (all new objects):**
```json
{
  "statuses": {
    "new": { "record_ids": ["uuid-1", "uuid-2"] }
  }
}
```

**Example 2 – mixed statuses:**
```json
{
  "statuses": {
    "new": { "record_ids": ["uuid-1", "uuid-2"] },
    "existing": { "record_ids": ["uuid-3"], "pgcs": [42] },
    "collided": {
      "record_ids": ["uuid-4"],
      "possible_matches": [[40, 41, 42]],
      "triage_statuses": ["resolved"]
    }
  }
}
```""",
            ),
            server.Route(
                "/v1/record/crossmatch",
                http.HTTPMethod.GET,
                api.get_record_crossmatch,
                "Get record crossmatch details",
                """Retrieves detailed crossmatch information for a specific record.""",
            ),
            server.Route(
                "/v1/data/structured",
                http.HTTPMethod.POST,
                api.save_structured_data,
                "Write structured data to layer 1",
                """Bulk write columnar data into a layer 1 catalog table. Records are identified by
internal HyperLEDA IDs (must already be registered there). Use `catalog` to target `icrs`,
`designation`, or `redshift`. Column names and units are given once; `data` is a 2D array of rows.
For every column that has unit metadata in the database, the request must include that column in
`units`.

**Example 1 – designation (no units):**
```json
{
  "catalog": "designation",
  "columns": ["design"],
  "units": {},
  "ids": ["uuid-1", "uuid-2"],
  "data": [["NGC 1234"], ["NGC 5678"]]
}
```

**Example 2 – ICRS (with units, values in degrees):**
```json
{
  "catalog": "icrs",
  "columns": ["ra", "dec", "e_ra", "e_dec"],
  "units": {"ra": "deg", "dec": "deg", "e_ra": "deg", "e_dec": "deg"},
  "ids": ["uuid-1"],
  "data": [[100.0, 20.0, 0.5, 0.5]]
}
```
""",
            ),
        ]

        super().__init__(routes, config, logger)
