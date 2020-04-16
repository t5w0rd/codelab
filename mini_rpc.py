__author__ = 'jing.liu@yff.com'

import socket
import threading
import os
import pickle
import struct
# import traceback
from enum import Enum
from typing import Optional, Union, Dict, List, Callable

packed_data_header_struct = struct.Struct(r'!i')
packed_data_header_size = packed_data_header_struct.size


def _recv_data(sock: socket.socket) -> memoryview:
    header = sock.recv(packed_data_header_size)
    if len(header) is 0:
        raise OSError('EOF')

    (data_len,) = packed_data_header_struct.unpack(header)

    data = memoryview(bytearray(data_len))
    offset = 0
    while data_len:
        nbytes = sock.recv_into(data[offset:], data_len)
        if nbytes <= 0:
            raise OSError('EOF')

        offset += nbytes
        data_len -= nbytes

    return data


def _send_data(sock: socket.socket, data: bytes):
    data_len = len(data)
    all_data = memoryview(bytearray(packed_data_header_size + data_len))

    packed_data_header_struct.pack_into(all_data, 0, data_len)
    all_data[packed_data_header_size:] = data

    sock.sendall(all_data.tobytes())


def recv_object(sock: socket.socket) -> object:
    data = _recv_data(sock)
    obj = pickle.loads(data)
    return obj


def send_object(sock: socket.socket, obj: object):
    data = pickle.dumps(obj)
    _send_data(sock, data)


def _create_socket(addr: Union[tuple, str], force=False) -> socket.socket:
    sock = None
    if isinstance(addr, str):
        # unix domain socket
        if force and os.path.exists(addr):
            os.unlink(addr)
        sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    elif isinstance(addr, tuple):
        # tcp socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if force:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

    return sock


RPCType = Enum('RPCType', {'rpc_client': 1, 'rpc_server': 2})
rpc_client = RPCType.rpc_client
rpc_server = RPCType.rpc_server

_RPCFuncType = Enum('_RPCFuncType', {'_rpc_method': 1, '_rpc_function': 2})
_rpc_method = 1
_rpc_function = 2


class RPCObject:
    """
    服务端务必在协程环境下使用，非线程安全
    """

    def __init__(self):
        self._addr: Union[tuple, str, None] = None
        self._rpc_type: RPCType = -1
        # self._pack = pack
        # self._unpack = unpack
        self._rpc_sock: Optional[socket.socket] = None
        self.rpc_client_keepalive = False

        self._rpc_connections: Dict[socket.socket, threading.Thread] = {}
        self._rpc_closed_connections: List[socket.socket] = []
        self._rpc_server_thread: Optional[threading.Thread] = None
        self._rpc_server_stop_event: Optional[threading.Event] = None

        # 防止多个协程共用一个socket乱序
        # self._client_seq = 1000
        # self._client_recv_keeper = {}

    def start_rpc_server(self, addr: Union[tuple, str]):
        """
        服务端务必在协程环境下使用，非线程安全
        :param addr:
        :return:
        """
        assert self._rpc_type is -1, 'this object is busy'
        assert isinstance(addr, (tuple, str))

        self._rpc_type = rpc_server
        self._addr = addr
        self._rpc_sock = _create_socket(addr, force=True)
        self._rpc_sock.bind(addr)
        self._rpc_sock.listen(5)

        self._rpc_server_stop_event = threading.Event()
        self._rpc_server_thread = threading.Thread(target=self._rpc_server)
        self._rpc_server_thread.start()

    def _cleanup_closed_connections(self):
        for conn in self._rpc_closed_connections:
            conn_thread = self._rpc_connections.pop(conn)
            conn.close()
            conn_thread.join()
        self._rpc_closed_connections.clear()

    def stop_rpc_server(self):
        assert self._rpc_type is rpc_server, 'not server'
        if self._rpc_sock is not None:
            self._rpc_server_stop_event.set()
            self._rpc_sock.close()
            self._cleanup_closed_connections()
            for conn, conn_thread in self._rpc_connections.items():
                conn.close()
                conn_thread.join()

            self._rpc_connections.clear()

            self._rpc_server_thread.join()
            self._rpc_server_thread = None
            self._rpc_type = -1

    def _rpc_server(self):
        while not self._rpc_server_stop_event.is_set():
            try:
                conn, addr = self._rpc_sock.accept()
                self._cleanup_closed_connections()
                conn_thread = threading.Thread(target=self._rpc_connection, args=(conn, addr))
                # conn_thread.daemon = True
                self._rpc_connections[conn] = conn_thread
                conn_thread.start()
            except:
                # traceback.print_exc()
                break

    def _rpc_connection(self, conn: socket.socket, addr: Union[tuple, str]):
        while not self._rpc_server_stop_event.is_set():
            try:
                func_type, func_name, args, kwargs = recv_object(conn)
                if func_type is _rpc_method:
                    func = getattr(self, func_name)
                else:
                    assert func_type is _rpc_function
                    func = globals()[func_name]

                res, err = None, None
                try:
                    res = func(*args, **kwargs)
                except Exception as e:
                    err = e
                send_object(conn, (res, err))
            except:
                # traceback.print_exc()
                break

        self._rpc_closed_connections.append(conn)

    def start_rpc_client(self, addr: Union[tuple, str], keepalive=False):
        assert self._rpc_type is -1, 'this object is busy'
        assert isinstance(addr, (tuple, str))

        self._rpc_type = rpc_client
        self._addr = addr
        self.rpc_client_keepalive = keepalive
        if keepalive:
            self._rpc_sock = self.create_and_connect()

    def create_and_connect(self) -> socket.socket:
        sock = _create_socket(self._addr)
        sock.connect(self._addr)
        return sock

    def stop_rpc_client(self):
        assert self._rpc_type is rpc_client, 'not client'
        if self._rpc_sock is not None:
            self._rpc_sock.close()
            self._rpc_sock = None
            self._rpc_type = -1

    def recv_object(self) -> object:
        assert self.rpc_type is rpc_client, 'not client'
        return recv_object(self._rpc_sock)

        # # 客户端模式下，防止复用相同socket引发包乱序，使用当前串号
        # if self._client_seq in self._client_recv_keeper:
        #     return self._client_recv_keeper.pop(self._client_seq)
        #
        # seq, obj = recv_object(self._rpc_sock)
        # while seq != self._client_seq:
        #     self._client_recv_keeper[seq] = obj
        #     seq, obj = recv_object(self._rpc_sock)
        # return obj

    def send_object(self, obj: object):
        assert self.rpc_type is rpc_client, 'not client'
        return send_object(self._rpc_sock, obj)

        # # 客户端模式下，串号每次发送自增
        # self._client_seq = self._client_seq + 1
        # return send_object(self._rpc_sock, (self._client_seq, obj))

    @property
    def rpc_type(self):
        return self._rpc_type


