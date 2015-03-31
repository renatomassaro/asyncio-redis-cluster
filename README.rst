Cluster support for asyncio Redis client 
================================

Redis client for the `PEP 3156`_ Python event loop with cluster support.  

Forked from `asyncio-redis`_ and heavily inspired by `redis-py-cluster`_.
It is completely untested and unreliable, but it works. Use at your own risk. You were warned.

.. _PEP 3156: http://legacy.python.org/dev/peps/pep-3156/
.. _asyncio-redis: https://github.com/jonathanslenders/asyncio-redis
.. _redis-py-cluster: https://github.com/Grokzen/redis-py-cluster

This Redis library is a completely asynchronous, non-blocking client for a
Redis server. It depends on asyncio (PEP 3156) and therefor it requires Python
3.3 or 3.4. If you're new to asyncio, it can be helpful to check out
`the asyncio documentation`_ first.

.. _the asyncio documentation: http://docs.python.org/dev/library/asyncio.html


Cluster Client Example
------------------

Cluster client currently only works with connection pooling.  

All requests will be  automatically load balanced. It assumes you have master (read/write) 
and slave (read-only)  instances. Therefore, all writable requests will be loaded only 
to the corresponding master, and all read requests (get, hget, hmget) will be balanced 
between master and slave.

Please note that redis cluster has some limitations when compared to default redis, like 
no pipeline support or a limited set of commands. This lib does not check for these limitations,
so you have to make sure to use only valid commands within the redis cluster domain. For more 
information read the official redis documentation.


.. code:: python
    
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
    
        # A poolsize of N means that N connections will be created on **each** link.
        # So if you have a poolsize of 5, with 6 servers, expect at least 30 
        # connections to be created.
        con = yield from Pool().create(nodes=nodes_one, poolsize=5)
    
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

Features
--------

- Works for the asyncio (PEP3156) event loop (YEAH)
- No dependencies except asyncio (YEAH)
- Connection pooling (YEAH)
- Automatic conversion from unicode (Python) to bytes (inside Redis.) (YEAH)
- Bytes and str protocols. (YEAH)
- Completely tested (NOPE)
- Blocking calls and transactions supported (NOT TESTED)
- Streaming of some multi bulk replies (NOT TESTED)
- Pubsub support (NOT TESTED)


Installation
------------

.. code::

    pip install asyncio_redis

Documentation
-------------

Who needs documentation?  
Just kidding, check asyncio-redis official documentation below.  
As for cluster support, check the example.

View documentation at `read-the-docs`_

.. _read-the-docs: http://asyncio-redis.readthedocs.org/en/latest/




Transactions example
--------------------

.. code:: python

    import asyncio
    import asyncio_redis

    @asyncio.coroutine
    def example():
        # Create Redis connection
        connection = yield from asyncio_redis.Pool.create(host='localhost', port=6379, poolsize=10)

        # Create transaction
        transaction = yield from connection.multi()

        # Run commands in transaction (they return future objects)
        f1 = yield from transaction.set('key', 'value')
        f2 = yield from transaction.set('another_key', 'another_value')

        # Commit transaction
        yield from transaction.exec()

        # Retrieve results
        result1 = yield from f1
        result2 = yield from f2

        # When finished, close the connection pool.
        connection.close()

It's recommended to use a large enough poolsize. A connection will be occupied
as long as there's a transaction running in there.


Pubsub example
--------------

.. code:: python

    import asyncio
    import asyncio_redis

    @asyncio.coroutine
    def example():
        # Create connection
        connection = yield from asyncio_redis.Connection.create(host='localhost', port=6379)

        # Create subscriber.
        subscriber = yield from connection.start_subscribe()

        # Subscribe to channel.
        yield from subscriber.subscribe([ 'our-channel' ])

        # Inside a while loop, wait for incoming events.
        while True:
            reply = yield from subscriber.next_published()
            print('Received: ', repr(reply.value), 'on channel', reply.channel)

        # When finished, close the connection.
        connection.close()


LUA Scripting example
---------------------

.. code:: python

    import asyncio
    import asyncio_redis

    code = \
    """
    local value = redis.call('GET', KEYS[1])
    value = tonumber(value)
    return value * ARGV[1]
    """

    @asyncio.coroutine
    def example():
        connection = yield from asyncio_redis.Connection.create(host='localhost', port=6379)

        # Set a key
        yield from connection.set('my_key', '2')

        # Register script
        multiply = yield from connection.register_script(code)

        # Run script
        script_reply = yield from multiply.run(keys=['my_key'], args=['5'])
        result = yield from script_reply.return_value()
        print(result) # prints 2 * 5

        # When finished, close the connection.
        connection.close()


Example using the Protocol class
--------------------------------

.. code:: python

    import asyncio
    import asyncio_redis

    @asyncio.coroutine
    def example():
        loop = asyncio.get_event_loop()

        # Create Redis connection
        transport, protocol = yield from loop.create_connection(
                    asyncio_redis.RedisProtocol, 'localhost', 6379)

        # Set a key
        yield from protocol.set('my_key', 'my_value')

        # Get a key
        result = yield from protocol.get('my_key')
        print(result)

        # Close transport when finished.
        transport.close()

    if __name__ == '__main__':
        asyncio.get_event_loop().run_until_complete(example())



.. |Build Status| image:: https://travis-ci.org/jonathanslenders/asyncio-redis.png
    :target: https://travis-ci.org/jonathanslenders/asyncio-redis#

.. |Build Status2| image:: https://drone.io/github.com/jonathanslenders/asyncio-redis/status.png
    :target: https://drone.io/github.com/jonathanslenders/asyncio-redis/latest
