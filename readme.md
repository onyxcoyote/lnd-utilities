

prerequisites
    ============
    
    1)see
      https://dev.lightning.community/guides/python-grpc/
      
    rpc_pb2.py
    put rpc_pb2.py in a python library path and update PYTHONPATH, e.g.
        export PYTHONPATH=${PYTHONPATH}:/srv/lib/python
        
    2) requires python libraries: 
	protobuf, grpcio, grpcio-tools          
    


channel_summary.py

    * purpose:
        * display some information about connected channels. Can also be used to see total node capacity.
    * requires:
        * LND
        * python3
    * run with:
```
python3 channel_summary.py
```
    
    

adjust_channel_fees.py

    * purpose:
        * automatically change channel fees based on: configured settings, current estimated basechain fees, and capacity of the channel (for example: if outgoing capacity is low, increase the fee)
    * requires:
        * LND
        * python3
        * crontab
    * run with:
```
python3 adjust_channel_fees.py
```
or run the same through crontab



get2_lowfee_nodes.py

    * purpose:
        * retrieves a list of lightning nodes based on fee and capacity criteria specified in .py file, and determine distance in terms of number of hops, and capacity. NOTE: THIS CAN BE VERY SLOW
    * requires:
        * LND
        * python3
    * run with:
```
python3 get2_lowfee_nodes.py
```
    

    
    
