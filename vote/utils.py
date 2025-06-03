from hashlib import sha256
from typing import List, Union


def sha256d(string: Union[str, bytes]) -> str:
    """双重SHA256哈希计算
    
    Args:
        string: 输入字符串或字节
        
    Returns:
        64字符的十六进制哈希字符串
        
    Raises:
        ValueError: 如果输入为空
    """
    if not string:
        raise ValueError("Input cannot be empty")
    if not isinstance(string, bytes):
        string = string.encode()
    return sha256(sha256(string).digest()).hexdigest()


def calc_merkle_root(data: List[str]) -> str:
    """计算默克尔根
    
    Args:
        data: 交易哈希列表，每个元素应为64字符的十六进制字符串
        
    Returns:
        默克尔根哈希值(64字符十六进制字符串)
        
    Raises:
        ValueError: 如果输入列表为空或包含非字符串元素
    """
    if not data:
        raise ValueError("Transaction list cannot be empty")
    if not all(isinstance(tx, str) for tx in data):
        raise ValueError("All transactions must be strings")
        
    calc_txs = data.copy()  # 避免修改原始数据
    if len(calc_txs) == 1:
        return calc_txs[0]
        
    while len(calc_txs) > 1:
        if len(calc_txs) % 2 == 1:
            calc_txs.append(calc_txs[-1])
            
        sub_hash_roots = []
        for i in range(0, len(calc_txs), 2):
            join_str = "".join(calc_txs[i:i + 2])
            sub_hash_roots.append(sha256(join_str.encode()).hexdigest())
            
        calc_txs = sub_hash_roots
        
    return calc_txs[0]
