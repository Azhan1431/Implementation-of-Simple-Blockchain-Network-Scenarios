from flask import Flask, request, jsonify, render_template
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
from crypto_util import sha256d

# 创建节点相对应的实体
network = entity.network  # 获取区块链网络内容，根据实际节点情况切换
c_peer = entity.peer0  # 取出当前进程的节点内容，根据实际情况切换
http_port = 5000  # 定义HTTP端口

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

@peer_socketio.on('connect')
def handle_connect():
    print('Client connected')

@peer_socketio.on('disconnect')
def handle_disconnect():
    print('Client disconnected')

def broadcast_new_transaction(tx):
    peer_socketio.emit('new_transaction', tx.to_json())

def broadcast_new_block(block):
    peer_socketio.emit('new_block', block.to_json())


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
        broadcast_new_transaction(tx)
    
    new_block = pow_services.exe_pow(data=c_peer.pool, peer=c_peer)
    if new_block:
        broadcast_new_block(new_block)
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
    broadcast_new_transaction(new_transaction)
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


@app.route('/chain', methods=['GET'])
def get_chain():
    """
    获取整个区块链
    """
    return jsonify({
        'code': 200,
        'data': [block.to_json() for block in c_peer.blockchain.chain]
    })

@app.route('/transaction/<txid>', methods=['GET'])
def get_transaction(txid):
    """
    根据交易ID查询交易
    """
    for block in c_peer.blockchain.chain:
        for tx in block.data:
            if tx.id == txid:
                return jsonify({
                    'code': 200,
                    'data': tx.to_json()
                })
    return jsonify({
        'code': 404,
        'message': 'Transaction not found'
    })

@app.route('/')
def index():
    """
    区块链浏览器首页
    """
    return render_template('index.html')

@app.route('/peers', methods=['GET'])
def get_peers():
    """
    获取所有节点信息(包含状态和区块高度)
    """
    current_height = len(c_peer.blockchain.chain)
    return jsonify({
        'code': 200,
        'data': [{
            'name': peer.name,
            'host': peer.host,
            'port': peer.port,
            'height': len(peer.blockchain.chain),
            'status': 'syncing' if len(peer.blockchain.chain) < current_height else 
                     'outdated' if len(peer.blockchain.chain) > current_height else
                     'normal'
        } for peer in network.peers]
    })

@app.route('/network_graph', methods=['GET'])
def get_network_graph():
    """
    获取网络拓扑图数据
    """
    try:
        nodes = [{
            'id': peer.name,
            'name': peer.name,
            'host': peer.host,
            'port': str(peer.port)  # 确保端口是字符串
        } for peer in network.peers]
        
        edges = []
        if hasattr(network, 'G') and network.G.edges():
            for edge in network.G.edges():
                try:
                    # 确保edge是包含两个节点的元组
                    if isinstance(edge, tuple) and len(edge) == 2:
                        source = edge[0].name if hasattr(edge[0], 'name') else str(edge[0])
                        target = edge[1].name if hasattr(edge[1], 'name') else str(edge[1])
                        edges.append({
                            'source': source,
                            'target': target
                        })
                except Exception as e:
                    print(f"处理边数据出错: {e}")
                    continue
        
        return jsonify({
            'code': 200,
            'data': {
                'nodes': nodes,
                'links': edges
            }
        })
    except Exception as e:
        return jsonify({
            'code': 500,
            'message': str(e)
        })

@app.route('/health', methods=['GET'])
def get_health():
    """
    获取节点健康状态
    """
    return jsonify({
        'code': 200,
        'data': {
            'status': 'running',
            'block_height': len(c_peer.blockchain.chain),
            'pool_size': len(c_peer.pool),
            'peers_count': len(network.peers),
            'last_block_hash': c_peer.blockchain.chain[-1].block_hash if c_peer.blockchain.chain else None
        }
    })

@app.route('/peer_health', methods=['GET'])
def get_peer_health():
    """
    获取指定节点的健康状态
    """
    name = request.args.get('name')
    peer = next((p for p in network.peers if p.name == name), None)
    if not peer:
        return jsonify({
            'code': 404,
            'message': 'Peer not found'
        })
    
    return jsonify({
        'code': 200,
        'data': {
            'status': 'running',
            'block_height': len(peer.blockchain.chain),
            'pool_size': len(peer.pool),
            'last_block_hash': peer.blockchain.chain[-1].block_hash if peer.blockchain.chain else None
        }
    })

