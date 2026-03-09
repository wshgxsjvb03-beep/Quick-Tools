import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QMessageBox, QLineEdit, QTextEdit
)
from ..services import CheckerWorker
from PyQt6.QtCore import pyqtSignal

class VideoCheckerWidget(QWidget):
    SUB_FOLDER_AUDIO = "分段音频"
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
            "💡 功能说明: \n"
            "在视频拼接之前，对比【基准分段音频】和【分段视频】文件夹，找出遗漏未匹配成功、缺失了的视频片段。\n"
            "即使您不小心关掉窗口，检查报告也会永久生成保存在输出目录的 txt 文件中。"
        )
        info_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # 音频目录选择 (基准)
        layout.addWidget(QLabel("📂 基准音频文件夹 (默认: 分段音频):"))
        h_aud = QHBoxLayout()
        self.audio_dir_edit = QLineEdit()
        h_aud.addWidget(self.audio_dir_edit)
        btn_aud = QPushButton("浏览...")
        btn_aud.clicked.connect(self.select_aud_dir)
        h_aud.addWidget(btn_aud)
        layout.addLayout(h_aud)
        
        # 视频目录选择 (基准)
        layout.addWidget(QLabel("🎬 目标视频文件夹 (默认: 分段视频):"))
        h_vid = QHBoxLayout()
        self.video_dir_edit = QLineEdit()
        h_vid.addWidget(self.video_dir_edit)
        btn_vid = QPushButton("浏览...")
        btn_vid.clicked.connect(self.select_vid_dir)
        h_vid.addWidget(btn_vid)
        layout.addLayout(h_vid)
        
        # 输出报告目录
        layout.addWidget(QLabel("📄 检查报告保存位置 (半成品):"))
        h_out = QHBoxLayout()
        self.output_dir_edit = QLineEdit()
        h_out.addWidget(self.output_dir_edit)
        btn_out = QPushButton("浏览...")
        btn_out.clicked.connect(self.select_out_dir)
        h_out.addWidget(btn_out)
        layout.addLayout(h_out)
        
        # 按钮
        self.run_btn = QPushButton("🔍 开始检测完整性")
        self.run_btn.setMinimumHeight(45)
        self.run_btn.clicked.connect(self.run_check)
        layout.addWidget(self.run_btn)
        
        # 日志
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)
        
    def select_aud_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择基准分段音频所在的文件夹")
        if d: 
            self.audio_dir_edit.setText(d)
            
    def select_vid_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择目标视频所在的文件夹")
        if d: 
            self.video_dir_edit.setText(d)
            
    def select_out_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择检查报告保存的文件夹")
        if d: 
            self.output_dir_edit.setText(d)
    
    def update_default_path(self, global_path):
        if global_path:
            audio_path = os.path.normpath(os.path.join(global_path, self.SUB_FOLDER_AUDIO))
            video_path = os.path.normpath(os.path.join(global_path, self.SUB_FOLDER_VIDEO))
            output_path = os.path.normpath(os.path.join(global_path, self.SUB_FOLDER_OUTPUT))
            
            self.audio_dir_edit.setText(audio_path)
            self.video_dir_edit.setText(video_path)
            self.output_dir_edit.setText(output_path)
            
    def run_check(self):
        audio_dir = self.audio_dir_edit.text().strip()
        video_dir = self.video_dir_edit.text().strip()
        output_dir = self.output_dir_edit.text().strip()
        
        if not audio_dir or not os.path.exists(audio_dir):
            QMessageBox.warning(self, "错误", "请选择有效的基准音频文件夹！")
            return
            
        if not video_dir or not os.path.exists(video_dir):
            QMessageBox.warning(self, "错误", "请选择有效的视频文件夹！\n如果为空请先进行音画匹配。")
            return
            
        if not output_dir:
            QMessageBox.warning(self, "错误", "请先在上方设置【全局输出路径】或手动指定报告位置！")
            return
            
        self.log_area.clear()
        self.run_btn.setEnabled(False)
        
        self.worker = CheckerWorker(audio_dir, video_dir, output_dir)
        self.worker.progress_log.connect(self.log_area.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
        
    def on_finished(self, msg, is_success):
        self.run_btn.setEnabled(True)
        if is_success:
            QMessageBox.information(self, "检查通过", msg)
            self.log_area.setStyleSheet("QTextEdit { color: green; }")
        else:
            QMessageBox.warning(self, "发现缺失", msg)
            self.log_area.setStyleSheet("QTextEdit { color: red; }")
            
        # 恢复默认字体颜色（对于新添加的内容）
        from PyQt6.QtGui import QTextCharFormat, QColor
        fmt = self.log_area.currentCharFormat()
        fmt.setForeground(QColor("black"))
        self.log_area.setCurrentCharFormat(fmt)

        
    def on_error(self, err_msg):
        self.run_btn.setEnabled(True)
        self.log_area.append(f"❌ 运行错误: {err_msg}")