def rpcmethod(func: Callable):
    # import os
    # from .logging import get_manager_logger
    # logger = get_manager_logger()

    def func_wrapper(o: RPCObject, *args, **kwargs):
        if o.rpc_type is rpc_client:
            obj = (_rpc_method, func.__name__, args, kwargs)
            if not o.rpc_client_keepalive:
                sock = o.create_and_connect()
                send_object(sock, obj)
                obj = recv_object(sock)
                sock.close()
            else:
                o.send_object(obj)
                obj = o.recv_object()
            res, err = obj
            # logger.info('rpcmethod: %s, ret: %r, err: %r, pid: %d', func.__name__, res, err, os.getpid())
            if err is not None:
                raise err
            return res
        else:
            assert o.rpc_type is rpc_server
            return func(o, *args, **kwargs)

    return func_wrapper


default_rpc_object = RPCObject()


def rpcfunction(o: RPCObject = default_rpc_object):
    # import os
    # from .logging import get_manager_logger
    # logger = get_manager_logger()

    def rpcfunction_wrapper(func: Callable):
        def func_wrapper(*args, **kwargs):
            if o.rpc_type is rpc_client:
                obj = (_rpc_function, func.__name__, args, kwargs)
                if not o.rpc_client_keepalive:
                    sock = o.create_and_connect()
                    send_object(sock, obj)
                    obj = recv_object(sock)
                    sock.close()
                else:
                    o.send_object(obj)
                    obj = o.recv_object()
                res, err = obj
                # logger.info('rpcfunction: %s, ret: %r, err: %r, pid: %d', func.__name__, res, err, os.getpid())
                if err is not None:
                    raise err
                return res
            else:
                assert o.rpc_type is rpc_server
                return func(*args, **kwargs)

        return func_wrapper

    if isinstance(o, Callable):
        func = o
        o = default_rpc_object
        return rpcfunction_wrapper(func)

    return rpcfunction_wrapper


if __name__ == '__main__':
    class TestObject(RPCObject):
        def __init__(self):
            RPCObject.__init__(self)
            self.a = 1

        @rpcmethod
        def inc(self, dt):
            self.a += dt
            return self.a

        @rpcmethod
        def print(self):
            print(self.a)
            raise(RuntimeError('TEST ERROR'))


    @rpcfunction
    def show(s):
        print(s)


    import sys, time

    if sys.argv[1] == 'c':
        o = TestObject()
        o.start_rpc_client('test.sock')
        # o.start_rpc_client(('127.0.0.1', 18080))

        default_rpc_object.start_rpc_client('test2.sock')
        show('i\'m client')

        o.inc(5)
        o.print()

        o.stop_rpc_client()
    elif sys.argv[1] == 's':
        o = TestObject()
        o.start_rpc_server('test.sock')
        # o.start_rpc_server(('0.0.0.0', 18080))
        default_rpc_object.start_rpc_server('test2.sock')

        time.sleep(1000)
        o.stop_rpc_server()