@app.route('/peer_chain', methods=['GET'])
def get_peer_chain():
    """
    获取指定节点的区块链数据
    """
    name = request.args.get('name')
    peer = next((p for p in network.peers if p.name == name), None)
    if not peer:
        return jsonify({
            'code': 404,
            'message': 'Peer not found'
        })
    
    return jsonify({
        'code': 200,
        'data': [block.to_json() for block in peer.blockchain.chain]
    })

@app.route('/upload_work', methods=['POST'])
def upload_work():
    """
    上传作品并生成版权登记交易
    """
    try:
        print("Received upload request with content type:", request.content_type)
        
        # 获取上传数据
        if 'file' in request.files:
            print("Processing file upload")
            file = request.files['file']
            if file.filename == '':
                return jsonify({
                    'code': 400,
                    'message': 'No selected file'
                }), 400
            work_content = file.read()
            work_type = file.content_type
            print("Form data:", request.form)
            author = request.form.get('author', '')
            description = request.form.get('description', '')
            private_key = request.form.get('private_key', '')
            print(f"Got file upload: type={work_type}, author={author}, desc={description}")
        elif request.is_json:
            print("Processing JSON upload")
            data = request.get_json()
            if 'text' not in data:
                return jsonify({
                    'code': 400,
                    'message': 'No text content provided'
                }), 400
            work_content = data['text'].encode()
            work_type = 'text/plain'
            author = data.get('author', '')
            description = data.get('description', '')
            private_key = data.get('private_key', '')
            print(f"Got text upload: author={author}, desc={description}")
        else:
            print("Invalid request format")
            return jsonify({
                'code': 400,
                'message': 'No file or text content provided'
            }), 400

        # 计算作品哈希
        work_hash = sha256d(work_content)
        
        # 获取合约参数
        license_type = request.form.get('license_type', 'none')
        allowed_users = request.form.get('allowed_users', '').split(',') if license_type == 'restricted' else []
        revenue_split = {
            'author': float(request.form.get('author_share', 0.7)),
            'platform': float(request.form.get('platform_share', 0.3))
        }

        # 创建版权交易
        tx = models.Transaction(
            sender='0'*32,  # 版权登记特殊交易，发送方为0
            recipient='0'*32,
            data=f"Copyright registration for {work_hash}",
            timestamp=datetime.now(),
            work_hash=work_hash,
            author=author,
            work_type=work_type,
            description=description,
            license_type=license_type,
            allowed_users=allowed_users,
            revenue_split=revenue_split
        )
        tx.gen_id()
        if private_key:
            tx.gen_sig(private_key)
        
        # 添加到交易池并广播
        c_peer.pool.append(tx)
        broadcast_new_transaction(tx)
        
        return jsonify({
            'code': 200,
            'data': {
                'tx_id': tx.id,
                'work_hash': work_hash,
                'timestamp': tx.timestamp.strftime('%Y/%m/%d %H:%M:%S')
            }
        })
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'code': 500,
            'message': str(e),
            'trace': traceback.format_exc()
        }), 500

@app.route('/query_work', methods=['GET'])
def query_work():
    """
    查询版权登记信息并验证使用权限
    """
    work_hash = request.args.get('work_hash')
    author = request.args.get('author')
    requester = request.args.get('requester')  # 请求者地址
    
    if not work_hash and not author:
        return jsonify({
            'code': 400,
            'message': 'Must provide work_hash or author'
        })
    
    results = []
    for block in c_peer.blockchain.chain:
        for tx in block.data:
            if hasattr(tx, 'work_hash') and ((work_hash and tx.work_hash == work_hash) or 
                                           (author and tx.author == author)):
                # 添加授权验证信息
                tx_data = tx.to_json()
                if requester:
                    if tx.license_type == 'free':
                        tx_data['allowed'] = True
                        tx_data['reason'] = 'Free license'
                    elif tx.license_type == 'restricted':
                        tx_data['allowed'] = requester in tx.allowed_users
                        tx_data['reason'] = 'Allowed' if tx_data['allowed'] else 'Not in allowed users list'
                    else:
                        tx_data['allowed'] = False
                        tx_data['reason'] = 'No license granted'
                
                # 添加收益分成信息
                tx_data['revenue_split'] = tx.revenue_split
                
                results.append(tx_data)
    
    return jsonify({
        'code': 200,
        'data': results
    })

if __name__ == '__main__':
    print(f'{"*" * 20}Starting peer0!{"*" * 20}')
    scheduler.start()
    peer_socketio.run(app, host='0.0.0.0', port=http_port, debug=False,allow_unsafe_werkzeug=True)
