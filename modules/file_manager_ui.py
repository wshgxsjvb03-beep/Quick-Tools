
import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QTextEdit, QMessageBox, QLineEdit, QDialog, QGroupBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# 解决导入路径问题
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from modules.file_manager import FileManager
from modules.config_manager import ConfigManager

class SmartImportDialog(QDialog):
    def __init__(self, parent=None, default_output_dir=""):
        super().__init__(parent)
        self.setWindowTitle("智能导入 - 粘贴您的数据")
        self.resize(600, 500)
        self.output_dir = default_output_dir
        self.parsed_data = None # (text1, text2, link)
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 1. 粘贴区域
        layout.addWidget(QLabel("1. 请粘贴您的数据 (Text1 - Tab - Text2 - Tab - Link):"))
        self.text_area = QTextEdit()
        self.text_area.setPlaceholderText("在此处粘贴...")
        self.text_area.textChanged.connect(self.on_text_changed)
        layout.addWidget(self.text_area)

        # 2. 预览区域
        self.preview_group = QGroupBox("2. 预览与命名")
        preview_layout = QVBoxLayout()
        
        # 显示解析结果简单预览
        self.lbl_status = QLabel("等待粘贴...")
        self.lbl_status.setStyleSheet("color: gray;")
        preview_layout.addWidget(self.lbl_status)
        
        # 命名输入框
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("文件名 (不含后缀):"))
        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("例如: my_data_01")
        name_layout.addWidget(self.name_input)
        preview_layout.addLayout(name_layout)
        
        self.preview_group.setLayout(preview_layout)
        layout.addWidget(self.preview_group)

        # 3. 按钮
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("执行导入 (保存 TXT + 下载文件)")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.run_import)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def on_text_changed(self):
        text = self.text_area.toPlainText()
        result = FileManager.parse_clipboard_data(text)
        
        if result:
            t1, t2, link = result
            self.parsed_data = result
            self.lbl_status.setText(f"✅ 解析成功!\n文本1: {t1[:20]}...\n文本2: {t2[:20]}...\n链接: {link[:40]}...")
            self.lbl_status.setStyleSheet("color: green;")
            self.btn_save.setEnabled(True)
        else:
            self.parsed_data = None
            self.lbl_status.setText("❌ 格式不匹配，无法解析。请确保有三列数据。")
            self.lbl_status.setStyleSheet("color: red;")
            self.btn_save.setEnabled(False)

    def run_import(self):
        name = self.name_input.text().strip()
        if not name:
            QMessageBox.warning(self, "提示", "请输入文件名！")
            return

        if not self.output_dir:
            QMessageBox.warning(self, "提示", "未设置输出目录，请先在主界面设置全局路径！")
            return
            
        # 开始处理
        try:
            # 1. 保存 TXT
            txt_path = os.path.join(self.output_dir, f"{name}.txt")
            t1, t2, url = self.parsed_data
            
            if FileManager.save_text(t1, t2, txt_path):
                # 2. 下载文件
                # 创建一个简单的进度对话框或者直接阻塞(简单起见先阻塞，如果文件大建议用线程)
                # 这里为了体验，简单的阻塞一下，如果用户觉得卡，后续优化为线程
                QMessageBox.information(self, "开始下载", "文本已保存，即将开始下载文件，请稍候...")
                
                base_path = os.path.join(self.output_dir, name) # 不带后缀
                success, msg = FileManager.download_file(url, base_path)
                
                if success:
                    final_path = msg
                    QMessageBox.information(self, "成功", f"全部完成！\n\n文本: {txt_path}\n文件: {final_path}")
                    self.accept()
                else:
                    QMessageBox.critical(self, "下载失败", f"文本已保存，但下载失败: {msg}")
            else:
                QMessageBox.critical(self, "错误", "无法保存文本文件。")
                
        except Exception as e:
            QMessageBox.critical(self, "异常", str(e))


class FileManagerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 说明区域
        label = QLabel("智能文件导入工具")
        label.setStyleSheet("font-size: 18px; font-weight: bold; margin-bottom: 10px;")
        layout.addWidget(label)
        
        info = QLabel(
            "功能说明：\n"
            "1. 从 Excel/Google Sheets 复制三个单元格 (文本1, 文本2, 驱动器链接)\n"
            "2. 点击下方按钮，粘贴内容\n"
            "3. 输入文件名，系统将自动拆分文本并下载文件"
        )
        info.setStyleSheet("color: #555; line-height: 1.5;")
        layout.addWidget(info)
        
        # 按钮
        layout.addStretch()
        
        btn_import = QPushButton("📋 打开智能导入窗口")
        btn_import.setMinimumHeight(50)
        btn_import.setStyleSheet("font-size: 16px; font-weight: bold; background-color: #0078d7; color: white; border-radius: 5px;")
        btn_import.clicked.connect(self.open_import_dialog)
        layout.addWidget(btn_import)
        
        layout.addStretch()
        
        # 当前路径显示
        path_layout = QHBoxLayout()
        path_layout.addWidget(QLabel("当前全局输出路径:"))
        self.path_label = QLineEdit()
        self.path_label.setReadOnly(True)
        self.update_default_path(self.config.get_global_output_dir())
        path_layout.addWidget(self.path_label)
        layout.addLayout(path_layout)
        
        self.setLayout(layout)

    def update_default_path(self, path):
        """主程序调用"""
        if path:
            self.path_label.setText(path)
        else:
            self.path_label.setText("未设置 (请在全局设置中选择)")

    def open_import_dialog(self):
        path = self.path_label.text()
        if not path or path.startswith("未设置"):
            QMessageBox.warning(self, "提示", "请先在上方【全局设置】中选择一个输出保存路径！")
            return
            
        dialog = SmartImportDialog(self, default_output_dir=path)
        dialog.exec()
