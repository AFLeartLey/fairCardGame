# -*- coding: utf-8 -*-
"""
Enhanced Host-Client Hybrid Network Layer – Bidirectional RPC Support
-------------------------------------------------------------------
A single Network class that can act as either
  - Host (listening server that creates the room), or
  - Client (connects to the room).

NEW FEATURES
------------
* Bidirectional RPC: request() / register_handler() style calls
* Asynchronous Future mechanism with timeout & exception propagation
* Directed requests for multi-client hosts (to_socket / request_to_peer)
* Thread-safe, callbacks and RPC handlers coexist
* Compatible with legacy heartbeat, disconnection detection and clean shutdown

Author: <your-name>
"""

from __future__ import annotations

import socket
import threading
import time
import uuid
from typing import Callable, Dict, Any, List, Optional
from concurrent.futures import Future

# --------------------------------------------------------------------------- #
#  Utility layer – replace with your own if needed
# --------------------------------------------------------------------------- #
from .utils import pack, unpack   # noqa: F401


class NetError(Exception):
    """Network-related runtime errors."""


# ============================================================================= #
#  Enhanced Network – with Bidirectional RPC support
# ============================================================================= #
class Network:
    """
    Universal TCP networking layer with RPC.

    Callbacks (set by application):
        on_message(msg: dict) -> None
        on_disconnect() -> None

    RPC:
        register_handler(request_type, handler)
        request(data, timeout=5, to_socket=?) -> dict
    """

    # --------------------------------------------------------------------- #
    #  Construction
    # --------------------------------------------------------------------- #
    def __init__(
        self,
        is_host: bool = False,
        host_ip: str = "0.0.0.0",
        port: int = 5555,
    ) -> None:
        """
        Parameters
        ----------
        is_host : bool
            True  -> this instance will listen for incoming connections
            False -> this instance will connect to a remote host
        host_ip : str
            Local interface to bind (Host only)
        port : int
            TCP port to bind/connect
        """
        self.is_host = is_host
        self.host_ip, self.port = host_ip, port

        # Socket & threading
        self._main_sock: Optional[socket.socket] = None
        self._peers: List[socket.socket] = []      # Host only: connected clients
        self._running = False

        # Callbacks – injected by application
        self.on_message: Optional[Callable[[Dict[str, Any]], None]] = None
        self.on_disconnect: Optional[Callable[[], None]] = None

        # Heart-beating
        self._last_seen: Dict[socket.socket, float] = {}  # sock -> timestamp
        self._hb_interval = 2.0      # seconds
        self._hb_timeout = 6.0       # seconds
        self._hb_thread: Optional[threading.Thread] = None

        # RPC
        self._pending_requests: Dict[str, Future] = {}
        self._request_handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}
        self._rpc_lock = threading.Lock()
        self._default_timeout = 5.0

        self.on_connected: Optional[Callable[[], None]] = None
        self.on_peer_connected: Optional[Callable[[int], None]] = None
        self.on_disconnected: Optional[Callable[[], None]] = None
        self.is_connected = False

        # Client keeps reference to server socket for heartbeat
        self._server_socket: Optional[socket.socket] = None

    # --------------------------------------------------------------------- #
    #  Public API – life-cycle
    # --------------------------------------------------------------------- #
    def start(self) -> None:
        """
        Host ONLY: start listening for incoming connections.

        Raises
        ------
        NetError
            If invoked on a Client instance.
        """
        if not self.is_host:
            raise NetError("Client must use connect(), not start()")
        self._start_host()

    def connect(self, target_ip: str = "127.0.0.1") -> None:
        """
        Client ONLY: connect to a remote host.

        Parameters
        ----------
        target_ip : str
            IPv4 address of the host to connect to.

        Raises
        ------
        NetError
            If invoked on a Host instance or connection fails.
        """
        if self.is_host:
            raise NetError("Host cannot connect()")
        self.host_ip = target_ip
        self._start_client()

    

    def close(self) -> None:
        """
        Idempotent shutdown: close sockets, stop threads, clean resources.
        Safe to call multiple times.
        """
        if not self._running:
            return
        self._running = False

        # Shutdown main socket
        if self._main_sock:
            try:
                self._main_sock.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass
            try:
                self._main_sock.close()
            except Exception:
                pass
            self._main_sock = None

        # Shutdown peer sockets
        for s in self._peers[:]:
            try:
                s.shutdown(socket.SHUT_RDWR)
            except Exception:
                pass

        # Cancel pending RPC futures
        with self._rpc_lock:
            for rid, fut in list(self._pending_requests.items()):
                if not fut.done():
                    fut.set_exception(NetError("Connection closed"))
            self._pending_requests.clear()

        # Wait for heartbeat thread
        if self._hb_thread and self._hb_thread.is_alive() and \
           self._hb_thread != threading.current_thread():
            self._hb_thread.join(timeout=0.5)

        # Close peers
        for s in self._peers:
            try:
                s.close()
            except Exception:
                pass
        self._peers.clear()

    # --------------------------------------------------------------------- #
    #  Public API – messaging
    # --------------------------------------------------------------------- #
    def send(self, data: Dict[str, Any], to_socket: Optional[socket.socket] = None) -> None:
        """
        Send a dictionary (will be JSON-encoded).

        Behaviour
        ---------
        Host  -> broadcast to all connected clients if to_socket is None
                 else send to the specified client
        Client-> send to the single server peer

        Parameters
        ----------
        data : dict
            JSON-serialisable payload
        to_socket : socket, optional
            Host only: target client socket for unicast
        """
        raw = pack(data)
        if self.is_host:
            if to_socket:
                try:
                    to_socket.sendall(raw)
                except Exception:
                    self._remove_peer(to_socket)
            else:
                for s in self._peers[:]:
                    try:
                        s.sendall(raw)
                    except Exception:
                        self._remove_peer(s)
        else:
            if self._main_sock:
                self._main_sock.sendall(raw)

    # --------------------------------------------------------------------- #
    #  Public API – RPC
    # --------------------------------------------------------------------- #
    def request(self,
                data: Dict[str, Any],
                timeout: Optional[float] = None,
                request_type: str = "rpc_request",
                send_request: bool = True,
                to_socket: Optional[socket.socket] = None) -> Dict[str, Any]:
        """
        Perform a synchronous RPC call.

        Parameters
        ----------
        data : dict
            Payload sent to the remote handler
        timeout : float, optional
            Seconds to wait; defaults to self._default_timeout
        request_type : str
            Key to select the remote handler
        to_socket : socket, optional
            Host only: which client to talk to; required when >1 peers

        Returns
        -------
        dict
            Remote handler return value

        Raises
        ------
        ValueError
            Host with multiple clients but no to_socket
        TimeoutError
            Response not received in time
        NetError
            Network or serialization error
        """
        if timeout is None:
            timeout = self._default_timeout

        if self.is_host and len(self._peers) > 1 and to_socket is None:
            raise ValueError("Host with multiple clients must specify to_socket")

        request_id = str(uuid.uuid4())
        future = Future()

        with self._rpc_lock:
            self._pending_requests[request_id] = future


        try:
            if send_request:
                self.send(data, to_socket=to_socket)
            try:
                return future.result(timeout=timeout)
            except TimeoutError:
                with self._rpc_lock:
                    self._pending_requests.pop(request_id, None)
                raise TimeoutError(f"Request timeout after {timeout} seconds")
        except Exception as e:
            with self._rpc_lock:
                self._pending_requests.pop(request_id, None)
            if isinstance(e, (TimeoutError, ValueError)):
                raise
            raise NetError(f"Request failed: {e}")

    def request_to_peer(self,
                        data: Dict[str, Any],
                        peer_index: int = 0,
                        timeout: Optional[float] = None,
                        request_type: str = "rpc_request") -> Dict[str, Any]:
        """
        Convenience wrapper for host to call a specific client by index.

        Parameters
        ----------
        peer_index : int
            Index inside self._peers list

        Raises
        ------
        NetError
            If invoked on Client side
        ValueError
            Index out of range
        """
        if not self.is_host:
            raise NetError("Client cannot use request_to_peer()")
        if peer_index >= len(self._peers):
            raise ValueError(f"Peer index {peer_index} out of range (total: {len(self._peers)})")
        return self.request(data, timeout, request_type, self._peers[peer_index])

    def register_handler(self,
                         request_type: str,
                         handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        """
        Register a handler for incoming RPC requests.

        Parameters
        ----------
        request_type : str
            The "type" field value that maps to this handler
        handler : callable(payload: dict) -> dict
            Business logic; return value will be sent back as payload
        """
        self._request_handlers[request_type] = handler

    def set_default_timeout(self, timeout: float) -> None:
        """
        Change the default RPC timeout.

        Parameters
        ----------
        timeout : float
            Seconds
        """
        self._default_timeout = timeout

    def get_peer_count(self) -> int:
        """
        Return the number of connected clients.

        Raises
        ------
        NetError
            If invoked on Client side
        """
        if not self.is_host:
            raise NetError("Only host can get peer count")
        return len(self._peers)

    # --------------------------------------------------------------------- #
    #  Private – Host initialisation
    # --------------------------------------------------------------------- #
    def _start_host(self) -> None:
        """Set up listening socket and background threads."""
        self._running = True
        self._main_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._main_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._main_sock.bind((self.host_ip, self.port))
        self._main_sock.listen(5)

        # Accept thread
        acc_thread = threading.Thread(target=self._accept_loop, daemon=True)
        acc_thread.start()

        # Heart-beat thread
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._hb_thread.start()

        self.is_connected = True
        if self.on_connected:
            self.on_connected()

    # --------------------------------------------------------------------- #
    #  Private – Client initialisation
    # --------------------------------------------------------------------- #
    def _start_client(self) -> None:
        """Connect to remote host and spawn receiver & heartbeat threads."""
        self._running = True
        self._main_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._main_sock.settimeout(10)          # connect timeout
        try:
            self._main_sock.connect((self.host_ip, self.port))
        except Exception as e:
            raise NetError(f"Connection failed: {e}") from e
        self._main_sock.settimeout(None)        # back to blocking
        self._server_socket = self._main_sock   # keep reference for heartbeat

        # Receiver thread
        recv_thread = threading.Thread(
            target=self._recv_loop, args=(self._main_sock, True), daemon=True
        )
        recv_thread.start()

        # Heart-beat thread
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._hb_thread.start()

        self.is_connected = True
        if self.on_connected:
            self.on_connected()

    # --------------------------------------------------------------------- #
    #  Private – Host connection acceptor
    # --------------------------------------------------------------------- #
    def _accept_loop(self) -> None:
        """Run in daemon thread – accept new clients."""    
        assert self.is_host
        while self._running:
            try:
                conn, addr = self._main_sock.accept()
                self._peers.append(conn)
                self._last_seen[conn] = time.time()
                
                # 【新增】通知有客户端连接了
                print(f"✅ 客户端已连接: {addr}")
                if hasattr(self, 'on_peer_connected') and self.on_peer_connected:
                    self.on_peer_connected(len(self._peers))  # 传入客户端数量
                
                threading.Thread(
                    target=self._recv_loop, args=(conn, False), daemon=True
                ).start()
            except Exception as e:
                print(f"❌ 接受客户端连接时出错: {e}")


    # --------------------------------------------------------------------- #
    #  Private – remove dead peer (Host only)
    # --------------------------------------------------------------------- #
    def _remove_peer(self, sock: socket.socket) -> None:
        """Clean up a disconnected client socket."""
        if sock in self._peers:
            self._peers.remove(sock)
        self._last_seen.pop(sock, None)
        sock.close()
        # If no clients left, notify application
        if self.is_host and not self._peers and self.on_disconnect:
            self.on_disconnect()

    # --------------------------------------------------------------------- #
    #  Private – receiver loop (Host & Client)
    # --------------------------------------------------------------------- #
    
    def _recv_loop(self, sock: socket.socket, is_client_me: bool) -> None:
        """Parse newline-delimited JSON and dispatch messages."""
        buffer = ""
        peer_info = "Client" if is_client_me else f"Peer {sock.getpeername() if sock else '?'}"
        
        while self._running:
            try:
                data = sock.recv(4096).decode("utf-8")
                if not data: # peer shutdown
                    print(f"[Network] {peer_info} 断开连接")
                    break
                
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    msg = unpack(line)
                    
                    # 【新增】打印接收到的数据包
                    msg_type = msg.get("type", "unknown")
                    if msg_type in ["ping", "pong"]:
                        # 心跳包用更简洁的格式
                        print(f"[Network RX] {peer_info} <- HEARTBEAT({msg_type})")
                    else:
                        # 其他数据包打印完整信息
                        print(f"[Network RX] {peer_info} <- {msg}")
                    
                    # RPC messages are processed first
                    if self._handle_rpc_message(msg, sock):
                        continue
                    
                    # Heart-beat packets – handled internally
                    if msg.get("type") == "ping":
                        self._last_seen[sock] = time.time()
                        continue
                    
                    if msg.get("type") == "pong":
                        self._last_seen[sock] = time.time()
                        continue
                    
                    # Business packet – forward to application
                    # 【新增】确保 on_message 回调被执行
                    if self.on_message:
                        print(f"[Network] 调用 on_message 回调，消息类型: {msg_type}")
                        self.on_message(msg)
                    else:
                        print(f"[Network] ⚠️  警告: on_message 回调未设置!")
            
            except Exception as e:
                print(f"[Network] {peer_info} 接收错误: {e}")
                break
        
        # Peer lost – clean up
        print(f"[Network] {peer_info} 连接已关闭，进行清理...")
        
        if is_client_me:
            self._running = False
            # Cancel pending RPCs on client side
            with self._rpc_lock:
                for request_id, future in list(self._pending_requests.items()):
                    if not future.done():
                        future.set_exception(NetError("Connection lost while waiting for response"))
                self._pending_requests.clear()
            
            if self.on_disconnect:
                self.on_disconnect()
        else:
            self._remove_peer(sock)


    # --------------------------------------------------------------------- #
    #  Private – RPC internals
    # --------------------------------------------------------------------- #
    def _handle_rpc_message(self, msg: Dict[str, Any], sock: socket.socket) -> bool:
        """
        Return True if message was consumed by RPC layer.
        """
        msg_type = msg.get("type", "")
        if msg_type == "rpc_response":
            request_id = msg.get("request_id")
            if request_id:
                self._handle_rpc_response(request_id, msg.get("payload", {}))
                return True
        elif msg_type in self._request_handlers:
            request_id = msg.get("request_id")
            if request_id:
                self._handle_rpc_request(msg_type, request_id, msg.get("payload", {}), sock)
                return True
        return False

    def _handle_rpc_response(self, request_id: str, payload: Dict[str, Any]) -> None:
        """Wake up waiting future with response payload."""
        with self._rpc_lock:
            if request_id in self._pending_requests:
                future = self._pending_requests[request_id]
                if not future.done():
                    future.set_result(payload)

    def _handle_rpc_request(self,
                            request_type: str,
                            request_id: str,
                            payload: Dict[str, Any],
                            sock: socket.socket) -> None:
        """Execute handler and send back result."""
        handler = self._request_handlers.get(request_type)
        if not handler:
            error_response = {
                "type": "rpc_response",
                "request_id": request_id,
                "payload": {
                    "error": f"No handler registered for request type: {request_type}",
                    "status": "error"
                }
            }
            try:
                sock.sendall(pack(error_response))
            except Exception:
                pass
            return

        try:
            response_payload = handler(payload)
            response_msg = {
                "type": "rpc_response",
                "request_id": request_id,
                "payload": response_payload
            }
            sock.sendall(pack(response_msg))
        except Exception as e:
            error_response = {
                "type": "rpc_response",
                "request_id": request_id,
                "payload": {
                    "error": str(e),
                    "status": "error"
                }
            }
            try:
                sock.sendall(pack(error_response))
            except Exception:
                pass

    # --------------------------------------------------------------------- #
    #  Private – heart-beating (Host & Client)
    # --------------------------------------------------------------------- #
    def _heartbeat_loop(self) -> None:
        """Send periodic pings and enforce timeout."""
        while self._running:
            time.sleep(self._hb_interval)
            now = time.time()

            if self.is_host:
                # Broadcast ping & check client timeouts
                self.send({"type": "ping"})
                for s in self._peers[:]:
                    if now - self._last_seen.get(s, 0) > self._hb_timeout:
                        self._remove_peer(s)
            else:
                # Send pong & check server timeout
                self.send({"type": "pong"})
                if now - self._last_seen.get(self._main_sock, 0) > self._hb_timeout:
                    self.close()
                    if self.on_disconnect:
                        self.on_disconnect()
                    break

            # Keep our own timestamp fresh
            target = self._main_sock if not self.is_host else self._main_sock
            self._last_seen[target] = now


# ---------------  Typical Usage Patterns  -------------------------------------

"""
1. Host (creates the room)
----------------------------
from network import Network

def handle(msg):
    print('Host received:', msg)

host = Network(is_host=True, port=5555)
host.on_message = handle
host.start()
# blocks forever – keep main thread alive
while True:
    import time
    time.sleep(1)

2. Client (joins the room)
----------------------------
from network import Network

def handle(msg):
    print('Client received:', msg)

client = Network(is_host=False)
client.on_message = handle
client.connect('192.168.1.10')   # IP of the host
client.send({'type': 'hello', 'name': 'Alice'})

3. Host with RPC service
----------------------------
from network import Network

def add_handler(payload):
    return {"sum": payload["a"] + payload["b"]}

host = Network(is_host=True, port=5555)
host.register_handler("add", add_handler)
host.start()

while True:
    time.sleep(1)

4. Client RPC call
----------------------------
from network import Network

client = Network(is_host=False)
client.connect('127.0.0.1')
try:
    ans = client.request({"a": 3, "b": 4}, request_type="add")
    print("3+4=", ans["sum"])
except Exception as e:
    print("RPC failed:", e)
"""