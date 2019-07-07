#import codecs, grpc, os
import rpc_pb2 as ln
#import rpc_pb2_grpc as lnrpc

import lnrpc_helper


#todo; include pending channels



stub = lnrpc_helper.get_lightning_stub()

all_channel_val = 0.00000000
all_channel_cap = 0.00000000

def printOneChannel(chan,chantype):
    
    global all_channel_val
    global all_channel_cap
    
    #print(dir(chan))
    
    if(chantype == 'active'):
        pubkey = chan.remote_pubkey
        channel = chan
        chanid = chan.chan_id
        chanactive = chan.active
        
        #if the other party opened the channel and is responsible for the commit fee, don't count it as part of my funds
        if(channel.initiator):
            my_commit_fee = chan.commit_fee
        else:
            my_commit_fee = 0
    elif(chantype == 'pending'):
        pubkey = chan.channel.remote_node_pub
        channel = chan.channel
        chanid = 'PENDING'
        chanactive = 'pnd..'    
        
        #if the other party opened the channel and is responsible for the commit fee, don't count it as part of my funds
        #NOTE: there is no initiator field, we could miscalculate total balance if it's an incoming channel. instead using a workaround that only works with channels with 1 initiator (currently all channels)
        if(channel.local_balance > 0):
            my_commit_fee = chan.commit_fee 
        else:
            my_commit_fee = 0 
    else:
        print('unknown chantype')
        print(chantype)
    
    #get node alias
    request_nodeinfo = ln.NodeInfoRequest(
        pub_key=pubkey,
    )
    response_nodeinfo = stub.GetNodeInfo(request_nodeinfo)
    node_alias = response_nodeinfo.node.alias
    
    
    local_pct = round(100*channel.local_balance/channel.capacity,1)
              
            
    print('%35s' % node_alias.encode('ascii','ignore'), '%18s' % chanid, pubkey, 'active: ', '%5s' % chanactive, 'remotebal:', '%8s' % channel.remote_balance, '%9s' % (my_commit_fee+channel.local_balance), '%7s' % my_commit_fee, 'localbal:', '%9s' % channel.local_balance, '/', '%9s' % channel.capacity, ' = ',  '%5s' % str(local_pct),'%')

    all_channel_val += (my_commit_fee+channel.local_balance)
    all_channel_cap += channel.capacity
    
    

def main():
    request = ln.ListChannelsRequest(
        active_only=False,
        inactive_only=False,
        public_only=False,
        private_only=False,
    )
    response = stub.ListChannels(request)

    

    if True:
        print('%35s' % 'chan_alias', '%18s' % 'chan_id', '%66s' % 'chan.remote_pubkey', 'active: ', '    ', 'remote balance', 'bal+fee', 'commit fee', 'local balance:', '%9s' % 'local_balance', 'chan_capacity', '%9s' % 'capacity %')
    for chan in response.channels:
        printOneChannel(chan, 'active')
        

    request_pending = ln.PendingChannelsRequest()
    response_pending = stub.PendingChannels(request_pending)
    #print(response_pending)

    for chan in response_pending.pending_open_channels:
        #print(chan)
        printOneChannel(chan, 'pending')
        
    
    print('total_limbo_balance=',response_pending.total_limbo_balance)
        

    tot_local_pct = round(100*all_channel_val/all_channel_cap,1)
    print('TOTAL (sat): ',all_channel_val,'/',all_channel_cap, '=', str(tot_local_pct),'%' )
    print('TOTAL (BTC): ',all_channel_val/100000000,'BTC','/',all_channel_cap/100000000,'BTC')


    #for chan in response:
    #    print(chan.active)
    
    
main()



    #LISTCHANNELS.channels
    #channel properties
    #['ByteSize', 'Clear', 'ClearExtension', 'ClearField', 'CopyFrom', 'DESCRIPTOR', 'DiscardUnknownFields', 'Extensions', 'FindInitializationErrors', 'FromString', 'HasExtension', 'HasField', 'IsInitialized', 'ListFields', 'MergeFrom', 'MergeFromString', 'ParseFromString', 'RegisterExtension', 'SerializePartialToString', 'SerializeToString', 'SetInParent', 'UnknownFields', 'WhichOneof', '_CheckCalledFromGeneratedFile', '_SetListener', '__class__', '__deepcopy__', '__delattr__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__setstate__', '__sizeof__', '__slots__', '__str__', '__subclasshook__', '__unicode__', '_extensions_by_name', '_extensions_by_number', 'active', 'capacity', 'chan_id', 'chan_status_flags', 'channel_point', 'commit_fee', 'commit_weight', 'csv_delay', 'fee_per_kw', 'initiator', 'local_balance', 'num_updates', 'pending_htlcs', 'private', 'remote_balance', 'remote_pubkey', 'total_satoshis_received', 'total_satoshis_sent', 'unsettled_balance']


    #LISTCHANNELS
    #print(type(response))
    #print(dir(response))
    #<class 'rpc_pb2.ListChannelsResponse'>
    #['ByteSize', 'Clear', 'ClearExtension', 'ClearField', 'CopyFrom', 'DESCRIPTOR', 'DiscardUnknownFields', 'Extensions', 'FindInitializationErrors', 'FromString', 'HasExtension', 'HasField', 'IsInitialized', 'ListFields', 'MergeFrom', 'MergeFromString', 'ParseFromString', 'RegisterExtension', 'SerializePartialToString', 'SerializeToString', 'SetInParent', 'UnknownFields', 'WhichOneof', '_CheckCalledFromGeneratedFile', '_SetListener', '__class__', '__deepcopy__', '__delattr__', '__dir__', '__doc__', '__eq__', '__format__', '__ge__', '__getattribute__', '__getstate__', '__gt__', '__hash__', '__init__', '__init_subclass__', '__le__', '__lt__', '__module__', '__ne__', '__new__', '__reduce__', '__reduce_ex__', '__repr__', '__setattr__', '__setstate__', '__sizeof__', '__slots__', '__str__', '__subclasshook__', '__unicode__', '_extensions_by_name', '_extensions_by_number', 'channels']
