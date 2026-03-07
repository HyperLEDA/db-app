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

    def get_records(
        self, request: Annotated[interface.GetRecordsRequest, fastapi.Query()]
    ) -> server.APIOkResponse[interface.GetRecordsResponse]:
        response = self.actions.get_records(request)
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

    def create_marking(
        self,
        request: interface.CreateMarkingRequest,
        token: str = fastapi.Security(api_key_header),
    ) -> server.APIOkResponse[interface.CreateMarkingResponse]:
        response = self.actions.create_marking(request)
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
                "/v1/records",
                http.HTTPMethod.GET,
                api.get_records,
                "List records",
                "Returns a paginated list of records for a table with their original data.",
            ),
            server.Route(
                "/v1/table",
                http.HTTPMethod.PATCH,
                api.patch_table,
                "Patch table schema",
                """Patches the schema of the table. Allows updating column metadata (UCD, unit, description) and 
setting column modifiers. Modifiers are transformations applied to column values during the unification process.

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
```

**Example 3**: Set a `map` modifier to convert categorical string values to numeric ones. 
For instance, mapping morphological types to numeric codes:
```json
{
    "table_name": "my_table",
    "columns": {
        "morph_type": {
            "modifiers": [
                {
                    "name": "map",
                    "params": {
                        "mapping": [
                            {"from": "E", "to": -5},
                            {"from": "S0", "to": 0},
                            {"from": "Sa", "to": 1},
                            {"from": "Sb", "to": 3}
                        ],
                        "default": null
                    }
                }
            ]
        }
    }
}
```

**Example 4**: Set a `format` modifier to reformat string values using a Python format pattern:
```json
{
    "table_name": "my_table",
    "columns": {
        "obj_id": {
            "modifiers": [
                {
                    "name": "format",
                    "params": {
                        "pattern": "SDSS J{}"
                    }
                }
            ]
        }
    }
}
```

**Example 5**: Set an `add_unit` modifier to override the unit attached to a column during processing:
```json
{
    "table_name": "my_table",
    "columns": {
        "velocity": {
            "modifiers": [
                {
                    "name": "add_unit",
                    "params": {
                        "unit": "km/s"
                    }
                }
            ]
        }
    }
}
```

**Example 6**: Set a `constant` modifier to replace all values in a column with a fixed value:
```json
{
    "table_name": "my_table",
    "columns": {
        "survey": {
            "modifiers": [
                {
                    "name": "constant",
                    "params": {
                        "constant": "SDSS"
                    }
                }
            ]
        }
    }
}
```

**Example 7**: Combine metadata updates with modifiers in a single request:
```json
{
    "table_name": "my_table",
    "columns": {
        "ra": {
            "ucd": "pos.eq.ra",
            "unit": "deg",
            "modifiers": [
                {
                    "name": "add_unit",
                    "params": {
                        "unit": "hourangle"
                    }
                }
            ]
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
                "/v1/marking",
                http.HTTPMethod.POST,
                api.create_marking,
                "New marking rules for the table",
                """Creates new marking rules to map the columns in the table to catalog parameters. 
For a given table a marking would consist of the mapping between catalog parameters 
and the columns from the original table.

For example, if one wants to create a marking for a column `object_name` that designates the name of an object,
they should create a catalog entry similar to the following:
```json
{
    "name": "designation",
    "parameters": {
        "design": {
            "column_name": "object_name"
        }
    }
}
```

Here, `name` respresents the name of the catalog, keys of `parameters` map are parameter names and `column_name`
values are actual names of the columns under question. **For now, only one column per parameter is supported.**

It is possible to create several catalog entries for a single object, for example - is there are two columns
that represent a name of an object. In that case we might want to upload both names to the database so it is
easier to cross-identify and search these objects later. Another use case might be if there are several columns
that represent photometric information in different filters. In that case one might want to create one entry
for each of the magnitude columns.

In that case you can specify several entries into `rules` list with different values of `key`. For example:

```json
{
    "table_name": "my_table",
    "rules": [
        {
            "name": "designation",
            "parameters": {
                "design": {
                    "column_name": "object_name"
                }
            },
            "key": "primary_name"
        },
        {
            "name": "designation",
            "parameters": {
                "design": {
                    "column_name": "secondary_object_name"
                }
            },
            "key": "secondary_name"
        }
    ]
}
```

The result of this would be two entries into the `designation` catalog for each object in the original table.

This handler also supports additional parameters that are not present in the original table. For example, a
table might not have a separate column for astrometric errors but from other sources you know that its error is
0.1 degrees for right ascension and 0.5 degrees for declination. You can specify this in the
`additional_params` field for each catalog:

```json
{
    "name": "icrs",
    "parameters": {
        "ra": {
            "column_name": "RAJ2000"
        },
        "dec": {
            "column_name": "DEJ2000"
        }
    },
    "additional_params": {
        "e_ra": 0.1,
        "e_dec": 0.5
    }
}
```""",
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
