import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QFileDialog, QMessageBox, QLineEdit, QTextEdit
)
from ..services import UnpackWorker

DEFAULT_7Z_PATH = r"C:\Program Files\7-Zip\7z.exe"
SUB_FOLDER_VIDEO = "分段视频"


class VideoUnpackWidget(QWidget):
    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.worker = None
        self.init_ui()
        if self.config:
            self.update_default_path(self.config.get_global_output_dir())

    def init_ui(self):
        layout = QVBoxLayout()

        # 说明
        info_label = QLabel(
            "💡 功能说明：\n"
            "批量解压指定文件夹内的压缩包，递归提取所有视频文件，"
            "平铺放置到同一文件夹根目录（自动处理重名）。\n"
            "解压完成后，原压缩包自动移入 _已解压/ 子文件夹归档。"
        )
        info_label.setStyleSheet("color: #666; font-style: italic; margin-bottom: 10px;")
        info_label.setWordWrap(True)
        layout.addWidget(info_label)

        # 压缩包所在文件夹
        layout.addWidget(QLabel("📂 压缩包所在文件夹（视频也会输出到此）:"))
        h_dir = QHBoxLayout()
        self.archive_dir_edit = QLineEdit()
        self.archive_dir_edit.setPlaceholderText("默认读取全局路径下的「分段视频」文件夹")
        h_dir.addWidget(self.archive_dir_edit)
        btn_dir = QPushButton("浏览...")
        btn_dir.clicked.connect(self.select_archive_dir)
        h_dir.addWidget(btn_dir)
        layout.addLayout(h_dir)

        # 7z 路径
        layout.addWidget(QLabel("🔧 7z.exe 路径:"))
        h_7z = QHBoxLayout()
        self.seven_zip_edit = QLineEdit()
        self.seven_zip_edit.setText(DEFAULT_7Z_PATH)
        h_7z.addWidget(self.seven_zip_edit)
        btn_7z = QPushButton("浏览...")
        btn_7z.clicked.connect(self.select_7z_path)
        h_7z.addWidget(btn_7z)
        layout.addLayout(h_7z)

        # 开始按钮
        self.run_btn = QPushButton("📦 开始解包")
        self.run_btn.setMinimumHeight(45)
        self.run_btn.clicked.connect(self.run_unpack)
        layout.addWidget(self.run_btn)

        # 日志区
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setPlaceholderText("操作日志将显示在这里...")
        layout.addWidget(self.log_area)

        self.setLayout(layout)

    def select_archive_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择压缩包所在文件夹")
        if d:
            self.archive_dir_edit.setText(d)

    def select_7z_path(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "选择 7z.exe",
            r"C:\Program Files\7-Zip",
            "可执行文件 (7z.exe)"
        )
        if path:
            self.seven_zip_edit.setText(path)

    def update_default_path(self, global_path):
        if global_path:
            video_path = os.path.normpath(os.path.join(global_path, SUB_FOLDER_VIDEO))
            self.archive_dir_edit.setText(video_path)

    def run_unpack(self):
        archive_dir = self.archive_dir_edit.text().strip()
        seven_zip = self.seven_zip_edit.text().strip()

        if not archive_dir or not os.path.isdir(archive_dir):
            QMessageBox.warning(self, "错误", "请选择有效的压缩包文件夹！")
            return

        if not seven_zip:
            QMessageBox.warning(self, "错误", "请填写 7z.exe 的路径！")
            return

        if not os.path.isfile(seven_zip):
            QMessageBox.warning(
                self, "找不到 7z.exe",
                f"路径不存在：\n{seven_zip}\n\n"
                "请安装 7-Zip（https://www.7-zip.org/）或手动指定正确路径。"
            )
            return

        self.log_area.clear()
        self.log_area.setStyleSheet("")
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳ 解包中...")

        self.worker = UnpackWorker(archive_dir, seven_zip)
        self.worker.progress_log.connect(self.log_area.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()

    def on_finished(self, msg):
        self._reset_btn()
        self.log_area.setStyleSheet("QTextEdit { color: green; }")
        QMessageBox.information(self, "解包完成", msg)

    def on_error(self, err_msg):
        self._reset_btn()
        self.log_area.append(f"\n❌ 错误: {err_msg}")
        self.log_area.setStyleSheet("QTextEdit { color: #cc3300; }")

    def _reset_btn(self):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("📦 开始解包")
