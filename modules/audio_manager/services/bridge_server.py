import json
import struct
from PyQt6.QtCore import QObject, pyqtSignal, QThread
from PyQt6.QtNetwork import QTcpServer, QHostAddress, QTcpSocket

class BridgeServer(QObject):
    """
    本地 TCP 服务器，用于接收来自 Native Host (浏览器插件中继) 的连接。
    主程序通过此类向插件发送指令。
    """
    message_received = pyqtSignal(dict)
    connected = pyqtSignal()
    disconnected = pyqtSignal()

    def __init__(self, port=9999, parent=None):
        super().__init__(parent)
        self.port = port
        self.server = QTcpServer(self)
        self.client_socket = None
        self.server.newConnection.connect(self._handle_new_connection)

    def start(self):
        if not self.server.isListening():
            success = self.server.listen(QHostAddress.SpecialAddress.LocalHost, self.port)
            if success:
                print(f"📡 BridgeServer listening on port {self.port}")
            else:
                print(f"❌ BridgeServer failed to listen on port {self.port}")
            return success
        return True

    def stop(self):
        if self.client_socket:
            self.client_socket.disconnectFromHost()
        self.server.close()

    def _handle_new_connection(self):
        # 仅支持单连接（一个浏览器实例）
        new_socket = self.server.nextPendingConnection()
        if self.client_socket:
            print("⚠️ 已有连接，断开旧连接")
            self.client_socket.disconnectFromHost()
            self.client_socket.deleteLater()
        
        self.client_socket = new_socket
        self.client_socket.readyRead.connect(self._read_data)
        self.client_socket.disconnected.connect(self._on_disconnected)
        print("✅ 浏览器 Host 已连接")
        self.connected.emit()

    def _on_disconnected(self):
        print("ℹ️ 浏览器 Host 已断开")
        self.client_socket = None
        self.disconnected.emit()

    def _read_data(self):
        if not self.client_socket:
            return

        while self.client_socket.bytesAvailable() >= 4:
            # 协议：4字节长度 + JSON 数据
            raw_len = self.client_socket.peek(4)
            msg_len = struct.unpack("<I", raw_len)[0]
            
            if self.client_socket.bytesAvailable() < 4 + msg_len:
                break
            
            # 读取长度头
            self.client_socket.read(4)
            # 读取数据
            data = self.client_socket.read(msg_len)
            try:
                msg = json.loads(data.decode("utf-8"))
                self.message_received.emit(msg)
            except Exception as e:
                print(f"❌ 解析消息失败: {e}")

    def send_message(self, msg: dict):
        if not self.client_socket:
            return False
        
        try:
            data = json.dumps(msg, ensure_ascii=False).encode("utf-8")
            self.client_socket.write(struct.pack("<I", len(data)))
            self.client_socket.write(data)
            self.client_socket.flush()
            return True
        except Exception as e:
            print(f"❌ 发送消息失败: {e}")
            return False

    def is_connected(self):
        return self.client_socket is not None and self.client_socket.state() == QTcpSocket.SocketState.ConnectedState
