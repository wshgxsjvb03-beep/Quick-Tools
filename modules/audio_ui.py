import os
import sys
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QSpinBox, QGroupBox, QTextEdit, QMessageBox,
    QListWidget, QAbstractItemView, QLineEdit
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

# 解决导入路径问题
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(current_dir)
if project_root not in sys.path:
    sys.path.append(project_root)

from modules.audio_tools import AudioSplitter, AudioUtils
from modules.config_manager import ConfigManager

class FileDropList(QListWidget):
    """
    支持拖拽文件的列表控件
    """
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setStyleSheet("border: 2px dashed #aaa; padding: 5px; background: #fafafa;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            if os.path.exists(f) and f.lower().endswith(('.mp3', '.wav', '.ogg', '.flac')):
                # 避免重复添加
                items = [self.item(i).text() for i in range(self.count())]
                if f not in items:
                    self.addItem(f)
        event.accept()

class AudioWorker(QThread):
    """
    后台工作线程 - 支持批量处理
    """
    progress_log = pyqtSignal(str) # 实时日志
    finished = pyqtSignal()       # 全部完成
    error = pyqtSignal(str)       # 错误信息

    def __init__(self, file_paths, segment_length_sec, output_dir):
        super().__init__()
        self.file_paths = file_paths
        self.segment_length_sec = segment_length_sec
        self.output_dir = output_dir

    def run(self):
        try:
            # 确保输出目录存在
            if self.output_dir and not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            total = len(self.file_paths)
            for i, file_path in enumerate(self.file_paths):
                self.progress_log.emit(f"[{i+1}/{total}] 正在处理: {os.path.basename(file_path)} ...")
                
                result_paths = AudioSplitter.split_audio(
                    file_path, 
                    max_duration_sec=self.segment_length_sec, 
                    output_dir=self.output_dir
                )
                
                self.progress_log.emit(f"   > 完成。生成了 {len(result_paths)} 个片段。")
            
            self.finished.emit()
            
        except Exception as e:
            import traceback
            traceback.print_exc()
            self.error.emit(str(e))

class AudioUI(QWidget):
    SUB_FOLDER_NAME = "分段音频" # 定义专属子文件夹名称

    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # --- 第1部分: 批量文件选择 ---
        input_group = QGroupBox("1. 导入音频 (支持拖拽)")
        input_layout = QVBoxLayout()
        
        self.file_list = FileDropList()
        self.file_list.setToolTip("请将音频文件拖入此处，或者点击下方按钮添加")
        input_layout.addWidget(self.file_list)
        
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("添加文件...")
        add_btn.clicked.connect(self.add_files)
        clear_btn = QPushButton("清空列表")
        clear_btn.clicked.connect(self.file_list.clear)
        
        btn_layout.addWidget(add_btn)
        btn_layout.addWidget(clear_btn)
        input_layout.addLayout(btn_layout)
        
        input_group.setLayout(input_layout)
        layout.addWidget(input_group)

        # --- 第2部分: 设置 ---
        settings_group = QGroupBox("2. 分割设置")
        settings_layout = QVBoxLayout()
        
        # 长度设置
        len_layout = QHBoxLayout()
        len_layout.addWidget(QLabel("单个片段最大时长 (秒):"))
        self.length_spin = QSpinBox()
        self.length_spin.setRange(5, 300)
        self.length_spin.setValue(29)
        len_layout.addWidget(self.length_spin)
        settings_layout.addLayout(len_layout)
        
        # 输出路径设置
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("输出目录:"))
        self.out_edit = QLineEdit()
        
        # 读取全局配置并拼接子目录
        global_path = self.config.get_global_output_dir()
        self.update_default_path(global_path)
            
        out_layout.addWidget(self.out_edit)
        out_btn = QPushButton("浏览...")
        out_btn.clicked.connect(self.select_output_dir)
        out_layout.addWidget(out_btn)
        settings_layout.addLayout(out_layout)
        
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        # --- 第3部分: 操作 & 日志 ---
        action_layout = QHBoxLayout()
        self.split_btn = QPushButton("🚀 开始批量智能分割")
        self.split_btn.setMinimumHeight(40)
        self.split_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.split_btn.clicked.connect(self.run_batch_split)
        action_layout.addWidget(self.split_btn)
        layout.addLayout(action_layout)
        
        layout.addWidget(QLabel("处理日志:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)

        self.setLayout(layout)

    def update_default_path(self, global_path):
        """
        [接口] 被主程序调用，用于实时更新默认保存路径
        """
        if global_path:
            # 自动拼接: 总路径 + /分段音频
            full_path = os.path.join(global_path, self.SUB_FOLDER_NAME)
            # 规范化路径分隔符
            full_path = os.path.normpath(full_path)
            self.out_edit.setText(full_path)
        else:
            self.out_edit.setText("")
            self.out_edit.setPlaceholderText("留空则默认保存在原文件同级目录")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择音频文件", "", "音频文件 (*.mp3 *.wav *.ogg *.flac)"
        )
        for f in files:
            items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
            if f not in items:
                self.file_list.addItem(f)

    def select_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d:
            self.out_edit.setText(d)

    def run_batch_split(self):
        count = self.file_list.count()
        if count == 0:
            QMessageBox.warning(self, "提示", "请先添加至少一个音频文件！")
            return

        file_paths = [self.file_list.item(i).text() for i in range(count)]
        sec_length = self.length_spin.value()
        
        # 此时 output_dir 应该已经被 update_default_path 或 用户手动设置 填好了
        output_dir = self.out_edit.text().strip()
        if not output_dir:
            output_dir = None
        
        self.log_area.clear()
        self.log_area.append(f"🔥 开始处理 {count} 个文件...")
        self.log_area.append(f"👉 模式: 智能静音切割 (Max {sec_length}s)")
        if output_dir:
            self.log_area.append(f"📂 输出目录: {output_dir}")
            # [自动创建文件夹逻辑] 移到了 Worker 里面，防止界面卡顿
        else:
            self.log_area.append(f"📂 输出目录: [原文件所在目录]")
            
        self.split_btn.setEnabled(False)
        self.file_list.setEnabled(False)

        # 启动线程
        self.worker = AudioWorker(file_paths, sec_length, output_dir)
        self.worker.progress_log.connect(self.log_area.append)
        self.worker.finished.connect(self.on_batch_finished)
        self.worker.error.connect(self.on_batch_error)
        self.worker.start()

    def on_batch_finished(self):
        self.log_area.append("\n✅ 所有任务执行完毕！")
        self.split_btn.setEnabled(True)
        self.file_list.setEnabled(True)
        QMessageBox.information(self, "完成", "批量分割任务已完成！")

    def on_batch_error(self, err):
        self.log_area.append(f"\n❌ 发生错误: {err}")
        self.split_btn.setEnabled(True)
        self.file_list.setEnabled(True)
