import ecdsa
import random
import hashlib
import base58


# 开发生成加密“种子”的功能
def create_seed():
    """
    创建密钥对应的种子
    :return:
    """
    return ''.join(random.sample('abcdefghijklmnopqrstuvwxyz!@#$%^&*()', 32)).encode()


# 基于种子，开发创建私钥的功能
def create_private_key(seed):
    """
    使用种子创建私钥
    :param seed: 生成私钥时需要的种子
    :return:
    """
    return ecdsa.SigningKey.from_string(seed, curve=ecdsa.SECP256k1).to_pem()


# 基于私钥，开发创建公钥的功能
def create_public_key(private_key):
    """
    使用私钥生成公钥
    :param private_key: 生成公钥时需要的私钥
    :return:
    """
    return ecdsa.SigningKey.from_pem(private_key).verifying_key.to_pem()


# 基于公钥，开发创建地址的功能
def create_account():
    """
    生成账户
    地址生成的具体过程如下：
    1. 利用SHA-256将公钥进行哈希计算生成哈希值。
    2. 将第1步中的哈希值通过RIPEMD-160、连续两次的SHA-256的哈希计算后生成新的哈希值。
    3. 将第2步中的哈希值的前4位与第1步中生成的哈希值进行Base58编码
    :return:
    """
    new_seed = create_seed()
    private_key_pem = create_private_key(new_seed)
    public_key_pem = create_public_key(private_key_pem)
    in_public_key = ecdsa.VerifyingKey.from_pem(public_key_pem).to_string()

    intermediate = hashlib.sha256(in_public_key).digest()
    ripemd160 = hashlib.new('ripemd160')
    ripemd160.update(intermediate)
    hash160 = ripemd160.digest()

    double_hash = hashlib.sha256(hashlib.sha256(hash160).digest()).digest()
    checksum = double_hash[:4]
    pre_address = hash160 + checksum
    address = base58.b58encode(pre_address)
    print(f'生成地址是: {address.decode()}')
    return {
        'address': address.decode(),
        'private_key': private_key_pem.decode(),
        'public_key': public_key_pem.decode()
    }


# 开发数据签名功能
def data_sign(data, password):
    """
    使用密码哈希进行签名
    :param data: 要签名的数据
    :param password: 用户密码
    :return: 签名哈希
    """
    if not isinstance(data, bytes):
        data = data.encode()
    
    password = password.strip()
    if not password:
        raise ValueError("密码不能为空")
    
    # 使用密码和数据的组合生成哈希
    combined = data + password.encode()
    return hashlib.sha256(combined).digest()


# 开发数据签名验证功能
def generate_id():
    """
    生成唯一ID
    :return: 返回32字节的十六进制字符串
    """
    return hashlib.sha256(str(random.getrandbits(256)).encode()).hexdigest()

def data_verify(data, sig, public_key):
    """
    验签
    :param data: 验签时使用的数据
    :param sig: 验签时使用的签名
    :param public_key: 验签时使用的公钥
    :return: 验签的结果
    """
    if not isinstance(data, bytes):
        data = data.encode()
    vk = ecdsa.VerifyingKey.from_pem(public_key)
    try:
        if vk.verify(sig, data):
            return 0  # 如果验签成功则返回0
        else:
            return 1  # 如果验签失败则返回1
    except Exception as e:
        print(e)
        return 2  # 如果验签出现问题则返回2
