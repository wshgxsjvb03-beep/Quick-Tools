import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QMessageBox, QLineEdit, QTextEdit
)
from ..services import AssembleWorker
from PyQt6.QtCore import pyqtSignal

class AssembleWidget(QWidget):
    SUB_FOLDER_VIDEO = "分段视频"
    SUB_FOLDER_OUTPUT = "半成品"

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.init_ui()
        if self.config:
            self.update_default_path(self.config.get_global_output_dir())
        
    def init_ui(self):
        layout = QVBoxLayout()
        
        # 说明
        info_label = QLabel(
            "💡 功能说明: 将文件夹中排好序的视频片段无损拼接为一个完整视频，完全保留原音质原画质。\n"
            "请确保此文件夹内的视频名字前缀带有数字或排列顺序正确（如 part1.mp4, part2.mp4）。\n"
            "输出文件将保存为 [全局路径/半成品]/合并输出.mp4"
        )
        info_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 视频目录选择
        layout.addWidget(QLabel("🎬 分段视频文件夹:"))
        h_dir = QHBoxLayout()
        self.video_dir_edit = QLineEdit()
        h_dir.addWidget(self.video_dir_edit)
        btn_dir = QPushButton("浏览...")
        btn_dir.clicked.connect(self.select_dir)
        h_dir.addWidget(btn_dir)
        layout.addLayout(h_dir)
        
        # 输出目录显示 (ReadOnly -> Editable with Browse)
        layout.addWidget(QLabel("📁 输出文件夹 (半成品):"))
        h_out = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        h_out.addWidget(self.output_dir_edit)
        btn_out = QPushButton("浏览...")
        btn_out.clicked.connect(self.select_output_dir)
        h_out.addWidget(btn_out)
        layout.addLayout(h_out)
        
        # 按钮
        self.run_btn = QPushButton("🚀 一键无损拼接视频")
        self.run_btn.setMinimumHeight(45)
        self.run_btn.clicked.connect(self.run_assemble)
        layout.addWidget(self.run_btn)
        
        # 日志
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
        
    def select_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择分段视频所在的文件夹")
        if d: 
            self.video_dir_edit.setText(d)
            
    def select_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出保存的文件夹")
        if d: 
            self.output_dir_edit.setText(d)
    
    def update_default_path(self, global_path):
        if global_path:
            video_path = os.path.normpath(os.path.join(global_path, self.SUB_FOLDER_VIDEO))
            output_path = os.path.normpath(os.path.join(global_path, self.SUB_FOLDER_OUTPUT))
            self.video_dir_edit.setText(video_path)
            self.output_dir_edit.setText(output_path)
            
    def run_assemble(self):
        video_dir = self.video_dir_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()
        
        if not video_dir or not os.path.exists(video_dir):
            QMessageBox.warning(self, "错误", "请选择有效的视频文件夹！")
            return
            
        if not output_dir:
            QMessageBox.warning(self, "错误", "请先在上方设置【全局输出路径】！")
            return
            
        self.log_area.clear()
        self.run_btn.setEnabled(False)
        
        self.worker = AssembleWorker(video_dir, output_dir)
        self.worker.progress_log.connect(self.log_area.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
        
    def on_finished(self, msg):
        self.run_btn.setEnabled(True)
        QMessageBox.information(self, "完成", msg)
        
    def on_error(self, err_msg):
        self.run_btn.setEnabled(True)
        self.log_area.append(f"❌ 错误: {err_msg}")
