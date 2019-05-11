#run this with ./get_lowfee_nodes.sh
import json


minCapacitySat = 5000000
maxFeeRateMilliMsat = 1
maxFeeBaseMsat = 10


def queryNodes():
    file = open("graph.tmp", "r")
    input = file.read()

    jsongraph = json.loads(input)

    #the graph has "nodes" and "edges"
    edges = jsongraph['edges']

    for edge in edges:

        #check that capacity is above X
        capacity = edge['capacity']
        if capacity is not None and int(float(capacity)) >= minCapacitySat:
            node = edge['node1_policy']
            if areChannelFeesLow(node):
                print(edge['node1_pub'])

            node = edge['node2_policy']
            if areChannelFeesLow(node):
                print(edge['node2_pub'])


def areChannelFeesLow(node):
    if node is not None:
        node_fee_rate_milli_msat = int(float(node['fee_rate_milli_msat']))
        if node_fee_rate_milli_msat <= maxFeeRateMilliMsat:
            node_fee_base_msat = int(float(node['fee_base_msat']))
            if node_fee_base_msat <= maxFeeBaseMsat:
                return True    
    return False


queryNodes()
