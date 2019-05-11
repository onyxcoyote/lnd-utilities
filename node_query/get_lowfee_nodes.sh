#!/bin/bash
lncli describegraph > graph.tmp
python3 get_lowfee_nodes.py > lowfeenodes.tmp
cat lowfeenodes.tmp | sort | uniq -c | sort -nr > lowfeenodes_uniq.tmp
echo "channelcount, pubkey"
cat nofeenodes_uniq.tmp
