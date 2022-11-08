import json
from datetime import datetime, timezone
from http import HTTPStatus

import pytest
from devtools import debug

from cloud.utils.testing import post_import, FakeCloud, del_node, compare_db_fc_state, File


async def test_with_fake_cloud(api_client, sync_connection):
    fake_cloud = FakeCloud()

    # ################################################################### #
    fake_cloud.generate_import([1, [2, [2, [2]]]], 2, [])
    await post_import(api_client, fake_cloud.get_import_dict())

    f1 = fake_cloud.get_node_copy('d1/d1/d1/f1')
    f2 = fake_cloud.get_node_copy('d1/d1/d1/f2')
    f3 = fake_cloud.get_node_copy('f1')
    f4 = fake_cloud.get_node_copy('f2')

    d1 = fake_cloud.get_node_copy('d1')
    d2 = fake_cloud.get_node_copy('d2')
    d3 = fake_cloud.get_node_copy('d1/d1')
    d4 = fake_cloud.get_node_copy('d1/d1/d1')
    # ################################################################### #
    # del f1
    del_date = fake_cloud.del_item(f1.id)
    await del_node(api_client, f1.id, del_date)

    compare_db_fc_state(sync_connection, fake_cloud)
    # ################################################################### #
    # import new file in d4 and update f2 in this dir
    fake_cloud.generate_import(1, parent_id=d4.id)
    fake_cloud.update_item(f2.id, size=50, url='la-la-lend')
    await post_import(api_client, fake_cloud.get_import_dict())

    compare_db_fc_state(sync_connection, fake_cloud)
    # ################################################################### #
    # del d3
    del_date = fake_cloud.del_item(d3.id)
    await del_node(api_client, d3.id, del_date)

    compare_db_fc_state(sync_connection, fake_cloud)
    # ################################################################### #
    # del d2
    del_date = fake_cloud.del_item(d2.id)
    await del_node(api_client, d2.id, del_date)

    compare_db_fc_state(sync_connection, fake_cloud)
    # ################################################################### #
    # del f3
    del_date = fake_cloud.del_item(f3.id)
    await del_node(api_client, f3.id, del_date)

    compare_db_fc_state(sync_connection, fake_cloud)
    # ################################################################### #
    # update f4
    fake_cloud.generate_import()
    fake_cloud.update_item(f4.id, size=100, url='la-la-lend-2', parent_id=d1.id)
    await post_import(api_client, fake_cloud.get_import_dict())

    compare_db_fc_state(sync_connection, fake_cloud)
    # ################################################################### #
    # del f4
    del_date = fake_cloud.del_item(f4.id)
    await del_node(api_client, f4.id, del_date)

    compare_db_fc_state(sync_connection, fake_cloud)
    # ################################################################### #


async def test_delete_old_parent(api_client, sync_connection):
    """Change file parent folder, then del this folder. File should stay in history."""
    fake_cloud = FakeCloud()
    fake_cloud.generate_import([1])
    await post_import(api_client, fake_cloud.get_import_dict())

    f1 = fake_cloud.get_node_copy('d1/f1')
    d1 = fake_cloud.get_node_copy('d1')

    fake_cloud.generate_import()
    fake_cloud.update_item(f1.id, parent_id=None)
    await post_import(api_client, fake_cloud.get_import_dict())

    date = fake_cloud.del_item(d1.id)
    await del_node(api_client, d1.id, date)

    compare_db_fc_state(sync_connection, fake_cloud)


fake_cloud = FakeCloud()
fake_cloud.generate_import([1])

CASES = [
    # non existing node id
    (File().id, datetime.now(timezone.utc), HTTPStatus.NOT_FOUND),
    # invalid date format (no tz)
    (fake_cloud.get_node_copy('d1').id, '2022-02-01 12:00:00', HTTPStatus.BAD_REQUEST)
]


@pytest.mark.parametrize(('node_id', 'date', 'expected_status'), CASES)
async def test_cases(api_client, sync_connection, node_id, date, expected_status):
    await del_node(api_client, node_id, date, expected_status)
