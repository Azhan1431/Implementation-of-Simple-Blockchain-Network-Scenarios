import models
from datetime import datetime
import random
from flask import jsonify
import http_res


# 开发生成区块链网络的功能
def generate_network(network_name, peer_list):
    """
    生成区块链网络，初始化网络实体，以及在网络实体中加入节点和边
    :param network_name: 网络名称
    :param peer_list: 已生成的节点列表
    :return: 生成的区块链网络实体对象
    """
    g_network = models.Network(network_name)
    for index, peer in enumerate(peer_list):
        g_network.add_peer(peer)
        if index == len(peer_list) - 1:
            # 如果是最后一个节点，就让最后一个节点和第一个节点首尾相连
            g_network.add_edge(peer.name, peer_list[0].name)
        else:
            # 否则，建立本节点与下一个节点的边
            g_network.add_edge(peer.name, peer_list[index + 1].name)
    return g_network


# 开发定时器功能的处理函数
def send_version(peer, network):
    """
    Socket客户端处理函数，随机发送询问最新消息版本的请求
    :param peer: 当前节点
    :param network: 当前区块链网络
    :return:
    """
    print('start to send version!')
    peer_name = peer.name
    neighbours = list(network.G.adj[peer_name])
    rand_index = random.randint(0, len(neighbours) - 1)
    neighbour_peer_name = neighbours[rand_index]
    neighbour_peer = network.G.nodes()[neighbour_peer_name]
    req_url = f'http://{neighbour_peer["host"]}:{neighbour_peer["port"]}'
    res_url = f'http://{peer.host}:{peer.port}'
    print(f'connect to peer {req_url}')
    peer.sio.connect(req_url)
    send_msg = {
       'version': peer.last_block,
        'url': res_url
    }
    peer.sio.emit('peer-version', send_msg)
    peer.sio.disconnect()


# 开发Socket服务端处理函数，接收邻近节点的新区块询问请求，并做出响应
def peer_version_services(rec_msg, c_peer, sio):
    """
    用于接收Socket客户端请求，消息中包含节点版本
    :param rec_msg: 字典，键值对形式，version表示请求节点的最新消息版本，url表示请求节点的URL
    :param c_peer: 当前服务端节点
    :param sio: 当前服务端节点的客户端
    :return:
    """
    version = rec_msg['version']
    url = rec_msg['url']
    print(f'receive message : {version}')
    # 如果请求的消息版本号小于本节点最新消息版本号，则需取出两版本号之间的所有数据
    res_arr = []
    send_msg = {}
    # 如果发送的版本小于当前最新区块，就要获取本地账本最新区块的数据
    if version < c_peer.last_block:
        # 倒序遍历，从列表最后一个元素依次遍历至索引值为0的元素
        for i in range(len(c_peer.blockchain.chain) - 1, -1, -1):
            get_block = c_peer.blockchain.chain[i]
            if version < get_block.index:
                res_arr.insert(0, get_block.to_json())
        # 按固定格式返回消息
        send_msg = {
            'code': 1,  # 1表示存在新消息
            'data': res_arr
        }
    else:
        # 当查询不到数据，则返回空消息
        send_msg = {
            'code': 0,  # 0表示不存在新消息
            'data': 'empty'
        }
    sio.connect(url)
    sio.emit('peer-message', send_msg)
    sio.disconnect()


# 开发Socket服务端处理函数，接收邻近节点发送的新区块，并将其存储至自身的区块链账本中
def peer_message_service(msg_dict, c_peer):
    """
    Socket服务端接收消息，如果code为0表示没有新消息，code为1表示有新消息
    :param msg_dict: 接收消息
    :param c_peer: 当前服务端节点
    :return:
    """
    # msg_dict = json.loads(msg)
    if 'code' not in msg_dict or 'data' not in msg_dict:
        return
    # code ：0表示没有新消息，不做任何操作
    # code ：1表示有新消息，将其加人交易池
    if msg_dict['code'] == 0:
        return
    if msg_dict['code'] == 1:
        for get_block_dict in msg_dict['data']:
            block = parse_dict_to_block(get_block_dict)
            c_peer.blockchain.chain.append(block)
        c_peer.last_block = msg_dict['data'][-1]['index']


# 开发将交易字典转为对象模型的功能
def parse_dict_tx(tx_dict):
    """
    将交易对象从字典转为对象模型
    :param tx_dict: 交易字典
    :return:
    """
    tx = models.Transaction(sender=tx_dict['sender'],
                            recipient=tx_dict['recipient'],
                            data=tx_dict['data'],
                            timestamp=datetime.strptime(tx_dict['timestamp'], '%Y/%m/%d %H:%M:%S'),
                            id=tx_dict['id'],
                            sig=tx_dict['sig'])
    return tx


# 开发将区块字典转为对象模型的功能
def parse_dict_to_block(block_dict):
    """
    将区块对象从字典转为对象模型
    :param block_dict: 区块字典
    :return:
    """
    tx_data = [parse_dict_tx(tx_dict) for tx_dict in block_dict['data']]
    block = models.Block(index=block_dict['index'],
                         prev_hash=block_dict['prev_hash'],
                         data=tx_data,
                         timestamp=datetime.strptime(block_dict['timestamp'], '%Y/%m/%d %H:%M:%S'),
                         bits=int(block_dict['bits'], 16),
                         nonce=int(block_dict['nonce'], 16),
                         merkle_root=block_dict['merkle_root'],
                         block_hash=block_dict['block_hash'])
    return block