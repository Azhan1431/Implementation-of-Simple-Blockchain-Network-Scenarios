from flask import Flask, request, jsonify
import flask_socketio
import p2p_services
import pow_services
import models
import entity
from flask_apscheduler import APScheduler
from datetime import datetime, timedelta
from typing import List
from pydantic import BaseModel
from models import Vote, VoteOption
import config
import crypto_util
import http_res

# 创建节点相对应的实体
network = entity.network  # 获取区块链网络内容，根据实际节点情况切换
c_peer = entity.peer3  # 取出当前进程的节点内容，根据实际情况切换
http_port = 5003  # 定义HTTP端口

# 创建HTTP接口
app = Flask(__name__)
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
                seconds=config.config.VERSION_REQ_INTERVAL,
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
                seconds=config.config.POW_INTERVAL,
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
    :return:
    """
    body = request.json
    if'sender' not in body or'recipient' not in body or 'data' not in body or 'private_key' not in body:
        return jsonify(http_res.empty_res)
    new_transaction = models.Transaction(body['sender'], body['recipient'],
                                         body['data'], datetime.now(), body['private_key'])
    c_peer.pool.append(new_transaction)
    return jsonify(http_res.success_res)


@app.route('/get_pool', methods=['GET'])
def get_pool():
    """
    获取交易池中的消息
    :return:
    """
    return jsonify({
        'code': 200,
        'data': c_peer.pool
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

# 投票相关API
class CreateVoteRequest(BaseModel):
    title: str
    description: str
    options: List[str]
    creator: str
    duration: int  # 投票持续时间(秒)

@app.route('/create_vote', methods=['POST'])
def create_vote():
    """创建新投票"""
    try:
        req = CreateVoteRequest(**request.json)
        vote_options = [VoteOption(
            option_id=crypto_util.generate_id(),
            content=opt
        ) for opt in req.options]
        
        new_vote = Vote(
            vote_id=crypto_util.generate_id(),
            title=req.title,
            description=req.description,
            creator=req.creator,
            start_time=datetime.now(),
            end_time=datetime.now() + timedelta(seconds=req.duration),
            options=vote_options
        )
        network.votes.append(new_vote)
        return jsonify({
            'code': 200,
            'data': new_vote.to_json()
        })
    except Exception as e:
        return jsonify({
            'code': 400,
            'message': str(e)
        }), 400

class CastVoteRequest(BaseModel):
    vote_id: str
    option_id: str 
    voter: str
    private_key: str

@app.route('/cast_vote', methods=['POST'])
def cast_vote():
    """进行投票"""
    try:
        req = CastVoteRequest(**request.json)
        vote_tx = models.Transaction(
            sender=req.voter,
            recipient='0'*32,  # 系统地址
            data=f'Vote for {req.option_id}',
            timestamp=datetime.now(),
            tx_type='vote',
            vote_id=req.vote_id,
            option_id=req.option_id
        )
        vote_tx.gen_id()
        vote_tx.gen_sig(req.private_key)
        c_peer.pool.append(vote_tx)
        return jsonify(http_res.success_res)
    except Exception as e:
        return jsonify({
            'code': 400,
            'message': str(e)
        }), 400

@app.route('/list_votes', methods=['GET'])
def list_votes():
    """获取所有投票列表"""
    return jsonify({
        'code': 200,
        'data': [vote.to_json() for vote in network.votes]
    })

@app.route('/get_vote/<vote_id>', methods=['GET'])
def get_vote(vote_id):
    """获取投票详情"""
    for vote in network.votes:
        if vote.vote_id == vote_id:
            return jsonify({
                'code': 200,
                'data': vote.to_json()
            })
    return jsonify({
        'code': 404,
        'message': 'Vote not found'
    }), 404

if __name__ == '__main__':
    print(f'{"*" * 20}Starting peer0!{"*" * 20}')
    scheduler.start()
    peer_socketio.run(app, host='0.0.0.0', port=http_port, debug=False,allow_unsafe_werkzeug=True)
