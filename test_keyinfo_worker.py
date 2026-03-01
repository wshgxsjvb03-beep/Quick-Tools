"""
测试 KeyInfoWorker 在 PyQt 环境中的行为
模拟应用程序中的查询流程
"""

import sys
import json
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget, QPushButton, QTextEdit
from PyQt6.QtCore import Qt

# 添加模块路径
sys.path.insert(0, 'modules/audio_manager/services')

from elevenlabs import KeyInfoWorker

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("KeyInfoWorker 测试")
        self.setGeometry(100, 100, 600, 400)
        
        # 主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # 日志显示
        self.log_text = QTextEdit()
        self.log_text.setReadOnly(True)
        layout.addWidget(self.log_text)
        
        # 测试按钮
        test_btn = QPushButton("测试查询第一个 API Key")
        test_btn.clicked.connect(self.test_query)
        layout.addWidget(test_btn)
        
        self.workers = []
        
    def log(self, message):
        self.log_text.append(message)
        print(message)
        
    def test_query(self):
        self.log("=" * 60)
        self.log("开始测试...")
        
        # 从配置文件加载第一个 Key
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            keys = config.get('elevenlabs_keys', [])
            if not keys:
                self.log("❌ 配置文件中没有 API Keys")
                return
            
            test_key = keys[0]['key']
            label = keys[0].get('label', '未命名')
            
            self.log(f"测试 Key: {label} ({test_key[-4:]})")
            
            # 创建 Worker
            worker = KeyInfoWorker(test_key)
            worker.info_received.connect(self.on_info_received)
            worker.error.connect(self.on_error)
            worker.finished.connect(lambda: self.on_finished(worker))
            
            self.workers.append(worker)
            worker.start()
            
            self.log("Worker 已启动,等待结果...")
            
        except Exception as e:
            self.log(f"❌ 错误: {e}")
            import traceback
            traceback.print_exc()
    
    def on_info_received(self, key, info):
        self.log(f"✅ 查询成功!")
        self.log(f"   Key: {key[-4:]}")
        self.log(f"   已用字符: {info['character_count']}")
        self.log(f"   字符限额: {info['character_limit']}")
        self.log(f"   剩余字符: {info['remaining']}")
        self.log(f"   订阅状态: {info['status']}")
    
    def on_error(self, key, error):
        self.log(f"❌ 查询失败!")
        self.log(f"   Key: {key[-4:]}")
        self.log(f"   错误: {error}")
    
    def on_finished(self, worker):
        self.log("Worker 已完成")
        if worker in self.workers:
            self.workers.remove(worker)

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TestWindow()
    window.show()
    sys.exit(app.exec())
