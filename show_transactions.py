import rpc_pb2 as ln

import lnrpc_helper
from datetime import datetime

stub = lnrpc_helper.get_lightning_stub()


#get channel list
request = ln.ListChannelsRequest(
    active_only=False,
    inactive_only=False,
    public_only=False,
    private_only=False,
)
response_channels = stub.ListChannels(request)


def main():
    
    #todo: show last 1000 events, check if offset is > 1000, and use index_offset = numevents-1000
    request = ln.ForwardingHistoryRequest(
        start_time=1500000000,
        end_time=1700000000,
        index_offset=0,
        num_max_events=1000,
    )
    response_fwdinghistory = stub.ForwardingHistory(request)
    
    for event in response_fwdinghistory.forwarding_events:
        #print(event)
        event_time = int(event.timestamp)
        
        nodealias_in = getNodeAliasFromChanId(event.chan_id_in)
        nodealias_out = getNodeAliasFromChanId(event.chan_id_out)
        
        print(datetime.utcfromtimestamp(event_time).strftime('%Y-%m-%d %H:%M:%S'), '%35s' % nodealias_in, '%35s' % nodealias_out, '%8s' % event.amt_out, '%5s' % event.fee, '%8s' % event.fee_msat)
        
    #print(response_fwdinghistory)
    
def getNodeAliasFromChanId(chanid):
    
    pubkey = None
    
    #lookup node name. not the most efficient. todo: consider caching node alias
    #todo: include closed channels too
    for chan in response_channels.channels:
        if chan.chan_id == chanid:
            pubkey = chan.remote_pubkey
            break
    
    if pubkey is None:
        return 'unknown node:'+str(chan.chan_id)
    else:
        request_nodeinfo = ln.NodeInfoRequest(
            pub_key=pubkey,
        )
        response_nodeinfo = stub.GetNodeInfo(request_nodeinfo)
        node_alias = response_nodeinfo.node.alias
        return node_alias
    
main()
