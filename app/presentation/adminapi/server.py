import http
from typing import Annotated

import fastapi
import structlog

from app.lib import audit, auth
from app.lib.web import server
from app.lib.web.middlewares import identity_from_request
from app.presentation.adminapi import interface


def _logout_token(request: fastapi.Request) -> str:
    ctx = identity_from_request(request)
    if ctx is not None:
        return ctx.token
    raw = request.headers.get("Authorization", "").strip()
    parts = raw.split(None, 1)
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1].strip()
    return ""


class API:
    def __init__(self, actions: interface.Actions) -> None:
        self.actions = actions

    def add_data(
        self,
        request: interface.AddDataRequest,
    ) -> server.APIOkResponse[interface.AddDataResponse]:
        response = self.actions.add_data(request)
        return server.APIOkResponse(data=response)

    def create_source(
        self,
        request: interface.CreateSourceRequest,
    ) -> server.APIOkResponse[interface.CreateSourceResponse]:
        response = self.actions.create_source(request)
        return server.APIOkResponse(data=response)

    def create_table(
        self,
        request: interface.CreateTableRequest,
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
    ) -> server.APIOkResponse[interface.PatchTableResponse]:
        response = self.actions.patch_table(request)
        return server.APIOkResponse(data=response)

    def login(
        self, request: fastapi.Request, body: interface.LoginRequest
    ) -> server.APIOkResponse[interface.LoginResponse]:
        _ = request
        response = self.actions.login(body)
        return server.APIOkResponse(data=response)

    def logout(
        self,
        request: fastapi.Request,
        _body: interface.LogoutRequest,
    ) -> server.APIOkResponse[interface.LogoutResponse]:
        return server.APIOkResponse(data=self.actions.logout(_logout_token(request)))

    def get_record_crossmatch(
        self, request: Annotated[interface.GetRecordCrossmatchRequest, fastapi.Query()]
    ) -> server.APIOkResponse[interface.GetRecordCrossmatchResponse]:
        response = self.actions.get_record_crossmatch(request)
        return server.APIOkResponse(data=response)

    def save_structured_data(
        self,
        request: interface.SaveStructuredDataRequest,
    ) -> server.APIOkResponse[interface.SaveStructuredDataResponse]:
        response = self.actions.save_structured_data(request)
        return server.APIOkResponse(data=response)

    def set_crossmatch_results(
        self,
        request: interface.SetCrossmatchResultsRequest,
    ) -> server.APIOkResponse[interface.SetCrossmatchResultsResponse]:
        response = self.actions.set_crossmatch_results(request)
        return server.APIOkResponse(data=response)

    def assign_record_pgcs(
        self,
        request: interface.AssignRecordPgcsRequest,
    ) -> server.APIOkResponse[interface.AssignRecordPgcsResponse]:
        response = self.actions.assign_record_pgcs(request)
        return server.APIOkResponse(data=response)

    def list_designation_rules(
        self,
    ) -> server.APIOkResponse[interface.ListRulesResponse]:
        response = self.actions.list_designation_rules()
        return server.APIOkResponse(data=response)

    def save_designation_rule(
        self,
        request: interface.SaveRuleRequest,
    ) -> server.APIOkResponse[interface.SaveRuleResponse]:
        response = self.actions.save_designation_rule(request)
        return server.APIOkResponse(data=response)


class Server(server.WebServer):
    def __init__(
        self,
        actions: interface.Actions,
        config: server.ServerConfig,
        logger: structlog.stdlib.BoundLogger,
        authenticator: auth.Authenticator,
        action_recorder: audit.ActionRecorder,
        auth_enabled: bool = True,
    ) -> None:
        api = API(actions)
        admin_only = [auth.Role.ADMIN]

        routes: list[server.Route] = [
            server.Route(
                "/v1/table/data",
                http.HTTPMethod.POST,
                api.add_data,
                "Add new data to the table",
                """Inserts new data to the table.
Deduplicates rows based on their contents.
If two rows were identical this method will only insert the last one.""",
                allowed_roles=admin_only,
                audit_action=True,
            ),
            server.Route(
                "/v1/source",
                http.HTTPMethod.POST,
                api.create_source,
                "New internal source entry",
                "Creates new source entry in the database for internal communication and unpublished articles.",
                allowed_roles=admin_only,
                audit_action=True,
            ),
            server.Route(
                "/v1/table",
                http.HTTPMethod.POST,
                api.create_table,
                "Get or create schema for the table.",
                """Creates new schema for the table which can later be used to upload data.
**Important**: If the table with the specified name already exists, does nothing and returns ID
of the previously created table without any alterations.""",
                allowed_roles=admin_only,
                audit_action=True,
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
                """Patches the schema of the table.

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

**Example 3**: Change the table description:
```json
{
    "table_name": "my_table",
    "description": "Photometric catalog from Smith et al."
}
```

**Example 4**: Change the table datatype:
```json
{
    "table_name": "my_table",
    "datatype": "preliminary"
}
```

**Example 5**: Rename the table (updates `layer0.tables` and the physical `rawdata` relation):
```json
{
    "table_name": "my_table",
    "new_table_name": "my_table_v2"
}
```""",
                allowed_roles=admin_only,
                audit_action=True,
            ),
            server.Route(
                "/v1/login",
                http.HTTPMethod.POST,
                api.login,
                "Login",
                "Authenticates user and returns token",
                rate_limit="10/minute",
            ),
            server.Route(
                "/v1/logout",
                http.HTTPMethod.POST,
                api.logout,
                "Logout",
                "Revokes the bearer token used for this request.",
                allowed_roles=admin_only,
                rate_limit="10/minute",
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
                allowed_roles=admin_only,
                audit_action=True,
            ),
            server.Route(
                "/v1/records/pgcs",
                http.HTTPMethod.POST,
                api.assign_record_pgcs,
                "Assign PGCs to records",
                """Assigns PGC numbers to records that already have crossmatch results with
`triage_status = resolved`. Each record must have been set using `POST /v1/records/crossmatch` first.
Records in `pending` triage or with collided metadata are rejected. The request is all-or-nothing.""",
                allowed_roles=admin_only,
                audit_action=True,
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
  "columns": ["design", "raw", "rule_id"],
  "units": {},
  "ids": ["uuid-1", "uuid-2"],
  "data": [["NGC 1234", "ngc 1234", "ngc"], ["NGC 5678", "NGC5678", "ngc"]]
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
                allowed_roles=admin_only,
                audit_action=True,
            ),
            server.Route(
                "/v1/designation/rules",
                http.HTTPMethod.GET,
                api.list_designation_rules,
                "List designation format rules",
                "Returns all designation formatting rules ordered by priority.",
                allowed_roles=admin_only,
            ),
            server.Route(
                "/v1/designation/rule",
                http.HTTPMethod.POST,
                api.save_designation_rule,
                "Save designation format rule",
                """Creates or updates a designation formatting rule.
`rule.id` is the stable free-text identifier and primary key.
Set `rule.enabled` to false to disable a rule instead of deleting it.
When `rule.enabled` is true, optional `examples` are validated before save.""",
                allowed_roles=admin_only,
                audit_action=True,
            ),
        ]

        super().__init__(
            routes,
            config,
            logger,
            authenticator,
            auth_enabled=auth_enabled,
            action_recorder=action_recorder,
        )
