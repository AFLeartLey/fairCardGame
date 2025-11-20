"""
Host-Client 混合网络层
- 第一个“创建房间”的进程 = Host（监听服务器）
- 其余进程 = Client，输入 IP 连入
- 所有消息 JSON，自动心跳 & 断线回调
"""
import socket
import threading
import time
import queue
from .utils import pack, unpack

class NetError(Exception):
    """网络相关异常"""

# ------------------------------------------------------------------
class Network:
    """
    通用接口：同一类既可当 Host 也可当 Client
    关键回调：
        on_message(msg_dict)  -> 收到任意数据包
        on_disconnect()       -> 对方断线（Client）或最后一个客户端退出（Host）
    """

    def __init__(self, is_host: bool = False,
                 host_ip: str = '0.0.0.0', port: int = 5555):
        self.is_host = is_host
        self.host_ip, self.port = host_ip, port

        # socket & 线程
        self._main_sock   = None          # Host 监听 / Client 单连接
        self._peers       = []            # Host 保存所有客户端 socket
        self._running     = False
        self._recv_thread = None

        # 回调（由逻辑层注入）
        self.on_message   = None
        self.on_disconnect = None

        # 心跳：每 2s 广播一次 ping，超时 6s 判掉
        self._last_seen   = {}            # sock -> timestamp
        self._hb_interval = 2
        self._hb_timeout  = 6
        self._hb_thread   = None

    # ==============================================================
    # 公有 API —— 仅这些函数供外部调用
    # ==============================================================
    def start(self) -> None:
        """启动网络（Host 开始监听 / Client 开始连接）"""
        if self.is_host:
            self._start_host()
        else:
            raise NetError('Client 请使用 connect() 而非 start()')

    def connect(self, target_ip: str = '127.0.0.1') -> None:
        """Client 主动连接服务器"""
        if self.is_host:
            raise NetError('Host 不能 connect()')
        self.host_ip = target_ip
        self._start_client()

    def send(self, data: dict) -> None:
        """发送字典（Host=广播，Client=单发）"""
        raw = pack(data)
        if self.is_host:
            for s in self._peers[:]:
                try:
                    s.sendall(raw)
                except Exception:
                    self._remove_peer(s)
        else:
            if self._main_sock:
                self._main_sock.sendall(raw)

    def close(self) -> None:
        """关闭所有连接并结束线程"""
        self._running = False
        for s in [self._main_sock] + self._peers:
            if s:
                try:
                    s.close()
                except Exception:
                    pass
        self._peers.clear()
        if self._recv_thread and self._recv_thread.is_alive():
            self._recv_thread.join(timeout=0.5)
        if self._hb_thread and self._hb_thread.is_alive():
            self._hb_thread.join(timeout=0.5)

    # ==============================================================
    # 私有实现
    # ==============================================================
    def _start_host(self):
        self._running = True
        self._main_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._main_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._main_sock.bind((self.host_ip, self.port))
        self._main_sock.listen(5)
        # 接受线程
        thr = threading.Thread(target=self._accept_loop, daemon=True)
        thr.start()
        # 心跳线程
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._hb_thread.start()

    def _start_client(self):
        self._running = True
        self._main_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._main_sock.settimeout(10)
        try:
            self._main_sock.connect((self.host_ip, self.port))
        except Exception as e:
            raise NetError(f'连接失败：{e}') from e
        self._main_sock.settimeout(None)
        self._recv_thread = threading.Thread(target=self._recv_loop,
                                             args=(self._main_sock, True),
                                             daemon=True)
        self._recv_thread.start()
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._hb_thread.start()

    # -------- Host 专用 --------
    def _accept_loop(self):
        while self._running:
            try:
                conn, addr = self._main_sock.accept()
                self._peers.append(conn)
                self._last_seen[conn] = time.time()
                threading.Thread(target=self._recv_loop, args=(conn, False), daemon=True).start()
            except Exception:
                pass

    def _remove_peer(self, sock):
        if sock in self._peers:
            self._peers.remove(sock)
        self._last_seen.pop(sock, None)
        sock.close()
        if self.is_host and not self._peers and self.on_disconnect:
            self.on_disconnect()

    # -------- 收发 & 心跳 --------
    def _recv_loop(self, sock: socket.socket, is_client_me: bool):
        buffer = ''
        while self._running:
            try:
                data = sock.recv(4096).decode('utf-8')
                if not data:
                    break
                buffer += data
                while '\n' in buffer:
                    line, buffer = buffer.split('\n', 1)
                    msg = unpack(line)
                    # 心跳包内部消化
                    if msg.get('type') == 'ping':
                        self._last_seen[sock] = time.time()
                        continue
                    if msg.get('type') == 'pong':
                        self._last_seen[sock] = time.time()
                        continue
                    # 业务包抛给逻辑层
                    if self.on_message:
                        self.on_message(msg)
            except Exception:
                break
        # 对端断开
        if is_client_me:
            self._running = False
            if self.on_disconnect:
                self.on_disconnect()
        else:
            self._remove_peer(sock)

    def _heartbeat_loop(self):
        while self._running:
            time.sleep(self._hb_interval)
            now = time.time()
            # 发送 ping / 检查超时
            if self.is_host:
                self.send({'type': 'ping'})
                for s in self._peers[:]:
                    if now - self._last_seen.get(s, 0) > self._hb_timeout:
                        self._remove_peer(s)
            else:
                self.send({'type': 'pong'})
                if now - self._last_seen.get(self._main_sock, 0) > self._hb_timeout:
                    self.close()
                    if self.on_disconnect:
                        self.on_disconnect()
                    break
            self._last_seen[self._main_sock if not self.is_host else self._main_sock] = now