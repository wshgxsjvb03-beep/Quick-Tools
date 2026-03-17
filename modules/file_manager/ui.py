import os
import sys
import re
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QMessageBox, QLineEdit, QSplitter, QListWidget, QListWidgetItem,
    QListView, QAbstractItemView, QFileDialog, QFrame, QStyle, QSizePolicy,
    QApplication, QMenu, QInputDialog
)
from PyQt6.QtCore import Qt, QDir, QSize
from PyQt6.QtGui import QAction, QFileSystemModel, QColor, QPalette, QIcon, QPixmap, QPainter
from modules.config_manager import ConfigManager
from .dialogs import SmartImportDialog
from .data import ProjectManager

# 紧凑样式表，加入圆点支持 + 暖米色卡片风格
STYLESHEET = """
/* 基础配色与字体：与全局暖米色主题一致 */
QWidget {
    background-color: #F7F3EC;
    font-family: 'Segoe UI', 'Microsoft YaHei', sans-serif;
    font-size: 13px;
    color: #3A3A2A;
}

/* 卡片容器：左右项目区/文件区 */
QFrame#card_frame {
    background-color: #FFFBF4;
    border: 1px solid #E3D9C9;
    border-radius: 14px;
}

/* 顶部标题 */
QLabel#title_label {
    font-size: 17px;
    font-weight: 600;
    color: #8A5B2E;
}

/* 区块标题条 */
QLabel#section_header {
    font-weight: 600;
    letter-spacing: 1px;
    color: #A88A5A;
    background-color: #F3E6D3;
    padding: 8px 12px;
    border-top-left-radius: 14px;
    border-top-right-radius: 14px;
}

/* 列表：项目列表 & 文件列表 */
QListWidget,
QListView {
    background-color: #FFFDF8;
    border: none;
    outline: none;
}

QListWidget::item,
QListView::item {
    padding: 4px 12px;
    margin: 2px 6px;
    border-radius: 10px;
    height: 30px;
}

QListWidget::item:selected,
QListView::item:selected {
    background-color: #F4E3C5;
    color: #8A5B2E;
    font-weight: 600;
}

QListWidget::item:hover,
QListView::item:hover {
    background-color: #F6EDDD;
}

/* 通用按钮：描边胶囊按钮 */
QPushButton {
    background-color: #FFFDF8;
    border: 1px solid #E0D2BE;
    border-radius: 18px;
    padding: 6px 18px;
    color: #5C4A32;
}

QPushButton:hover {
    background-color: #F4EBDE;
    border-color: #D5C4AE;
}

QPushButton:pressed {
    background-color: #E9DFC9;
}

QPushButton:disabled {
    background-color: #F3EEE5;
    color: #B9B1A4;
    border-color: #E3D8C9;
}

/* 主要操作按钮：实心暖色胶囊 */
QPushButton#btn_primary {
    background-color: #F1A94A;
    color: #4A310F;
    border: none;
    border-radius: 22px;
    padding: 8px 22px;
    font-weight: 600;
}

QPushButton#btn_primary:hover {
    background-color: #F7B963;
}

QPushButton#btn_primary:pressed {
    background-color: #E69834;
}

/* 文本输入框 */
QLineEdit {
    background-color: #FFFFFF;
    border: 1px solid #E1D5C4;
    border-radius: 10px;
    padding: 6px 10px;
}

QLineEdit:focus {
    border-color: #D1B585;
}

/* 分割条 */
QSplitter::handle {
    background-color: #E8DDCE;
}

QSplitter::handle:hover {
    background-color: #E0D1BF;
}

/* 右键菜单（项目菜单） */
QMenu {
    background-color: #FFFCF7;
    border: 1px solid #E3D4C1;
    border-radius: 10px;
    padding: 4px 0;
}

QMenu::item {
    padding: 6px 24px;
}

QMenu::item:selected {
    background-color: #F4E3C5;
    color: #8A5B2E;
}
"""

def create_dot_icon(color_str, size=16):
    """动态生成一个小圆点图标"""
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(color_str))
    painter.setPen(Qt.PenStyle.NoPen)
    # 画一个小圆
    margin = 4
    painter.drawEllipse(margin, margin, size - 2*margin, size - 2*margin)
    painter.end()
    return QIcon(pixmap)

