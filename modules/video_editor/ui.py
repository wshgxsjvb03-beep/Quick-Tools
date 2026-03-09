from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from modules.config_manager import ConfigManager
from modules.audio_manager.widgets import AssembleWidget
from .widgets import VideoCheckerWidget

class VideoEditorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        
        self.checker_widget = VideoCheckerWidget(self.config)
        self.tabs.addTab(self.checker_widget, "✅ 片段检测")

        self.assemble_widget = AssembleWidget(self.config)
        self.tabs.addTab(self.assemble_widget, "🧩 视频拼接")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def update_default_path(self, global_path):
        self.checker_widget.update_default_path(global_path)
        self.assemble_widget.update_default_path(global_path)
