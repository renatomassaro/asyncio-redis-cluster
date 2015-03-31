import asyncio

from asyncio_redis.pool import Pool


def vidalok():

    # There is no need to list all nodes from the cluster. You can connect only
    # to one node, and this one node will gather information from the cluster.

    nodes_one = [
        {'host': '172.17.0.25', 'port': 7000},  # Slave or master
    ]

    nodes_all = [
        {'host': '172.17.0.25', 'port': 7000},  # Slave
        {'host': '172.17.0.26', 'port': 7001},  # Master
        {'host': '172.17.0.27', 'port': 7002},  # Slave
        {'host': '172.17.0.28', 'port': 7003},  # Master
        {'host': '172.17.0.29', 'port': 7004},  # Master
        {'host': '172.17.0.30', 'port': 7005},  # Slave
    ]

    con = yield from Pool().create(nodes=nodes_one, poolsize=3)

    # Test 1:
    # Making a simple call

    yield from con.set('foo', 'bar', debug=True)
    # [DEBUG]: Connecting to Connection(host='172.17.0.29', port=7004)

    key = yield from con.get('foo', debug=True)
    # [DEBUG]: Connecting to Connection(host='172.17.0.29', port=7004)

    print(key)
    # bar

    # Test 2:
    # Calling a different key on a different host

    yield from con.set('foo2', 'bar2', debug=True)
    # [DEBUG]: Connecting to Connection(host='172.17.0.26', port=7001)

    key2 = yield from con.get('foo2', debug=True)
    # [DEBUG]: Connecting to Connection(host='172.17.0.26', port=7001)

    print(key2)
    # bar2

    # Test 3:
    # Lets read multiple times on either master or slave servers. The algorithm
    # will load-balance the requests across unused connections from the pool.

    for _ in range(50):
        f = yield from con.get('foo', debug=True)
        print(f)

        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.30', port=7005)
        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.30', port=7005)
        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.29', port=7004)
        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.29', port=7004)
        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.29', port=7004)
        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.30', port=7005)
        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.30', port=7005)
        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.29', port=7004)
        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.30', port=7005)
        # bar
        # [DEBUG]: Connecting to Connection(host='172.17.0.30', port=7005)
        # ...

    con.close()


if __name__ == '__main__':
    loop = asyncio.get_event_loop()
    loop.run_until_complete(vidalok())
