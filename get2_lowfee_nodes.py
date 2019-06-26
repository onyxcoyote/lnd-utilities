 
import rpc_pb2 as ln

import lnrpc_helper_largemessage as lnrpc_helper #temporary until describegraph is changed

import time

#todo: identify pending channels


minCapacitySat = 5000000
maxFeeRateMilliMsat = 100
maxFeeBaseMsat = 10*1000
minChanCount = 4

maxChanCountToCalcRoutes = 200
minChanCountToCalcRoutes = 40
maxRoutesToQuery = 10 #WARNING! this is very slow. use a low number or 0 if speed is important

pauseBetweenRouteQueriesSeconds = 3.00 #use a non-zero number to help avoid overuse of resources. 0 or a low number for faster speed.


stub = lnrpc_helper.get_lightning_stub()


def areChannelFeesLow(node):
    if node is not None:
        if node.disabled:
            return False
        if node.fee_rate_milli_msat <= maxFeeRateMilliMsat:
            if node.fee_base_msat <= maxFeeBaseMsat:
                return True    
    return False
    
def getCurrentNodePubKey():
    request_getinfo = ln.GetInfoRequest()
    response_getinfo = stub.GetInfo(request_getinfo)
    return response_getinfo.identity_pubkey

    
    
def main():






    #get currently connected channels (additional information)
    request_channels = ln.ListChannelsRequest(
        active_only=False,
        inactive_only=False,
        public_only=False,
        private_only=False,
    )
    response_channels = stub.ListChannels(request_channels)

    
    request_graph = ln.ChannelGraphRequest(
        include_unannounced=False
    )

    response_graph = stub.DescribeGraph(request_graph)
    #print(response)


    dict_pubkey_chancount = {}
    current_node_pub_key = getCurrentNodePubKey()

    for edge in response_graph.edges:
        #print(edge)

        #check that capacity is above X
        if edge.capacity is not None and edge.capacity >= minCapacitySat:
            
            if areChannelFeesLow(edge.node1_policy):
                if(edge.node1_pub not in dict_pubkey_chancount):
                    dict_pubkey_chancount[edge.node1_pub]=1
                else:
                    current_count=dict_pubkey_chancount.get(edge.node1_pub)
                    dict_pubkey_chancount[edge.node1_pub]=current_count+1   
                #print(edge.node1_pub)


            if areChannelFeesLow(edge.node2_policy):
                if(edge.node2_pub not in dict_pubkey_chancount):
                    dict_pubkey_chancount[edge.node2_pub]=1
                else:
                    current_count=dict_pubkey_chancount.get(edge.node2_pub)
                    dict_pubkey_chancount[edge.node2_pub]=current_count+1
                #print(edge.node2_pub)

    routesQueried = 0

    #print sorted by channel count (value)
    for chanCount in sorted(set(dict_pubkey_chancount.values()), reverse=True):
        if chanCount >= minChanCount:
        
            for pubkey,count in dict_pubkey_chancount.items():
                if(count == chanCount):
                    
                    #get info about remote node
                    request_nodeinfo = ln.NodeInfoRequest(
                        pub_key=pubkey,
                    )
                    response_nodeinfo = stub.GetNodeInfo(request_nodeinfo)
                    node_alias = response_nodeinfo.node.alias
                    
                    #check to see if we're connected
                    connected = False
                    for connectedChannel in response_channels.channels:
                        if(pubkey==connectedChannel.remote_pubkey):
                            connected = True    
                    
                    if(connected):
                        connectedText = '(connected)'
                    elif(current_node_pub_key==pubkey):
                        connectedText = '(self)'
                    else:
                        connectedText = ''
                    
                    route_fee='n/a'
                    first_hop='n/a'
                    hop_count=0
                    if(count >= minChanCountToCalcRoutes):
                        if(count <= maxChanCountToCalcRoutes):
                            #query route to node (might be computationally expensive)
                            request_route = ln.QueryRoutesRequest(
                                pub_key=pubkey,
                                amt=1000000,
                            )
                            
                            if(routesQueried < maxRoutesToQuery):
                                routesQueried += 1
                                try:
                                    response_route = stub.QueryRoutes(request_route)
                                
                                    route_fee=str(response_route.routes[0].total_fees)+'sat'
                                    
                                    first_hop = response_route.routes[0].hops[0].chan_id
                                    
                                    hop_count = len(response_route.routes[0].hops)
                                    
                                    time.sleep(pauseBetweenRouteQueriesSeconds)

                                except (KeyboardInterrupt, SystemExit):
                                    raise
                                except Exception as e:
                                    if(hasattr(e, 'details')):
                                        if('unable to find a path to destination' in str(e.details)):
                                            route_fee = 'NO PATH!'
                                        else:
                                            route_fee = 'ERROR with details'
                                            print(e.details)
                                            print(str(e))
                                    else:
                                        route_fee = 'UNKNOWN ERROR'
                                        print(str(e))

                                #print(dir(response_route))
                                
                            else:
                                route_fee='(queries >)'
                        else:
                            route_fee='(skip >)'
                    else:
                        route_fee='(skip <)'

                                                
                            
                    
                    print(pubkey, ":",'%5s' % count, '%6s' % route_fee, '%11s' % connectedText, '%35s' % node_alias.encode('ascii','ignore'), '%12s' % first_hop, '%2s' % hop_count)
                    #print(response_nodeinfo)



main()

