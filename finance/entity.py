import p2p_services
import models

# 预置一个私钥，用于创建创世区块
d_pk = """-----BEGIN EC PRIVATE KEY-----\nMHQCAQEEIClncSpsc2Fua3ljeiR2aCNydSFkbxQoQHAleGZlYizqoAcGBSuBBAAK
\noUQDQgAEyTx/sAlhdNUOwcfnCjOVp9fxMF6DUwSLkFqj2E6sDFuPvrKF9wVWH8J3
\nntxWh+kR3GFKcB48v3eTfE1Us5L7Zw==\n-----END EC PRIVATE KEY-----\n"""

# 用于创建节点和网络实体
blockchain = models.Blockchain(d_pk)
peer0 = models.Peer('peer0', 'localhost', 5000, blockchain)
peer1 = models.Peer('peer1', 'localhost', 5001, blockchain)
peer2 = models.Peer('peer2', 'localhost', 5002, blockchain)
peer3 = models.Peer('peer3', 'localhost', 5003, blockchain)
peer4 = models.Peer('peer4', 'localhost', 5004, blockchain)
peer_list = [peer0, peer1, peer2, peer3, peer4]
network = p2p_services.generate_network('test', peer_list)