import rpc_pb2 as ln
import math

import lnrpc_helper


#these values can be adjusted
capacity_pct_lower_target_100=30
capacity_pct_upper_target_100=65
#max_fee=0.0001
max_fee=0.001000
min_fee=0.000000
set_fees_on_channels_initiated_by_others=False #False=more polite, True=better balanced channels
set_max_fee_based_on_commit_fee=True #False=hard coded max fee, True=base max fee on commit fee
print_fee_range=True #False=do nothing, True=output fee range (for troubleshooting)
dry_run=False #False=will change fee rate, True=prints ideal fees but does not actually change fees, 

#init
target_capacity_range_100 = capacity_pct_upper_target_100 - capacity_pct_lower_target_100
stub = lnrpc_helper.get_lightning_stub()


#value range checks
if(target_capacity_range_100 < 0):
    print('capacity range cannot be less than 0')
    exit()

if(max_fee > 0.005):
    print('max fee is too high, you crazy?')
    exit()

if(min_fee < 0.000001 and min_fee != 0):
    print('min fee is too low, min fee 0.000001 (or 0.000000) is hard-coded in LND')
    exit()


def getFeeFromFeeJson(fee_response, channel_endpoint):   
    for channel_fees in fee_response.channel_fees:
        if(channel_endpoint == channel_fees.chan_point): 
            return channel_fees.fee_rate

def getCurrentNodePubKey():
    request_getinfo = ln.GetInfoRequest()
    response_getinfo = stub.GetInfo(request_getinfo)
    return response_getinfo.identity_pubkey

def getActiveChannelList():
    channel_request = ln.ListChannelsRequest(
        active_only=True,
        inactive_only=False,
        public_only=False,
        private_only=False,
    )
    return stub.ListChannels(channel_request)

def getNodeInfo(chan):
    request_chaninfo = ln.ChanInfoRequest(
        chan_id=chan.chan_id,
    )
    return stub.GetChanInfo(request_chaninfo)

def calcFeeFromCapacity(local_balance_pct_100, max_fee_to_use):
    if(local_balance_pct_100 < capacity_pct_lower_target_100):
        target_fee = max_fee_to_use
    elif(local_balance_pct_100 > capacity_pct_upper_target_100):
        target_fee = min_fee
    else:
        #this equation is meant to start at low fees and go higher the lower the local channel capacity is. The sine curve is used to ease into fees at the lower ranges and increase fees using a higher delta in the middle ranges of local capacity.
        target_fee = max_fee_to_use*(1- (math.sin( math.pi*((local_balance_pct_100-capacity_pct_lower_target_100)/(target_capacity_range_100*2))))) 
        
    target_fee = round(target_fee,6)
    
    if(target_fee < min_fee):
        target_fee = min_fee

    if(target_fee > max_fee_to_use):
        target_fee = max_fee_to_use
        
    return target_fee

def getMaxFee(is_i_created_channel, commit_fee):
    if(set_max_fee_based_on_commit_fee):
        if(is_i_created_channel):
            my_commit_fee = commit_fee
        else:
            my_commit_fee = 0
        max_fee_to_use = my_commit_fee * 0.5 * 0.05 * 0.000001
        #0.5 - can likely negotiate half fee
        #0.05 - assume transactions of at least 20x the total channel capacity will be paying fee
        #0.000001 - to get the correct fee rate
        
        max_fee_to_use = round(max_fee_to_use,6)
        if(max_fee_to_use < min_fee):
            max_fee_to_use = min_fee
        if(max_fee_to_use > max_fee):
            max_fee_to_use = max_fee
    else:
        max_fee_to_use = max_fee
    return max_fee_to_use

