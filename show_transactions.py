from datetime import date
from datetime import timedelta
from datetime import datetime
import time

import rpc_pb2 as ln

import lnrpc_helper


stub = lnrpc_helper.get_lightning_stub()


#get channel list
request = ln.ListChannelsRequest(
    active_only=False,
    inactive_only=False,
    public_only=False,
    private_only=False,
)
response_channels = stub.ListChannels(request)

def dateTimeToUnixTime(inDateTime):
    unixTime = time.mktime(inDateTime.timetuple())
    return unixTime

def main():

    today = date.today()
    threeMonthsAgo = today - timedelta(days=90)
    tomorrow = today + timedelta(days=1)

    #todo: adjust max number of events
    request = ln.ForwardingHistoryRequest(
        start_time=int(dateTimeToUnixTime(threeMonthsAgo)),
        end_time=int(dateTimeToUnixTime(tomorrow)),
        #start_time=1570000000,
        #end_time=1700000000,
        index_offset=0,
        num_max_events=10000,
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
