import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QPlainTextEdit, QMessageBox, QLineEdit, QDialog, QGroupBox
)
from .logic import FileManager

import os
from PyQt6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QMessageBox, QDialog, QGroupBox, QTableWidget, 
    QTableWidgetItem, QHeaderView, QApplication
)
from PyQt6.QtCore import Qt
from .logic import FileManager

class SmartImportDialog(QDialog):
    def __init__(self, parent=None, default_output_dir="", project_manager=None):
        super().__init__(parent)
        self.setWindowTitle("智能批量生成项目 (支持表格富文本复制)")
        self.resize(800, 600)
        self.output_dir = default_output_dir
        self.project_manager = project_manager
        self.parsed_data = [] # 存储字典列表
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        # 1. 操作区
        top_layout = QHBoxLayout()
        self.btn_read_clipboard = QPushButton("📋 从剪贴板读取表格数据 (自动解析超链接)")
        self.btn_read_clipboard.clicked.connect(self.read_from_clipboard)
        top_layout.addWidget(self.btn_read_clipboard)
        
        self.lbl_status = QLabel("等待读取剪贴板...")
        top_layout.addWidget(self.lbl_status)
        layout.addLayout(top_layout)

        # 2. 预览区
        self.preview_group = QGroupBox("数据预览 (请确认识别是否正确)")
        preview_layout = QVBoxLayout()
        
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["拟建项目文件夹名", "中文文案摘要", "西语文案摘要", "提取下载链接数"])
        self.table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.ResizeToContents)
        preview_layout.addWidget(self.table)
        
        self.preview_group.setLayout(preview_layout)
        layout.addWidget(self.preview_group)

        # 3. 底部按钮
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("✅ 确认无误，开始批量创建与下载")
        self.btn_save.setEnabled(False)
        self.btn_save.clicked.connect(self.run_import)
        
        btn_cancel = QPushButton("取消")
        btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addStretch()
        btn_layout.addWidget(btn_cancel)
        btn_layout.addWidget(self.btn_save)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def read_from_clipboard(self):
        clipboard = QApplication.clipboard()
        mime_data = clipboard.mimeData()
        
        if not mime_data.hasHtml():
            self.lbl_status.setText("❌ 剪贴板中没有找到富文本(HTML)表格数据！请直接从云端表格复制。")
            self.lbl_status.setStyleSheet("color: red;")
            return
            
        html_text = mime_data.html()
        self.parsed_data = FileManager.parse_clipboard_html(html_text)
        
        count = len(self.parsed_data)
        if count > 0:
            self.lbl_status.setText(f"✅ 成功解析 {count} 个项目！")
            self.lbl_status.setStyleSheet("color: green;")
            self.btn_save.setEnabled(True)
            self.update_table()
        else:
            self.lbl_status.setText("❌ 未能从表格中提取到有效数据，请检查复制的内容。")
            self.lbl_status.setStyleSheet("color: red;")
            self.btn_save.setEnabled(False)
            self.table.setRowCount(0)

    def update_table(self):
        self.table.setRowCount(len(self.parsed_data))
        for row, item in enumerate(self.parsed_data):
            # 文件夹名
            main = item.get('main_name', '')
            sub = item.get('sub_name', '')
            folder_name = f"{row+1:02d}_{main}-{sub}" if sub else f"{row+1:02d}_{main}"
            
            # 摘要
            cn_snippet = item.get('cn_text', '').replace('\n', ' ')[:30] + "..."
            es_snippet = item.get('es_text', '').replace('\n', ' ')[:30] + "..."
            link_count = str(len(item.get('links', [])))
            
            self.table.setItem(row, 0, QTableWidgetItem(folder_name))
            self.table.setItem(row, 1, QTableWidgetItem(cn_snippet))
            self.table.setItem(row, 2, QTableWidgetItem(es_snippet))
            
            link_item = QTableWidgetItem(link_count + " 个")
            link_item.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setItem(row, 3, link_item)

    def run_import(self):
        if not self.output_dir:
            QMessageBox.warning(self, "提示", "未设置全局输出目录！")
            return
            
        if not self.parsed_data:
            return

        self.btn_save.setEnabled(False)
        self.btn_read_clipboard.setEnabled(False)
        
        total = len(self.parsed_data)
        success_builds = 0
        total_downloads = 0
        success_downloads = 0
        
        # 计算已存在项目的最大序号
        start_index = 1
        if self.output_dir and os.path.exists(self.output_dir):
            import re
            existing_files = os.listdir(self.output_dir)
            max_idx = 0
            for f in existing_files:
                match = re.match(r'^(\d{2,})_', f)
                if match:
                    idx = int(match.group(1))
                    if idx > max_idx:
                        max_idx = idx
            start_index = max_idx + 1
        
        for i, item in enumerate(self.parsed_data):
            main_name = item.get('main_name', '未命名')
            self.lbl_status.setText(f"正在处理 {i+1}/{total}: {main_name} ...")
            QApplication.processEvents() # 防止界面假死
            
            # 1. 获取不冲突的基础文件名，基于已存在的最大序号递增
            base_name = FileManager.get_unique_base_name(self.output_dir, item, index=start_index + i)
            
            # 2. 合并写入文案到单 TXT
            ok, txt_path = FileManager.save_combined_text(self.output_dir, base_name, item)
            if ok:
                success_builds += 1
                if self.project_manager:
                     # 注册该基础文件名（无扩展名的纯项目名）
                     self.project_manager.add_project(base_name)
                
                # [更新] 西语字幕自动切片逻辑：将长段落切分为 3-4 词一行的短句，存入单独文件夹
                es_text = item.get('es_text', '')
                if es_text:
                    formatted_sub = FileManager.wrap_spanish_for_subtitles(es_text, words_per_line=4)
                    FileManager.save_subtitle_file(self.output_dir, base_name, formatted_sub)
                     
                # 3. 下载链接到全局目录
                links = item.get('links', [])
                
                for j, url in enumerate(links):
                    total_downloads += 1
                    self.lbl_status.setText(f"正在处理 {i+1}/{total}: 下载附件 {j+1}/{len(links)} ...")
                    QApplication.processEvents()
                    
                    # 附件跟随主文件名前缀
                    download_base_name = os.path.join(self.output_dir, f"{base_name}_附件_{j+1}")
                    dl_ok, _ = FileManager.download_file(url, download_base_name)
                    if dl_ok:
                        success_downloads += 1

        self.lbl_status.setText("✅ 批量处理完成！")
        QMessageBox.information(self, "完成", 
            f"处理完毕！\n成功建立 {success_builds}/{total} 个项目。\n共尝试下载 {total_downloads} 个链接，成功 {success_downloads} 个。")
            
        self.accept()
