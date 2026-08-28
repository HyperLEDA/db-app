import abc

from app.specs import dataapi as spec


class Actions(abc.ABC):
    @abc.abstractmethod
    def query_simple(self, query: spec.QuerySimpleRequest) -> spec.QuerySimpleResponse:
        pass

    @abc.abstractmethod
    def tap_tables(self, request: spec.ListTAPTablesRequest) -> spec.ListTAPTablesResponse:
        pass

    @abc.abstractmethod
    def tap_sync(self, request: spec.TAPSyncRequest) -> spec.TAPSyncResponse:
        pass
