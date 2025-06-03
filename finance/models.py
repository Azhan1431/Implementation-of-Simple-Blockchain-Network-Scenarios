import networkx as nx
import matplotlib.pyplot as plt
import socketio
from datetime import datetime
import hashlib
from utils import sha256d
import binascii
from crypto_util import data_sign
import ecdsa
import random


# 定义交易对象模型
class Transaction(object):
    def __init__(self, sender, recipient, data, timestamp, id='', sig=''):
        """
        交易的初始化
        :param sender: 发送方的地址
        :param recipient: 接收方的地址
        :param data: 交易的内容
        :param timestamp: 交易的时间戳
        :param private_key: 发送方的私钥
        """
        self.sender = sender
        self.recipient = recipient
        self.data = data
        self.timestamp = timestamp
        self.id = id
        self.sig = sig

    # 生成交易的哈希值
    def gen_id(self):
        self.id = sha256d(self.to_string())

    # 生成签名
    def gen_sig(self, private_key):
        self.sig = data_sign(self.id, private_key)

    def to_string(self):
        """
        将交易元素拼接为一个字符串
        :return:
        """
        return f'{self.sender}{self.recipient}{self.data}' \
               f'{self.timestamp.strftime("%Y/%m/%d %H:%M:%S")}'

    def to_json(self):
        """
        将交易元素转换为一个JSON对象
        :return:
        """
        if not isinstance(self.sig, str):
            self.sig = binascii.hexlify(self.sig).decode()
        return {
            'id': self.id,
           'sender': self.sender,
           'recipient': self.recipient,
            'data': self.data,
            'timestamp': self.timestamp.strftime('%Y/%m/%d %H:%M:%S'),
           'sig': self.sig,
        }


# 定义区块对象模型
class Block(object):
    def __init__(self, index, prev_hash, data, timestamp,
                 bits, nonce=0, merkle_root='', block_hash=''):
        """
        区块的初始化方法，在创建一个区块时需传入索引值等相关信息
        :param index: 区块索引值
        :param prev_hash: 父块哈希值
        :param data: 区块中需保存的记录
        :param timestamp: 区块生成的时间戳
        :param difficult_bits: 区块难度
        """
        self.index = index
        self.prev_hash = prev_hash
        self.data = data
        self.timestamp = timestamp
        self.difficult_bits = bits
        self.nonce = nonce
        self.merkle_root = merkle_root
        self.block_hash = block_hash

    # 计算新区块的默克尔根和区块哈希值
    def gen_merkle_root_and_block_hash(self):
        self.merkle_root = self.calc_merkle_root()
        self.block_hash = self.calc_block_hash()

    def to_json(self):
        """
        以JSON格式输出区块内容
        :return:
        """
        return {
            'index': self.index,
            'prev_hash': self.prev_hash,
           'merkle_root': self.merkle_root,
            'data': [item.to_json() for item in self.data],
            'timestamp': self.timestamp.strftime('%Y/%m/%d %H:%M:%S'),
            'bits': hex(self.difficult_bits)[2:].rjust(8, "0"),
            'nonce': hex(self.nonce)[2:].rjust(8, "0"),
            'block_hash': self.block_hash
        }

    def calc_merkle_root(self):
        """
        计算默克尔根
        :return:
        """
        calc_txs = [tx.to_string() for tx in self.data]
        if len(calc_txs) == 1:
            return sha256d(calc_txs[0])
        if len(calc_txs) == 0:
            return
        while len(calc_txs) > 1:
            if len(calc_txs) % 2 == 1:
                calc_txs.append(calc_txs[-1])
            sub_hash_roots = []
            for i in range(0, len(calc_txs), 2):
                join_str = "".join(calc_txs[i:i + 2])
                sub_hash_roots.append(hashlib.sha256(join_str.encode()).hexdigest())
            calc_txs = sub_hash_roots
        return calc_txs[0]

    def calc_block_hash(self):
        """
        生成区块的哈希值
        """
        parse_data = [item.to_json() for item in self.data]
        blockheader = str(self.index) + str(self.prev_hash) \
                      + str(parse_data) + str(self.timestamp) + \
                      hex(self.difficult_bits)[2:] + str(self.nonce) + \
                      self.merkle_root
        h = hashlib.sha256(blockheader.encode()).hexdigest()
        self.block_hash = h
        return h


# 定义区块链网络对象模型
class Network(object):
    def __init__(self, name):
        """
        初始化区块链网络
        :param name:
        """
        self.peers = []  # 网络中的节点
        self.name = name  # 网络名称
        self.G = nx.Graph()  # 网络拓扑

    def add_peer(self, peer):
        """
        在网络中新增节点
        """
        self.peers.append(peer)
        self.G.add_node(peer.name, host=peer.host, port=peer.port)

    def add_edge(self, s_peer, e_peer):
        """
        在网络中新增节点间的边
        """
        e = (s_peer, e_peer)
        self.G.add_edge(*e)

    def del_peer(self, peer_name):
        """
        删除指定名称的节点
        """
        for i, peer in enumerate(self.peers):
            if peer_name == peer.name:
                del self.peers[i]
                self.G.remove_node(peer_name)

    def draw_network(self):
        """
        绘制网络
        """
        pos = nx.spring_layout(self.G, iterations=100)
        nx.draw(self.G, pos, with_labels=True)
        plt.show()


# 定义区块链账本对象模型
DIFFICULT_BITS = 0x1e11ffff  # 定义区块难度


class Blockchain(object):
    def __init__(self, d_pk):
        self.chain = []
        # 用于记录不同节点按索引值顺序获取区块记账权的信息
        self.peer_block = {}
        self.create_genesis_block(d_pk)

    def add_block(self, block):
        self.chain.append(block)

    def add_peer_block(self, name, block_index):
        """
        向peer_block中添加节点的block_index记录
        :param name: 节点名称
        :param block_index: 区块索引值
        """
        if name in self.peer_block:
            self.peer_block[name].append(block_index)
        else:
            self.peer_block[name] = [block_index]

    def query_peer_block(self, name):
        """
        查询peer_block的内容
        :param name: 节点名称
        """
        return self.peer_block[name]

    def query_block_info(self, index=0):
        """
        通过索引值查询区块链中的区块信息
        """
        if index > len(self.chain) - 1:
            return 'block not exists!'
        block_json = self.chain[index].to_json()
        return block_json

    def create_genesis_block(self, d_pk):
        """
        创建创世区块，在其中定义区块难度，之后将被所有的区块沿用
        """
        tx = Transaction('0' * 32, '0' * 32, '第一笔交易', datetime.now())
        tx.gen_id()
        tx.gen_sig(d_pk)
        genesis_block = Block(0,
                              '0' * 64,
                              [tx],
                              datetime.now(),
                              DIFFICULT_BITS)
        genesis_block.gen_merkle_root_and_block_hash()
        self.add_block(genesis_block)


# 定义节点对象模型
class Peer(object):
    def __init__(self, name, host, port, blockchain):
        """
        初始化节点
        :param name: 节点名称
        :param host: 节点的主机IP地址
        :param port: 节点的端口
        """
        self.name = name
        self.host = host
        self.port = port
        self.version = 0  # 节点当前最新消息的版本号
        self.pool = []  # 节点存储消息的交易池
        self.last_block = 1  # 记录前一个区块的索引值
        self.blockchain = blockchain
        self.sio = socketio.Client()  # 创建P2P通信的客户端

    def add_message(self, message):
        """
        向交易池中添加消息
        :param message: 传入的消息对象
        """
        self.pool.append(message)
