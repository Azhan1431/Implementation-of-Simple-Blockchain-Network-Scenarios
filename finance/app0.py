from flask import Flask, request, jsonify
import flask_socketio
import p2p_services
import pow_services
import models
import entity
from flask_apscheduler import APScheduler  
from datetime import datetime
import config
import crypto_util
import http_res

# 创建节点相对应的实体
network = entity.network  # 获取区块链网络内容，根据实际节点情况切换
c_peer = entity.peer0  # 取出当前进程的节点内容，根据实际情况切换
http_port = 5000  # 定义HTTP端口

# 创建HTTP接口
app = Flask(__name__)
from flask_cors import CORS
CORS(app)
# 创建定时器
scheduler = APScheduler()


class Config(object):
    SCHEDULER_API_ENABLED = True


app.config.from_object(Config())
scheduler.init_app(app)
# 创建Socket服务端处理内容
peer_socketio = flask_socketio.SocketIO(app, cors_allowed_origins='*')


# 开发Socket客户端与服务端功能
# 定时启动Socket客户端，向邻近节点发送请求
@scheduler.task('interval',
                id='send_message',
                seconds=config.version_req_interval_seconds,
                misfire_grace_time=900)
def send_message():
    p2p_services.send_version(c_peer, network)


@peer_socketio.on('peer-version')
def peer_version(rec_msg):
    p2p_services.peer_version_services(rec_msg, c_peer, c_peer.sio)


@peer_socketio.on('peer-message')
def peer_message(msg_dict):
    p2p_services.peer_message_service(msg_dict, c_peer)


# 启动PoW算法定时器
@scheduler.task('interval',
                id='peer-calc',
                seconds=config.pow_interval_seconds,
                misfire_grace_time=900)
def peer_exe_pow():
    # 如果交易池中没有消息，就加一条模拟消息
    if len(c_peer.pool) == 0:
        tx_content = datetime.strftime(datetime.now(), '%Y-%m-%d %H:%M:%S')
        tx = models.Transaction('0' * 32, '0' * 32, f'交易内容为: {tx_content}',
                                datetime.now())
        tx.gen_id()
        tx.gen_sig(entity.d_pk)
        c_peer.pool.append(tx)
    pow_services.exe_pow(data=c_peer.pool, peer=c_peer)
    c_peer.pool = []


# 开发HTTP接口服务并启动程序
@app.route('/account_create', methods=['GET'])
def account_create():
    """
    创建账户接口
    :return:
    """
    return jsonify({
        'code': 200,
        'data': crypto_util.create_account()
    })


@app.route('/add_transaction', methods=['POST'])
def add_transaction():
    """
    新增一笔交易
    请求体格式:
    {
        "sender": "发送方地址",
        "recipient": "接收方地址", 
        "data": "交易数据/金额",
        "private_key": "发送方私钥"
    }
    :return:
    """
    body = request.json
    if not all(key in body for key in ['sender', 'recipient', 'data', 'private_key']):
        return jsonify({
            'code': 400,
            'message': '缺少必要参数'
        })

    try:
        # 创建交易对象
        tx = models.Transaction(
            sender=body['sender'],
            recipient=body['recipient'],
            data=body['data'],
            timestamp=datetime.now()
        )
        
        # 生成交易ID和签名
        tx.gen_id()
        tx.gen_sig(body['private_key'])
        
        # 验证签名
        if crypto_util.data_verify(tx.id, tx.sig, tx.sender) != 0:
            return jsonify({
                'code': 401,
                'message': '交易签名验证失败'
            })
            
        # 加入交易池
        c_peer.pool.append(tx)
        
        return jsonify({
            'code': 200,
            'message': '交易已加入交易池',
            'tx_id': tx.id,
            'data': tx.to_json()
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': f'交易处理失败: {str(e)}'
        })


@app.route('/get_pool', methods=['GET'])
def get_pool():
    """
    获取交易池中的消息
    :return:
    """
    return jsonify({
        'code': 200,
        'data': [tx.to_json() for tx in c_peer.pool]
    })


@app.route('/peer_block_query', methods=['GET'])
def peer_block_query():
    """
    获取所有节点及其记录区块的索引值
    :return:
    """
    return c_peer.blockchain.peer_block


@app.route('/block_query', methods=['GET'])
def block_query():
    """
    查询指定区块索引值（高度）接口
    :return:
    """
    index = request.args['id']
    return c_peer.blockchain.query_block_info(int(index))


if __name__ == '__main__':
    print(f'{"*" * 20}Starting peer0!{"*" * 20}')
    scheduler.start()
    peer_socketio.run(app, host='0.0.0.0', port=http_port, debug=False,allow_unsafe_werkzeug=True)