def main(): 

    #GET CURRENT NODE INFO
    #request_getinfo = ln.GetInfoRequest()
    #response_getinfo = stub.GetInfo(request_getinfo)
    #current_node_pub_key = response_getinfo.identity_pubkey
    current_node_pub_key = getCurrentNodePubKey()


    #GET CHANNEL LIST
    #channel_request = ln.ListChannelsRequest(
        #active_only=False,
        #inactive_only=False,
        #public_only=False,
        #private_only=False,
    #)
    #channels_response = stub.ListChannels(channel_request)
    channels_response = getActiveChannelList()

    #get fee report
    feereport_request = ln.FeeReportRequest()
    feereport_response = stub.FeeReport(feereport_request)

    #each channel
    for chan in channels_response.channels:
        #get channel details    
        request_nodeinfo = ln.NodeInfoRequest(
            pub_key=chan.remote_pubkey,
        )
        response_nodeinfo = stub.GetNodeInfo(request_nodeinfo)
        node_alias = response_nodeinfo.node.alias
    
        if(not chan.active):
            continue
        
        if(not set_fees_on_channels_initiated_by_others):
            if(not chan.initiator):
                continue #don't set fee on a channel someone else opened, unless configured to do so
        
        local_balance_pct = (chan.local_balance/chan.capacity)
        local_balance_pct_100 = math.floor(local_balance_pct*100)


        max_fee_to_use = getMaxFee(chan.initiator, chan.commit_fee)

        
        
        #fee calc
        target_fee = calcFeeFromCapacity(local_balance_pct_100, max_fee_to_use)

        current_fee = getFeeFromFeeJson(feereport_response, chan.channel_point)

        if(current_fee != target_fee):
            update_fee = True
        else:
            update_fee = False
        
        print('%32s' % node_alias, chan.chan_id, chan.remote_pubkey, 'local capacity pct: ', round(local_balance_pct,4), 'current fee:', '%f' % current_fee, 'target fee:', '%f' % target_fee, 'updating_fee:', update_fee, 'maxfee:', '%f' % max_fee_to_use)
    
        if(update_fee):
            chan_point = ln.ChannelPoint()
            chan_point_elems = chan.channel_point.split(':')
            chan_point.funding_txid_str = chan_point_elems[0]
            chan_point.output_index = int(chan_point_elems[1])

            #GET NODE INFO
            #request_chaninfo = ln.ChanInfoRequest(
                #chan_id=chan.chan_id,
            #)
            #response_chaninfo = stub.GetChanInfo(request_chaninfo)
            response_chaninfo = getNodeInfo(chan)

            if(response_chaninfo.node1_pub == current_node_pub_key):
                node = response_chaninfo.node1_policy
            if(response_chaninfo.node2_pub == current_node_pub_key):
                node = response_chaninfo.node2_policy

            #STUB
            #print(node)

            current_time_lock_delta = node.time_lock_delta
            current_fee_base_msat = node.fee_base_msat

            #UPDATE CHANNEL POLICY    
            if(not dry_run):
                request_policy_update_request = ln.PolicyUpdateRequest(
                    chan_point=chan_point,
                    base_fee_msat=current_fee_base_msat, 
                    fee_rate=target_fee,
                    time_lock_delta=current_time_lock_delta,
                )
                
                try:
                    response_policy_update_request = stub.UpdateChannelPolicy(request_policy_update_request)
                    print('fees updated')
                except Exception as e:
                    print(e)
                    


#print fee range, used for informational purposes or debugging only
if(print_fee_range):
    fee_increments = 4000
    
    #print headers
    print('')
    print('capacity',' target fee rate')
    print('--------',' ------------------------------------------------------------------------------------------------------------------------')
    print('   ', end="", flush=True)
    for commit_fee_multiplier in range(0,10):
        commit_fee_to_check = commit_fee_multiplier * fee_increments
        print('%12s' % commit_fee_to_check, end="", flush=True)

    print('')

    #loop through capacity percent from 0 to 100
    for cap in range(0,100):
        print('%3s' % cap,'  ',end="", flush=True)
 
        #loop through commit fees
        #since our target_fee is based on the commit fee, check the value using different commit fees (which vary based on base chain fees)
        for commit_fee_multiplier in range(0,10) :
            commit_fee_to_check = getMaxFee(True,commit_fee_multiplier * fee_increments)
            print('%12f' % calcFeeFromCapacity(cap,commit_fee_to_check),end="", flush=True)
        print('')
    
main()




    
