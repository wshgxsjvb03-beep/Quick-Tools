import sys
import json
import struct
import socket
import threading
import time

# 配置
HOST = '127.0.0.1'
PORT = 9999

def read_from_socket(sock):
    """从 Socket 读取数据并发送给 Chrome (stdout)"""
    try:
        while True:
            # 协议：4字节长度 + JSON 数据
            raw_len = sock.recv(4)
            if not raw_len or len(raw_len) < 4:
                break
            msg_len = struct.unpack("<I", raw_len)[0]
            data = sock.recv(msg_len)
            if not data or len(data) < msg_len:
                break
            
            # 写入 Chrome 的 stdout
            sys.stdout.buffer.write(raw_len)
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
    except Exception:
        pass

def main():
    """Native host 主循环：桥接 stdin 到 Socket，并启动读取线程"""
    while True:
        try:
            # 建立与主程序的连接
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect((HOST, PORT))
            
            # 启动线程读取来自主程序的消息
            t = threading.Thread(target=read_from_socket, args=(sock,), daemon=True)
            t.start()
            
            # 主循环：读取来自 Chrome 的 stdin 并发送到 Socket
            while True:
                raw_len = sys.stdin.buffer.read(4)
                if not raw_len or len(raw_len) < 4:
                    return # Chrome 关闭了连接
                
                msg_len = struct.unpack("<I", raw_len)[0]
                data = sys.stdin.buffer.read(msg_len)
                if not data or len(data) < msg_len:
                    break
                
                # 转发到 Socket
                sock.sendall(raw_len)
                sock.sendall(data)
                
        except (ConnectionRefusedError, ConnectionResetError):
            # 如果主程序还没启动或断开了，等待重试
            time.sleep(1)
            continue
        except Exception:
            break
        finally:
            try: sock.close()
            except: pass

if __name__ == "__main__":
    main()

