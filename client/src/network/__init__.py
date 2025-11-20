# 统一导出接口，方便别人“from network import Network, NetError”
from .core import Network, NetError
__all__ = ['Network', 'NetError']