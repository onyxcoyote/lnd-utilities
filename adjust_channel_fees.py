import rpc_pb2 as ln
import math

import lnrpc_helper


##these values can be adjusted

#fee range (min fee threshold, max fee threshold)
capacity_pct_lower_target_100=0
capacity_pct_upper_target_100=90

#fee rate
max_fee=0.001250
min_fee=0.000000
set_fees_on_channels_initiated_by_others=False #False=more polite, True=better balanced channels
set_max_fee_based_on_commit_fee=True #False=hard coded max fee, True=base max fee on commit fee

#base fee
update_base_fee=True
#base_fee_msat_value=1
base_fee_msat_value=0

#misc
print_fee_range=True #False=do nothing, True=output fee range (for troubleshooting)
dry_run=False #False=will change fee rate, True=prints ideal fees but does not actually change fees, 

##


#init
target_capacity_range_100 = capacity_pct_upper_target_100 - capacity_pct_lower_target_100
stub = lnrpc_helper.get_lightning_stub()
conf_file_name = "adjust_channel_fees.conf"
multiplier_list = []






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


class MultiplierConfig(object):
    chan_id = ""
    multi_value = 0
    comment = ""
    
    def __init__(self, chan_id, multi_value, comment):
        self.chan_id = int(chan_id)
        self.multi_value = float(multi_value)
        self.comment = comment
        
def make_multiplier_config(line):
    
    chan_id,multi_value,comment = line.split(",")
    chan_id = chan_id.strip()
    multi_value = multi_value.strip()
    comment = comment.strip()
    
    multiplier_obj = MultiplierConfig(chan_id, multi_value, comment)
    
    return multiplier_obj

def load_config():
    
    global multiplier_list
    conf_file = open(conf_file_name, "r") 
    
    for conf_line in conf_file:
        if not conf_line.startswith("#"):
            multiplier_obj = make_multiplier_config(conf_line)
            multiplier_list.append(multiplier_obj)
            
    print("multiplier list")
    for multiplier_obj in multiplier_list:
        print(multiplier_obj.chan_id, multiplier_obj.multi_value)


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

def calcFeeFromCapacity(local_balance_pct_100, max_fee_to_use, multiplier):
    if(local_balance_pct_100 < capacity_pct_lower_target_100):
        target_fee = max_fee_to_use
    elif(local_balance_pct_100 > capacity_pct_upper_target_100):
        target_fee = min_fee
    else:
        #this equation is meant to start at low fees and go higher the lower the local channel capacity is. The sine curve is used to ease into fees at the lower ranges and increase fees using a higher delta in the middle ranges of local capacity.
        target_fee = max_fee_to_use*(1- (math.sin( math.pi*((local_balance_pct_100-capacity_pct_lower_target_100)/(target_capacity_range_100*2))))) 

    target_fee = target_fee*multiplier
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
            
        #assumptions for these values
        #0.33 - can likely negotiate a lower closing fee, maybe 33% of commit_fee
        #0.05 - assume transactions of at least 20x the total channel capacity will be paying fee
        #0.000001 - to get the correct fee rate
        max_fee_to_use = my_commit_fee * 0.33 * 0.05 * 0.000001
        
        max_fee_to_use = round(max_fee_to_use,6)
        if(max_fee_to_use < min_fee):
            max_fee_to_use = min_fee
        if(max_fee_to_use > max_fee):
            max_fee_to_use = max_fee
    else:
        max_fee_to_use = max_fee
    return max_fee_to_use

def main(): 

    
    #GET LOCAL CONFIG SETTINGS, fee multiplier config (to make popular channels more expensive so they don't get exhausted quickly)
    load_config()
    

    #GET CURRENT NODE INFO
    current_node_pub_key = getCurrentNodePubKey()


    #GET CHANNEL LIST
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

        multiplier = 1    
        for multiplier_obj in multiplier_list:
            if(multiplier_obj.chan_id == chan.chan_id):
                multiplier = multiplier_obj.multi_value
        
        #fee calc
        target_fee = calcFeeFromCapacity(local_balance_pct_100, max_fee_to_use, multiplier)

        current_fee = getFeeFromFeeJson(feereport_response, chan.channel_point)

        if(current_fee != target_fee):
            update_fee = True
        else:
            update_fee = False
        
        #GET NODE INFO
        response_chaninfo = getNodeInfo(chan)

        if(response_chaninfo.node1_pub == current_node_pub_key):
            node = response_chaninfo.node1_policy
        if(response_chaninfo.node2_pub == current_node_pub_key):
            node = response_chaninfo.node2_policy

        #STUB
        #print(node)

        current_time_lock_delta = node.time_lock_delta
        current_fee_base_msat = node.fee_base_msat

        #maybe update also based on base fee
        if(not update_fee):
            if(update_base_fee):
                if(current_fee_base_msat != base_fee_msat_value):
                    update_fee = True
            
    
    
        updated=False
        if(update_fee):
            chan_point = ln.ChannelPoint()
            chan_point_elems = chan.channel_point.split(':')
            chan_point.funding_txid_str = chan_point_elems[0]
            chan_point.output_index = int(chan_point_elems[1])

            response_chaninfo = getNodeInfo(chan)

            if(response_chaninfo.node1_pub == current_node_pub_key):
                node = response_chaninfo.node1_policy
            if(response_chaninfo.node2_pub == current_node_pub_key):
                node = response_chaninfo.node2_policy

            current_time_lock_delta = node.time_lock_delta
            current_fee_base_msat = node.fee_base_msat

            if(update_base_fee):
                base_fee_msat_to_set = base_fee_msat_value
            else:
                base_fee_msat_to_set = current_fee_base_msat

            #UPDATE CHANNEL POLICY    
            if(not dry_run):
                request_policy_update_request = ln.PolicyUpdateRequest(
                    chan_point=chan_point,
                    base_fee_msat=base_fee_msat_to_set, 
                    fee_rate=target_fee,
                    time_lock_delta=current_time_lock_delta,
                )
                
                try:
                    response_policy_update_request = stub.UpdateChannelPolicy(request_policy_update_request)
                    updated=True
                except Exception as e:
                    print(e)

        
        print('%35s' % node_alias.encode('ascii','replace'), chan.chan_id, 'local cap%: ', '%4s' % round(local_balance_pct,2), 'commit_fee:', '%7s' % chan.commit_fee, 'oldfee:', '%f' % current_fee, 'target fee:', '%f' % target_fee, 'toUpdate:', '%5s' % update_fee, 'updated:', '%5s' % updated, 'mltyplr:', '%3s' % multiplier, 'basefee:', current_fee_base_msat)
        #other fields: chan.remote_pubkey

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
            print('%12f' % calcFeeFromCapacity(cap,commit_fee_to_check,1),end="", flush=True)
        print('')
    
main()




    
