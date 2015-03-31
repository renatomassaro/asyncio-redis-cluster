# -*- coding: utf-8 -*-

# python std lib
import asyncio

# rediscluster imports
from .exceptions import NodeError
from .connection import Connection


class NodeManager:
    RedisClusterHashSlots = 16384

    def __init__(self, startup_nodes=None):
        self.nodes = {}
        self.slots = {}
        self.startup_nodes = [] if startup_nodes is None else startup_nodes
        self.orig_startup_nodes = [node for node in self.startup_nodes]
        self.refresh_table_asap = None
        self.pubsub_node = None

        if len(self.startup_nodes) == 0:
            raise NodeError("No startup nodes provided")

    @asyncio.coroutine
    def get_redis_link(self, host, port, decode_responses=False):
        if decode_responses:
            raise NotImplementedError
        return Connection.create(host=host, port=port)

    @staticmethod
    def get_slave_from(host_id, slave_list):
        for slave in slave_list:
            if slave[3] == host_id:
                return slave[1]
        raise Exception

    @asyncio.coroutine
    def initialize(self):
        """
        Init the slots cache by asking all startup nodes what the current
        cluster configuration is

        TODO: Currently the last node will have the last say about how the
        configuration is setup.
        Maybe it should stop to try after it have correctly covered all slots
        or when one node is reached and it could execute CLUSTER NODES command.
        """
        # Reset variables
        self.flush_nodes_cache()
        self.flush_slots_cache()
        disagreements = []
        node = self.startup_nodes[0]

        try:
            r = yield from self.get_redis_link(host=node["host"],
                                               port=int(node["port"]),
                                               decode_responses=False)
            cluster_slots = yield from r.cluster("nodes")
            r.close()
        except Exception as e:
            raise NodeError("ERROR sending 'cluster nodes' command to redis se"
                            "rver: {}".format(node))

        all_slots_covered = True

        cluster_slots = cluster_slots.splitlines()
        node_list = []
        slave_list = []
        master_list = []

        for node in cluster_slots:
            node_info = node.split(' ')
            node_list.append(node_info)
            if node_info[2] == 'master' or node_info[2] == 'myself,master':
                master_list.append(node_info)
            else:
                slave_list.append(node_info)

        for slot in master_list:
            ip, port = slot[1].split(':')
            self.set_node(ip, port, server_type='master')

        for slot in slave_list:
            ip, port = slot[1].split(':')
            self.set_node(ip, port, server_type='slave')

        for node in master_list:

            slot_start, slot_finish = node[8].split('-')
            for i in range(int(slot_start), int(slot_finish) + 1):
                if i not in self.slots:
                    self.slots[i] = [node[1],
                                     self.get_slave_from(node[0], slave_list)]
                else:
                    # Validate that 2 nodes want to use the same slot cache
                    if self.slots[i]['name'] != node['name']:
                        disagreements.append("{} vs {} on slot: {}".format(
                            self.slots[i]['name'], node['name'], i))
                        if len(disagreements) > 5:
                            raise NodeError("startup_nodes could not agree on "
                                            "a valid slots cache. %s" % ", "
                                            .join(disagreements))

        self.populate_startup_nodes()
        self.refresh_table_asap = False

        # Validate if all slots are covered or if we should try next node
        for i in range(0, self.RedisClusterHashSlots):
            if i not in self.slots:
                all_slots_covered = False

        if all_slots_covered:
            # All slots are covered and application can continue to execute
            # Parse and determine what node will be pubsub node
            self.determine_pubsub_node()
            return

        if not all_slots_covered:
            raise NodeError("All slots are not covered after query all startup"
                            "_nodes. {} of {} covered..."
                            .format(len(self.slots),
                                    self.RedisClusterHashSlots))

    def determine_pubsub_node(self):
        """
        Determine what node object should be used for pubsub commands.

        All clients in the cluster will talk to the same pubsub node to ensure
        all code stay compatible. See pubsub doc for more details why.

        Allways use the server with highest port number
        """
        highest = -1
        node = None
        for n in self.nodes.values():
            if n["port"] > highest:
                highest = n["port"]
                node = n
        self.pubsub_node = {"host": node["host"], "port": node["port"], "server_type": node["server_type"], "pubsub": True}

    def set_node_name(self, n):
        """
        Format the name for the given node object

        # TODO: This shold not be constructed this way. It should update the name of the node in the node cache dict
        """
        if "name" not in n:
            n["name"] = "{0}:{1}".format(n["host"], n["port"])

    def set_node(self, host, port, server_type=None):
        """
        Update data for a node.
        """
        node_name = "{0}:{1}".format(host, port)
        self.nodes.setdefault(node_name, {})
        self.nodes[node_name]['host'] = host
        self.nodes[node_name]['port'] = int(port)
        self.nodes[node_name]['name'] = node_name

        if server_type:
            self.nodes[node_name]['server_type'] = server_type

        return self.nodes[node_name]

    def populate_startup_nodes(self):
        """
        Do something with all startup nodes and filters out any duplicates
        """
        for item in self.startup_nodes:
            self.set_node_name(item)
        for n in self.nodes.values():
            if n not in self.startup_nodes:
                self.startup_nodes.append(n)
        # freeze it so we can set() it
        uniq = set([frozenset(node.items()) for node in self.startup_nodes])
        # then thaw it back out into a list of dicts
        self.startup_nodes = [dict(node) for node in uniq]

    def reset(self):
        """
        Drop all node data and start over from startup_nodes
        """
        self.flush_nodes_cache()
        self.flush_slots_cache()
        self.initialize()

    def flush_slots_cache(self):
        """
        Reset slots cache back to empty dict
        """
        self.slots = {}

    def flush_nodes_cache(self):
        """
        Reset nodes cache back to empty dict
        """
        self.nodes = {}
