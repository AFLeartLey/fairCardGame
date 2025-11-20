"""序列化 / 协议辅助"""
import json

def pack(data: dict) -> bytes:
    """字典 → 字节流（带 \n 分隔符）"""
    return (json.dumps(data, ensure_ascii=False) + '\n').encode('utf-8')

def unpack(raw: str) -> dict:
    """字节流 → 字典"""
    return json.loads(raw)