# -*- coding: utf-8 -*-
"""
Host-Client Hybrid Network Layer – Fully Commented Version
---------------------------------------------------------
A single Network class that can act as either
  - Host (listening server that creates the room), or
  - Client (connects to the room).

Features
--------
* JSON messages, newline-delimited
* Automatic heartbeat (ping/pong) every 2 s, timeout 6 s
* Thread-safe, callback-driven
* Clean shutdown & disconnection handling

Author: <your-name>
"""

from __future__ import annotations

import socket
import threading
import time
from typing import Callable, Dict, Any, List, Optional

# --------------------------------------------------------------------------- #
#  Utility layer – replace with your own if needed
# --------------------------------------------------------------------------- #
from .utils import pack, unpack   # noqa: F401


class NetError(Exception):
    """Network-related runtime errors."""


# ============================================================================= #
#  Network – unified Host & Client interface
# ============================================================================= #
class Network:
    """
    Universal TCP networking layer.

    Callbacks (set by application):
        on_message(msg: dict) -> None
        on_disconnect() -> None
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
        self._running = False

        # Close all sockets
        for s in [self._main_sock] + self._peers:
            if s:
                try:
                    s.shutdown(socket.SHUT_RDWR)
                    s.close()
                except Exception:
                    pass
        self._peers.clear()

        # Wait threads (non-blocking)
        if self._hb_thread and self._hb_thread.is_alive():
            self._hb_thread.join(timeout=0.5)

    # --------------------------------------------------------------------- #
    #  Public API – messaging
    # --------------------------------------------------------------------- #
    def send(self, data: Dict[str, Any]) -> None:
        """
        Send a dictionary (will be JSON-encoded).

        Behaviour
        ---------
        Host  -> broadcast to all connected clients
        Client-> send to the single server peer

        Parameters
        ----------
        data : dict
            JSON-serialisable payload
        """
        raw = pack(data)
        if self.is_host:
            # Iterate over a snapshot to allow removal while looping
            for s in self._peers[:]:
                try:
                    s.sendall(raw)
                except Exception:
                    self._remove_peer(s)
        else:
            if self._main_sock:
                self._main_sock.sendall(raw)

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

        # Receiver thread
        recv_thread = threading.Thread(
            target=self._recv_loop, args=(self._main_sock, True), daemon=True
        )
        recv_thread.start()

        # Heart-beat thread
        self._hb_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._hb_thread.start()

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
                threading.Thread(
                    target=self._recv_loop, args=(conn, False), daemon=True
                ).start()
            except Exception:
                pass

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
        while self._running:
            try:
                data = sock.recv(4096).decode("utf-8")
                if not data:                       # peer shutdown
                    break
                buffer += data
                while "\n" in buffer:
                    line, buffer = buffer.split("\n", 1)
                    msg = unpack(line)

                    # Heart-beat packets – handled internally
                    if msg.get("type") == "ping":
                        self._last_seen[sock] = time.time()
                        continue
                    if msg.get("type") == "pong":
                        self._last_seen[sock] = time.time()
                        continue

                    # Business packet – forward to application
                    if self.on_message:
                        self.on_message(msg)
            except Exception:
                break

        # Peer lost – clean up
        if is_client_me:
            self._running = False
            if self.on_disconnect:
                self.on_disconnect()
        else:
            self._remove_peer(sock)

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

3. Disconnection handling
----------------------------
host.on_disconnect = lambda: print("All clients gone – room empty")
client.on_disconnect = lambda: print("Kicked or host died")
"""