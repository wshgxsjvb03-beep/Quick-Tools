from PyQt6.QtWidgets import QWidget, QVBoxLayout, QTabWidget
from modules.config_manager import ConfigManager
from .widgets import VideoUnpackWidget, VideoStudioWidget, VideoIntegratedWidget

class VideoEditorUI(QWidget):
    def __init__(self):
        super().__init__()
        self.config = ConfigManager()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        self.tabs = QTabWidget()
        
        # 集成检测与拼接
        self.integrated_widget = VideoIntegratedWidget(self.config)
        self.tabs.addTab(self.integrated_widget, "🧩 视频智能合并")

        self.unpack_widget = VideoUnpackWidget(self.config)
        self.tabs.addTab(self.unpack_widget, "📦 视频解包")

        self.studio_widget = VideoStudioWidget(self.config)
        self.tabs.addTab(self.studio_widget, "🎬 视频工作室")
        
        layout.addWidget(self.tabs)
        self.setLayout(layout)

    def update_default_path(self, global_path):
        self.integrated_widget.update_default_path(global_path)
        self.unpack_widget.update_default_path(global_path)
        self.studio_widget.update_default_path(global_path)
