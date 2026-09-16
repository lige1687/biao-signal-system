"""独立复核工具：彻底禁用网络后再运行目标命令。

任何 socket 创建（含 DNS）都会抛错，用于证明「离线复用」名副其实，
而不是依赖「我没写联网代码」这种自我声明。
"""
import socket
import sys
import runpy


class NetworkBlocked(RuntimeError):
    pass


def _blocked(*a, **k):
    raise NetworkBlocked("网络已被复核工具禁用")


socket.socket = _blocked
socket.create_connection = _blocked
socket.getaddrinfo = _blocked
socket.gethostbyname = _blocked

target = sys.argv[1]
sys.argv = sys.argv[1:]
runpy.run_path(target, run_name="__main__")
