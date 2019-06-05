"""
Unicast Heartbeat module
"""
import sys
import socket
import threading
import time

import six
import rcExceptions as ex
import osvcd_shared as shared
from rcGlobalEnv import rcEnv
from storage import Storage
from hb import Hb

class HbUcast(Hb):
    """
    A class factorizing common methods and properties for the unicast
    heartbeat tx and rx child classes.
    """
    config_change = False
    timeout = None
    peer_config = None

    def status(self, **kwargs):
        data = Hb.status(self, **kwargs)
        data.stats = Storage(self.stats)
        data.config = {
            "addr": self.peer_config[rcEnv.nodename].addr,
            "port": self.peer_config[rcEnv.nodename].port,
            "timeout": self.timeout,
        }
        return data

    def configure(self):
        self.reset_stats()
        self._configure()

    def reconfigure(self):
        self._configure()

    def _configure(self):
        self.get_hb_nodes()
        peer_config = {}

        # peers
        for nodename in self.hb_nodes:
            if nodename not in peer_config:
                addr = shared.NODE.oget(self.name, "addr", impersonate=nodename)
                port = shared.NODE.oget(self.name, "port", impersonate=nodename)
                if addr is not None:
                    pass
                elif nodename == rcEnv.nodename:
                    addr = "0.0.0.0"
                else:
                    addr = nodename
                peer_config[nodename] = Storage({
                    "addr": addr,
                    "port": port,
                })

        if peer_config != self.peer_config:
            self.config_change = True
            self.peer_config = peer_config

        timeout = shared.NODE.oget(self.name, "timeout")

        if timeout != self.timeout:
            self.config_change = True
            self.timeout = timeout

        self.max_handlers = len(self.hb_nodes) * 4

class HbUcastTx(HbUcast):
    """
    The unicast heartbeat tx class.
    """
    def __init__(self, name):
        HbUcast.__init__(self, name, role="tx")

    def run(self):
        self.set_tid()
        try:
            self.configure()
        except ex.excAbortAction:
            return

        try:
            while True:
                self.do()
                if self.stopped():
                    sys.exit(0)
                with shared.HB_TX_TICKER:
                    shared.HB_TX_TICKER.wait(self.default_hb_period)
        except Exception as exc:
            self.log.exception(exc)

    def status(self, **kwargs):
        data = HbUcast.status(self, **kwargs)
        data["config"] = {}
        return data

    def do(self):
        self.janitor_procs()
        self.reload_config()
        message, message_bytes = self.get_message()
        if message is None:
            return

        for nodename, config in self.peer_config.items():
            if nodename == rcEnv.nodename:
                continue
            self._do(message, message_bytes, nodename, config)

    def _do(self, message, message_bytes, nodename, config):
        try:
            #self.log.info("sending to %s:%s", config.addr, config.port)
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            sock.bind((self.peer_config[rcEnv.nodename].addr, 0))
            sock.connect((config.addr, config.port))
            sock.sendall((message+"\0").encode())
            self.set_last(nodename)
            self.push_stats(message_bytes)
        except socket.timeout as exc:
            self.push_stats()
            if self.get_last(nodename).success:
                self.log.warning("send to %s (%s:%d) timeout", nodename,
                                 config.addr, config.port)
            self.set_last(nodename, success=False)
        except socket.error as exc:
            self.push_stats()
            if self.get_last(nodename).success:
                self.log.warning("send to %s (%s:%d) error: %s", nodename,
                               config.addr, config.port, str(exc))
            self.set_last(nodename, success=False)
        finally:
            self.set_beating(nodename)
            sock.close()

class HbUcastRx(HbUcast):
    """
    The unicast heartbeat rx class.
    """
    def __init__(self, name):
        HbUcast.__init__(self, name, role="rx")
        self.sock = None

    def _configure(self):
        HbUcast._configure(self)
        if not self.config_change:
            return
        self.config_change = False
        if self.sock:
            self.log.debug("close socket")
            self.sock.close()
        self.log.debug("bind socket")
        for _ in range(3):
            try:
                self.configure_listener()
                return
            except socket.error as exc:
                time.sleep(1)
        self.log.error("init error: %s", str(exc))
        raise ex.excAbortAction

    def configure_listener(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.bind((self.peer_config[rcEnv.nodename].addr,
                        self.peer_config[rcEnv.nodename].port))
        self.sock.listen(5)
        self.sock.settimeout(2)

    def run(self):
        self.set_tid()
        try:
            self.configure()
        except ex.excAbortAction:
            return

        self.log.info("listening on %s:%s",
                      self.peer_config[rcEnv.nodename].addr,
                      self.peer_config[rcEnv.nodename].port)

        while True:
            self.do()
            if self.stopped():
                self.join_threads()
                self.sock.close()
                sys.exit(0)

    def do(self):
        self.reload_config()
        self.janitor_procs()
        self.janitor_threads()

        try:
            conn, addr = self.sock.accept()
        except socket.timeout:
            return
        finally:
            self.set_peers_beating()
        if len(self.threads) >= self.max_handlers:
            self.log.warning("drop message received from %s: too many running handlers (%d)",
                             addr, self.max_handlers)
            return
        try:
            thr = threading.Thread(target=self.handle_client, args=(conn, addr))
            thr.start()
            self.threads.append(thr)
        except RuntimeError as exc:
            self.log.warning(exc)
            conn.close()

    def handle_client(self, conn, addr):
        try:
            self._handle_client(conn, addr)
        finally:
            conn.close()

    def _handle_client(self, conn, addr):
        chunks = []
        buff_size = 4096
        while True:
            chunk = conn.recv(buff_size)
            if chunk:
                chunks.append(chunk)
            if not chunk or chunk.endswith(b"\x00"):
                break
        data = six.b("").join(chunks)
        self.push_stats(len(data))
        del chunks

        nodename, data = self.decrypt(data, sender_id=addr[0])
        if nodename is None or nodename == rcEnv.nodename:
            # ignore hb data we sent ourself
            return
        elif nodename not in self.hb_nodes:
            return
        if data is None:
            self.push_stats()
            self.set_beating(nodename)
            return
        try:
            self.store_rx_data(data, nodename)
            self.set_last(nodename)
        except Exception as exc:
            if self.get_last(nodename).success:
                self.log.error("%s", exc)
            self.set_last(nodename, success=False)
        finally:
            self.set_beating(nodename)