class FileManagerUI(QWidget):
    def __init__(self):
        super().__init__()
        self.setStyleSheet(STYLESHEET)
        self.config = ConfigManager()
        self.current_root = self.config.get_global_output_dir()
        self.project_manager = ProjectManager(self.current_root)
        self.init_ui()

    def init_ui(self):
        self.main_layout = QVBoxLayout(self)
        self.main_layout.setContentsMargins(10, 10, 10, 10)
        self.main_layout.setSpacing(8)
        self.main_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        # 1. 顶部 Header
        header_widget = QWidget()
        header_layout = QVBoxLayout(header_widget)
        header_layout.setContentsMargins(5, 0, 5, 0)
        header_layout.setSpacing(5)
        
        title_label = QLabel("项目管理器 (Project Manager)")
        title_label.setObjectName("title_label")
        header_layout.addWidget(title_label)
        
        tool_row = QHBoxLayout()
        tool_row.addWidget(QLabel("存储路径:"))
        self.path_label = QLineEdit()
        self.path_label.setReadOnly(True)
        self.path_label.setText(self.current_root if self.current_root else "未设置")
        self.path_label.setFixedHeight(28)
        tool_row.addWidget(self.path_label)
        
        tool_row.addStretch()
        
        btn_import = QPushButton("➕ 新建导入 (Import)")
        btn_import.setObjectName("btn_primary")
        btn_import.setFixedHeight(30)
        btn_import.setCursor(Qt.CursorShape.PointingHandCursor)
        btn_import.clicked.connect(self.open_import_dialog)
        tool_row.addWidget(btn_import)
        
        header_layout.addLayout(tool_row)
        self.main_layout.addWidget(header_widget)
        
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("color: #EEE;")
        self.main_layout.addWidget(line)
        
        # 3. 主体区域
        self.splitter = QSplitter(Qt.Orientation.Horizontal)
        self.splitter.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        left_container = QFrame()
        left_container.setObjectName("card_frame")
        left_vbox = QVBoxLayout(left_container)
        left_vbox.setContentsMargins(0, 0, 0, 0)
        left_vbox.setSpacing(0)
        
        l_header = QLabel("项目列表")
        l_header.setObjectName("section_header")
        l_header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        left_vbox.addWidget(l_header)
        
        self.project_list = QListWidget()
        self.project_list.setIconSize(QSize(20, 20)) # 设置圆点图标大小
        self.project_list.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.project_list.itemClicked.connect(self.on_project_selected)
        self.project_list.itemDoubleClicked.connect(self.on_project_double_clicked)
        self.project_list.customContextMenuRequested.connect(self.on_project_context_menu)
        left_vbox.addWidget(self.project_list)
        
        right_container = QFrame()
        right_container.setObjectName("card_frame")
        right_vbox = QVBoxLayout(right_container)
        right_vbox.setContentsMargins(10, 10, 10, 10)
        
        r_toolbar = QHBoxLayout()
        self.lbl_current_project = QLabel("请选择项目...")
        self.lbl_current_project.setStyleSheet("font-weight: bold; color: #6C48B5;")
        r_toolbar.addWidget(self.lbl_current_project)
        r_toolbar.addStretch()
        
        self.btn_open_folder = QPushButton("📂 在文件夹中显示")
        self.btn_open_folder.setEnabled(False)
        self.btn_open_folder.clicked.connect(self.open_current_folder)
        r_toolbar.addWidget(self.btn_open_folder)
        right_vbox.addLayout(r_toolbar)
        
        self.file_model = QFileSystemModel()
        self.file_list = QListView()
        self.file_list.setModel(self.file_model)
        self.file_list.setViewMode(QListView.ViewMode.ListMode)
        self.file_list.setUniformItemSizes(True)
        self.file_list.setIconSize(QSize(24, 24))
        self.file_list.doubleClicked.connect(self.on_file_double_click)
        right_vbox.addWidget(self.file_list)
        
        self.splitter.addWidget(left_container)
        self.splitter.addWidget(right_container)
        self.splitter.setSizes([200, 700])
        
        self.main_layout.addWidget(self.splitter, 1)
        self.refresh_projects()

    def update_default_path(self, path):
        self.current_root = path
        self.path_label.setText(path if path else "未设置")
        self.project_manager.set_root_dir(path)
        self.refresh_projects()
        self.lbl_current_project.setText("请选择项目...")
        self.file_list.setRootIndex(self.file_model.index(""))
        self.btn_open_folder.setEnabled(False)

    def refresh_projects(self):
        self.project_list.clear()
        if not self.current_root or not os.path.exists(self.current_root):
            return
            
        projects = self.project_manager.get_projects()
        projects.sort(key=lambda x: x.get("updated_at", ""), reverse=True)
        
        # 扫描文件以确定状态
        all_files = os.listdir(self.current_root)
        
        for p in projects:
            name = p["name"]
            # 状态检测：文档(txt), 图片(jpg/png/jpeg), 音频(mp3/wav)
            has_txt = any(f.startswith(name) and f.lower().endswith('.txt') for f in all_files)
            has_img = any(f.startswith(name) and f.lower().endswith(('.jpg', '.png', '.jpeg')) for f in all_files)
            has_audio = any(f.startswith(name) and f.lower().endswith(('.mp3', '.wav')) for f in all_files)
            
            # 颜色判定
            status_color = "#FF4D4F" # 红色 (默认/仅文档)
            if has_txt and has_img and has_audio:
                status_color = "#52C41A" # 绿色 (全齐)
            elif has_txt and has_img:
                status_color = "#FAAD14" # 橙色 (文档+图片)
            
            item = QListWidgetItem(name)
            item.setIcon(create_dot_icon(status_color))
            self.project_list.addItem(item)

    def on_project_selected(self, item):
        name = item.text()
        self.lbl_current_project.setText(f"📋 {name}")
        if self.current_root:
            self.file_model.setRootPath(self.current_root)
            self.file_list.setRootIndex(self.file_model.index(self.current_root))
            self.file_model.setNameFilters([f"{name}*"])
            self.file_model.setNameFilterDisables(False)
            self.btn_open_folder.setEnabled(True)

    def on_project_double_clicked(self, item):
        """双击复制项目名称"""
        name = item.text()
        clipboard = QApplication.clipboard()
        clipboard.setText(name)
        # 可以在状态栏提示，但目前没有状态栏，直接复制即可

    def on_project_context_menu(self, pos):
        """项目右键菜单"""
        item = self.project_list.itemAt(pos)
        if not item:
            return

        menu = QMenu(self)
        rename_action = menu.addAction("✏️ 重命名 (Rename)")
        delete_action = menu.addAction("🗑️ 删除项目 (Delete)")
        
        # 样式微调
        menu.setStyleSheet("QMenu { padding: 5px; } QMenu::item { padding: 5px 20px; }")

        action = menu.exec(self.project_list.mapToGlobal(pos))
        
        if action == rename_action:
            self.rename_selected_project(item)
        elif action == delete_action:
            self.delete_selected_project(item)

    def rename_selected_project(self, item):
        old_name = item.text()
        new_name, ok = QInputDialog.getText(self, "重命名项目", f"请输入项目 '{old_name}' 的新名称:", text=old_name)
        
        if ok and new_name and new_name != old_name:
            success, msg = self.project_manager.rename_project(old_name, new_name)
            if success:
                self.refresh_projects()
                # 重新选择新命名的项目
                items = self.project_list.findItems(new_name, Qt.MatchFlag.MatchExactly)
                if items:
                    self.project_list.setCurrentItem(items[0])
                    self.on_project_selected(items[0])
            else:
                QMessageBox.critical(self, "错误", f"重命名失败: {msg}")

    def delete_selected_project(self, item):
        name = item.text()
        reply = QMessageBox.question(self, "确认删除", 
                                   f"确定要删除项目 '{name}' 及其所有关联文件吗？\n(操作不可撤销)",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        
        if reply == QMessageBox.StandardButton.Yes:
            success, msg = self.project_manager.delete_project(name)
            if success:
                self.refresh_projects()
                self.lbl_current_project.setText("请选择项目...")
                self.file_list.setRootIndex(self.file_model.index(""))
                self.btn_open_folder.setEnabled(False)
            else:
                QMessageBox.critical(self, "错误", f"删除失败: {msg}")

    def open_current_folder(self):
        if self.current_root:
            os.startfile(self.current_root)

    def on_file_double_click(self, index):
        path = self.file_model.filePath(index)
        if os.path.exists(path):
            os.startfile(path)

    def open_import_dialog(self):
        if not self.current_root:
            QMessageBox.warning(self, "提示", "请先配置输出目录")
            return
        dialog = SmartImportDialog(self, self.current_root, self.project_manager)
        if dialog.exec():
            self.refresh_projects()
