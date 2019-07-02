import multiprocessing
import multiprocessing.synchronize
import socket
import pickle
import struct
import os
import setproctitle
from typing import Callable


def process_title(title: str):
    def set_process_title_wrapper(run_func: Callable):
        def run_func_wrapper(*args, **kwargs):
            setproctitle.setproctitle(title)
            return run_func(*args, **kwargs)

        return run_func_wrapper

    return set_process_title_wrapper


class Connection:
    def __init__(self, conn: socket.socket, lock: bool = False):
        self._conn = conn
        self._pickle_data_struct = struct.Struct(r'!i')
        self._pickle_data_header_size = self._pickle_data_struct.size
        self._read_lock = None
        self._write_lock = None
        self.use_lock(use=lock)

    def use_lock(self, use: bool = True):
        if use:
            self._read_lock = multiprocessing.Lock()
            self._write_lock = multiprocessing.Lock()
        else:
            self._read_lock = None
            self._write_lock = None

    def _recvall(self) -> memoryview:
        header = self._conn.recv(self._pickle_data_header_size)
        (data_len,) = self._pickle_data_struct.unpack(header)
        # print('recv data_len', data_len)

        pickle_data = memoryview(bytearray(data_len))
        offset = 0
        while data_len:
            nbytes = self._conn.recv_into(pickle_data[offset:], data_len)
            if nbytes <= 0:
                raise OSError('EOF')

            offset += nbytes
            data_len -= nbytes

        return pickle_data

    def _recv_pickle_data(self) -> memoryview:
        if self._read_lock:
            with self._read_lock:
                pickle_data = self._recvall()
        else:
            pickle_data = self._recvall()

        return pickle_data

    def _send_pickle_data(self, pickle_data: bytes):
        data_len = len(pickle_data)
        data = memoryview(bytearray(self._pickle_data_header_size + data_len))

        self._pickle_data_struct.pack_into(data, 0, data_len)
        data[self._pickle_data_header_size:] = pickle_data

        if self._write_lock:
            with self._write_lock:
                self._conn.sendall(data.tobytes())
        else:
            self._conn.sendall(data.tobytes())

    def recv(self) -> object:
        data = self._recv_pickle_data()
        obj = pickle.loads(data)
        return obj

    def send(self, obj):
        data = pickle.dumps(obj)
        self._send_pickle_data(data)

    def close(self):
        self._conn.close()


def Pipe() -> (Connection, Connection):
    s1, s2 = socket.socketpair(family=socket.AF_UNIX, type=socket.SOCK_STREAM)
    c1 = Connection(s1)
    c2 = Connection(s2)
    return c1, c2


class Pool:
    def __init__(self, processes: int = None, title_format: str = None):
        if processes is None:
            processes = os.cpu_count() or 1

        self._title_format = title_format
        self._child_conn, self._parent_conn = Pipe()
        self._child_conn.use_lock()
        self._procs = []

        for i in range(processes):
            if self._title_format is None:
                target = self._worker_proc
            else:
                wrapper = process_title(self._title_format % (i,))
                target = wrapper(self._worker_proc)
            p = multiprocessing.Process(target=target)
            self._procs.append(p)
            p.start()

        self._child_conn.close()

    def _worker_proc(self):
        self._parent_conn.close()

        while True:
            try:
                i, func, args = self._child_conn.recv()
                try:
                    res = func(*args)
                except Exception as e:
                    print(type(e).__name__, e)
                    res = None
                self._child_conn.send((i, res))
            except Exception as e:
                break

        print('pool.worker exited')

    def starmap(self, func, args_list):
        for i, args in enumerate(args_list):
            self._parent_conn.send((i, func, args))

        count = len(args_list)
        ret = [None] * count

        while count > 0:
            try:
                i, res = self._parent_conn.recv()
                ret[i] = res
                count -= 1
            except Exception:
                break

        return ret

    def join(self):
        for p in self._procs:
            p.join()
            p.close()

        print('pool.joined')

    def terminate(self):
        for p in self._procs:
            p.terminate()

        print('pool.terminated')

    def close(self):
        self._parent_conn.close()
        print('pool.closed')

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.terminate()
        self.close()
        self.join()


if __name__ == '__main__':
    import time


    def test(a, b, c):
        print(os.getpid(), a, b, c)
        time.sleep(100)
        return a + b


    pool = Pool(4, 'Go Worker %d')

    res = pool.starmap(test, [(1, 1, list(range(10000))), (2, 2, 2), (3, 3, 3), (4, 4, 4), (5, 5, 5)])
    print(res)
    # pool.terminate()
    # import time
    #
    # time.sleep(1)
    pool.close()
    pool.join()
