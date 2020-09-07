import codecs, grpc, os
import rpc_pb2 as ln, rpc_pb2_grpc as lnrpc




#this will vary depending on install location, by default is probably something like '~/.lnd/'
LND_DIR='/srv/lnd_data/'


def get_lightning_stub():
    os.environ['GRPC_SSL_CIPHER_SUITES'] = 'HIGH+ECDSA'
    cert = open(LND_DIR+'tls.cert', 'rb').read()
    ssl_creds = grpc.ssl_channel_credentials(cert)

    auth_creds = grpc.metadata_call_credentials(metadata_callback)

    combined_creds = grpc.composite_channel_credentials(ssl_creds, auth_creds)
    channel = grpc.secure_channel('localhost:10009', combined_creds)
    stub = lnrpc.LightningStub(channel)

    return stub


def metadata_callback(context, callback):
    #for more info see grpc docs
    macaroon = codecs.encode(open(LND_DIR+'data/chain/bitcoin/mainnet/admin.macaroon', 'rb').read(), 'hex')
    callback([('macaroon', macaroon)], None)

 
