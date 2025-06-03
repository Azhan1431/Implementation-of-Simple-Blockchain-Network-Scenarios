from pydantic_settings import BaseSettings

class Config(BaseSettings):
    POW_INTERVAL: int = 20  # PoW算法执行间隔(秒)
    VERSION_REQ_INTERVAL: int = 20  # 版本请求间隔(秒)
    
    class Config:
        env_prefix = "BLOCKCHAIN_"

config = Config()
