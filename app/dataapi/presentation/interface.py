import abc

from app.specs.dataapi import interface, tap


class Actions(abc.ABC):
    @abc.abstractmethod
    def query_simple(self, query: interface.QuerySimpleRequest) -> interface.QuerySimpleResponse:
        pass

    @abc.abstractmethod
    def tap_tables(self, request: tap.ListTAPTablesRequest) -> tap.ListTAPTablesResponse:
        pass

    @abc.abstractmethod
    def tap_sync(self, request: tap.TAPSyncRequest) -> tap.TAPSyncResponse:
        pass
