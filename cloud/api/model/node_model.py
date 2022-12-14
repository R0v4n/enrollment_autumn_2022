from datetime import datetime
from typing import Any

from aiohttp.web_exceptions import HTTPNotFound, HTTPBadRequest

from .base_model import BaseImportModel
from .data_classes import ItemType, ExportItem
from .node_tree import ExportNodeTree
from .query_builder import FileQuery, FolderQuery, Sign, QueryT


class NodeModel(BaseImportModel):

    __slots__ = ('node_id', '_query', '_node_type')

    def __init__(self, node_id: str, date: datetime | None = None):

        super().__init__(date)
        self.node_id = node_id
        self._query = None
        self._node_type = None

    @property
    def query(self) -> type[QueryT]:
        return self._query

    @property
    def node_type(self) -> ItemType:
        return self._node_type

    async def init(self, connection):
        await super().init(connection)
        for self._query, self._node_type in zip([FileQuery, FolderQuery], ItemType):
            node_exists = await self.conn.fetchval(self._query.exist(self.node_id))

            if node_exists:
                return

        raise HTTPNotFound()

    async def get_node(self) -> dict[str, Any]:
        res = await self.conn.fetch(self.query.get_node_select_query(self.node_id))
        # In general from_records returns a list[NodeTree]. In this case it will always be a single NodeTree list.
        tree = ExportNodeTree.from_records(res)[0]
        return tree.dict(by_alias=True)

    async def execute_delete_node(self):
        await self.insert_import()

        parents = self.query.recursive_parents(self.node_id)
        history_q = FolderQuery.insert_history_from_select(parents)

        file_id, folder_id = (self.node_id, None) if self.node_type == ItemType.FILE else (None, self.node_id)
        update_q = FolderQuery.update_parent_sizes(file_id, folder_id, self.import_id, Sign.SUB)

        await self.conn.execute(history_q)
        await self.conn.execute(update_q)
        await self.conn.execute(self.query.delete(self.node_id))

    async def get_node_history(self, date_start: datetime, date_end: datetime) -> list[dict[str, Any]]:

        if date_start >= date_end or date_end.tzinfo is None or date_start.tzinfo is None:
            raise HTTPBadRequest

        query = self.query.select_nodes_union_history_in_daterange(date_start, date_end, self.node_id, closed=False)

        res = await self.conn.fetch(query)
        nodes = [ExportItem.construct(type=self.node_type, **rec).dict(by_alias=True) for rec in res]

        return nodes
