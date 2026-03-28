import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QSpinBox, QGroupBox, QTextEdit, QMessageBox,
    QListWidget, QAbstractItemView, QLineEdit, QComboBox
)
from ..services import SplitWorker

class FileDropList(QListWidget):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
        self.setStyleSheet("border: 2px dashed #aaa; padding: 5px; background: #fafafa;")

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls(): event.accept()
        else: event.ignore()

    def dropEvent(self, event):
        files = [u.toLocalFile() for u in event.mimeData().urls()]
        for f in files:
            if os.path.exists(f) and f.lower().endswith(('.mp3', '.wav', '.ogg', '.flac')):
                items = [self.item(i).text() for i in range(self.count())]
                if f not in items:
                    self.addItem(f)
        event.accept()

class AudioSplitWidget(QWidget):
    SUB_FOLDER_NAME = "分段音频"

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()
        input_group = QGroupBox("1. 导入音频 (支持拖拽)")
        input_layout = QVBoxLayout()
        self.file_list = FileDropList()
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

        settings_group = QGroupBox("2. 分割设置")
        settings_layout = QVBoxLayout()
        
        mode_layout = QHBoxLayout()
        mode_layout.addWidget(QLabel("切割模式:"))
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["固定时长切割", "目标倍数切割"])
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        mode_layout.addWidget(self.mode_combo)
        settings_layout.addLayout(mode_layout)

        self.len_layout = QHBoxLayout()
        self.len_layout.addWidget(QLabel("限制时长 (秒):"))
        self.length_spin = QSpinBox()
        self.length_spin.setRange(5, 300)
        self.length_spin.setValue(29)
        self.len_layout.addWidget(self.length_spin)
        settings_layout.addLayout(self.len_layout)

        self.mul_layout = QHBoxLayout()
        self.mul_layout.addWidget(QLabel("目标倍数:"))
        self.multiple_spin = QSpinBox()
        self.multiple_spin.setRange(1, 100)
        self.multiple_spin.setValue(3)
        self.mul_layout.addWidget(self.multiple_spin)
        self.mul_layout.addWidget(QLabel("段 (按此倍数等分, 且不超过限制时长)"))
        settings_layout.addLayout(self.mul_layout)

        for i in range(self.mul_layout.count()):
            widget = self.mul_layout.itemAt(i).widget()
            if widget: widget.setVisible(False)

        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("输出目录:"))
        self.out_edit = QLineEdit()
        self.update_default_path(self.config.get_global_output_dir())
        out_layout.addWidget(self.out_edit)
        out_btn = QPushButton("浏览...")
        out_btn.clicked.connect(self.select_output_dir)
        out_layout.addWidget(out_btn)
        settings_layout.addLayout(out_layout)
        settings_group.setLayout(settings_layout)
        layout.addWidget(settings_group)
        
        self.split_btn = QPushButton("🚀 开始批量智能分割")
        self.split_btn.setMinimumHeight(40)
        self.split_btn.setStyleSheet("font-weight: bold; font-size: 14px;")
        self.split_btn.clicked.connect(self.run_batch_split)
        layout.addWidget(self.split_btn)
        
        layout.addWidget(QLabel("处理日志:"))
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        layout.addWidget(self.log_area)
        self.setLayout(layout)

    def update_default_path(self, global_path):
        if global_path:
            full_path = os.path.normpath(os.path.join(global_path, self.SUB_FOLDER_NAME))
            self.out_edit.setText(full_path)
        else:
            self.out_edit.setText("")

    def add_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择音频文件", "", "音频文件 (*.mp3 *.wav *.ogg *.flac)")
        for f in files:
            items = [self.file_list.item(i).text() for i in range(self.file_list.count())]
            if f not in items: self.file_list.addItem(f)

    def on_mode_changed(self, index):
        is_multiple = (index == 1)
        for i in range(self.mul_layout.count()):
            widget = self.mul_layout.itemAt(i).widget()
            if widget: widget.setVisible(is_multiple)

    def select_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d: self.out_edit.setText(d)

    def run_batch_split(self):
        count = self.file_list.count()
        if count == 0:
            QMessageBox.warning(self, "提示", "请先添加至少一个音频文件！")
            return
        file_paths = [self.file_list.item(i).text() for i in range(count)]
        sec_length = self.length_spin.value()
        output_dir = self.out_edit.text().strip() or None
        mode = "multiple" if self.mode_combo.currentIndex() == 1 else "fixed"
        multiple_val = self.multiple_spin.value()

        self.log_area.clear()
        self.split_btn.setEnabled(False)
        self.worker = SplitWorker(
            file_paths, sec_length, output_dir, 
            mode=mode, multiple_val=multiple_val, min_duration=10.0
        )
        self.worker.progress_log.connect(self.log_area.append)
        self.worker.finished.connect(lambda: [self.split_btn.setEnabled(True), QMessageBox.information(self, "完成", "任务已完成！")])
        self.worker.error.connect(lambda e: [self.split_btn.setEnabled(True), self.log_area.append(f"❌ 错误: {e}")])
        self.worker.start()
