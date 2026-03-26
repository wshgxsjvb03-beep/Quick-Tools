import os
import time
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QMessageBox, QAbstractItemView, QLineEdit, QTabWidget,
    QCheckBox, QComboBox, QTextEdit, QTableWidget, QTableWidgetItem, QHeaderView
)
from PyQt6.QtCore import Qt, QTimer

from ..services.elevenlabs import BearerTokenWorker, BearerQueryWorker
from ..dialogs import AudioItemDialog, BatchImportDialog
from ...history_manager import HistoryManager
from .generate_widget import CheckBoxHeader

class BearerTokenGenerateWidget(QWidget):
    SUB_FOLDER_NAME = "生成音频"
    
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.query_workers = [] # 保持强引用
        
        self.init_ui()
        self.load_tokens()
        self.load_tasks()
        
        # 启动定时器刷新倒计时
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_token_timers)
        self.timer.start(1000)
        
        # UI初始化完毕后自动查询一遍 Token 的余额
        QTimer.singleShot(500, self.refresh_all_tokens_balance)
        self.update_default_path(self.config.get_global_output_dir())

    def init_ui(self):
        layout = QVBoxLayout()
        
        # --- 1. Token 管理区 ---
        token_layout = QVBoxLayout()
        token_layout.addWidget(QLabel("🔑 Bearer Token 管理 (有效时长约1小时，从浏览器截取):"))
        
        input_layout = QHBoxLayout()
        self.token_input = QLineEdit()
        self.token_input.setPlaceholderText("粘贴 Bearer eyJhbGciOiJ... / 直接粘贴 eyJhbGciOiJ...")
        input_layout.addWidget(self.token_input)
        
        btn_add_token = QPushButton("➕ 添加 Token")
        btn_add_token.clicked.connect(self.add_token)
        input_layout.addWidget(btn_add_token)
        token_layout.addLayout(input_layout)
        
        self.token_table = QTableWidget(0, 4)
        self.token_table.setHorizontalHeaderLabels(["Token 末尾", "添加时间", "剩余时间", "可用余额"])
        self.token_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.token_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.token_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.token_table.setMaximumHeight(150)
        token_layout.addWidget(self.token_table)
        
        btn_del_token = QPushButton("🗑️ 删除选中的 Token")
        btn_del_token.clicked.connect(self.delete_selected_tokens)
        token_layout.addWidget(btn_del_token)
        
        layout.addLayout(token_layout)
        
        # 增加一点间距
        layout.addSpacing(10)

        # --- 2. 任务管理区 ---
        row1_layout = QHBoxLayout()
        row1_layout.addWidget(QLabel("📝 任务操作:"))
        btn_add = QPushButton("➕ 新建任务")
        btn_add.clicked.connect(self.add_new_task)
        row1_layout.addWidget(btn_add)
        
        btn_batch = QPushButton("🚀 批量导入")
        btn_batch.clicked.connect(self.batch_import_tasks)
        row1_layout.addWidget(btn_batch)
        
        row1_layout.addStretch()
        
        btn_delete = QPushButton("🗑️ 删除选中")
        btn_delete.clicked.connect(self.delete_selected_tasks)
        row1_layout.addWidget(btn_delete)
        
        btn_clear = QPushButton("🧹 清空列表")
        btn_clear.clicked.connect(self.clear_tasks)
        row1_layout.addWidget(btn_clear)
        layout.addLayout(row1_layout)

        # 任务列表表格
        self.task_table = QTableWidget(0, 4)
        
        # Set custom header
        self.header_checkbox = CheckBoxHeader(Qt.Orientation.Horizontal, self.task_table)
        self.header_checkbox.toggled.connect(self.set_all_checked)
        self.task_table.setHorizontalHeader(self.header_checkbox)

        self.task_table.setHorizontalHeaderLabels(["", "文件名", "文案内容", "Voice ID"])
        self.task_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)
        self.task_table.setColumnWidth(0, 40)
        self.task_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeMode.Stretch)
        self.task_table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.task_table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.task_table.doubleClicked.connect(self.edit_task)
        layout.addWidget(self.task_table)

        # --- 3. 输出设置区 ---
        out_layout = QHBoxLayout()
        out_layout.addWidget(QLabel("输出目录:"))
        self.out_edit = QLineEdit()
        out_layout.addWidget(self.out_edit)
        out_btn = QPushButton("浏览...")
        out_btn.clicked.connect(self.select_output_dir)
        out_layout.addWidget(out_btn)
        layout.addLayout(out_layout)

        # 批处理高级设置
        adv_settings = QHBoxLayout()
        self.chk_clear_out = QCheckBox("🚧 生成前清空输出文件夹 (慎选)")
        adv_settings.addWidget(self.chk_clear_out)
        layout.addLayout(adv_settings)

        # --- 4. 运行按钮与日志区 ---
        self.run_btn = QPushButton("🎤 启动 Bearer Token 轮询生成")
        self.run_btn.setMinimumHeight(45)
        self.run_btn.setStyleSheet("font-weight: bold; background-color: #9C27B0; color: white;")
        self.run_btn.clicked.connect(self.toggle_generation)
        layout.addWidget(self.run_btn)

        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        self.log_area.setMaximumHeight(150)
        layout.addWidget(self.log_area)
        
        self.setLayout(layout)

    def update_default_path(self, global_path):
        if global_path:
            full_path = os.path.normpath(os.path.join(global_path, self.SUB_FOLDER_NAME))
            self.out_edit.setText(full_path)
        else:
            self.out_edit.setText("")

    def select_output_dir(self):
        d = QFileDialog.getExistingDirectory(self, "选择输出目录")
        if d: self.out_edit.setText(d)

    # ---------------- Token 管理部分 ----------------

    def load_tokens(self):
        tokens = self.config.get_bearer_tokens()
        self.token_table.setRowCount(0)
        current_time = time.time()
        valid_tokens = []
        
        for t in tokens:
            # 过滤掉超过 1 小时 (3600秒) 的 Token
            if current_time - t.get("added_at", 0) < 3600:
                valid_tokens.append(t)
                self.insert_token_row(t)
        
        if len(valid_tokens) != len(tokens):
            self.config.set_bearer_tokens(valid_tokens)

    def insert_token_row(self, t_obj):
        row = self.token_table.rowCount()
        self.token_table.insertRow(row)
        
        token_str = t_obj.get("token", "")
        # 只显示最后 8 位
        display_tok = f"...{token_str[-8:]}" if len(token_str) > 8 else token_str
        
        time_str = time.strftime("%H:%M:%S", time.localtime(t_obj.get("added_at", 0)))
        
        item_tok = QTableWidgetItem(display_tok)
        item_tok.setData(Qt.ItemDataRole.UserRole, t_obj)
        self.token_table.setItem(row, 0, item_tok)
        
        self.token_table.setItem(row, 1, QTableWidgetItem(time_str))
        self.token_table.setItem(row, 2, QTableWidgetItem("计算中..."))
        self.token_table.setItem(row, 3, QTableWidgetItem(t_obj.get("balance", "未知")))

    def add_token(self):
        raw_text = self.token_input.text().strip()
        if not raw_text:
            return
            
        token = raw_text
        if raw_text.startswith("Bearer "):
            token = raw_text[7:].strip()
            
        if not token:
            return
            
        tokens = self.config.get_bearer_tokens()
        # 查重
        if any(t.get("token") == token for t in tokens):
            QMessageBox.information(self, "提示", "该 Token 已存在！")
            self.token_input.clear()
            return
            
        new_obj = {"token": token, "added_at": time.time(), "balance": "查询中..."}
        tokens.append(new_obj)
        self.config.set_bearer_tokens(tokens)
        self.insert_token_row(new_obj)
        self.token_input.clear()
        
        # 立即查询余额
        self.query_token_balance(token)

    def delete_selected_tokens(self):
        rows = sorted(list(set(index.row() for index in self.token_table.selectedIndexes())), reverse=True)
        if not rows:
            return
            
        tokens = self.config.get_bearer_tokens()
        for r in rows:
            t_obj = self.token_table.item(r, 0).data(Qt.ItemDataRole.UserRole)
            if t_obj in tokens:
                tokens.remove(t_obj)
            self.token_table.removeRow(r)
            
        self.config.set_bearer_tokens(tokens)

    def update_token_timers(self):
        # 每秒更新剩余时间，到期自动删除
        current_time = time.time()
        tokens = self.config.get_bearer_tokens()
        changed = False
        
        rows_to_delete = []
        for r in range(self.token_table.rowCount()):
            t_obj = self.token_table.item(r, 0).data(Qt.ItemDataRole.UserRole)
            elapsed = current_time - t_obj.get("added_at", 0)
            remains = 3600 - int(elapsed)
            
            if remains <= 0:
                rows_to_delete.append(r)
                if t_obj in tokens:
                    tokens.remove(t_obj)
                changed = True
            else:
                mins = remains // 60
                secs = remains % 60
                self.token_table.setItem(r, 2, QTableWidgetItem(f"{mins:02d}:{secs:02d}"))
                
        # 倒序删除过期的行
        for r in reversed(rows_to_delete):
            self.token_table.removeRow(r)
            
        if changed:
            self.config.set_bearer_tokens(tokens)

    def refresh_all_tokens_balance(self):
        tokens = self.config.get_bearer_tokens()
        for t in tokens:
            self.query_token_balance(t["token"])

    def query_token_balance(self, token):
        worker = BearerQueryWorker(token)
        worker.info_received.connect(self._on_balance_success)
        worker.error.connect(self._on_balance_error)
        self.query_workers.append(worker)
        worker.start()

    def _on_balance_success(self, token_str, info):
        # 查找到对应行更新UI和Config
        tokens = self.config.get_bearer_tokens()
        changed = False
        for i, t in enumerate(tokens):
            if t["token"] == token_str:
                t["balance"] = str(info["remaining"])
                changed = True
                break
                
        if changed:
            self.config.set_bearer_tokens(tokens)
            # Update UI
            for r in range(self.token_table.rowCount()):
                item = self.token_table.item(r, 0)
                if item and item.data(Qt.ItemDataRole.UserRole).get("token") == token_str:
                    item.setData(Qt.ItemDataRole.UserRole, tokens[i])
                    self.token_table.setItem(r, 3, QTableWidgetItem(tokens[i]["balance"]))
                    break

    def _on_balance_error(self, token_str, err_msg):
        # 查找到对应行更新为失效状态
        tokens = self.config.get_bearer_tokens()
        changed = False
        for i, t in enumerate(tokens):
            if t["token"] == token_str:
                t["balance"] = "失效/风控"
                changed = True
                break
                
        if changed:
            self.config.set_bearer_tokens(tokens)
            for r in range(self.token_table.rowCount()):
                item = self.token_table.item(r, 0)
                if item and item.data(Qt.ItemDataRole.UserRole).get("token") == token_str:
                    item.setData(Qt.ItemDataRole.UserRole, tokens[i])
                    self.token_table.setItem(r, 3, QTableWidgetItem(tokens[i]["balance"]))
                    break

    # ---------------- 任务管理部分 ----------------

    def load_tasks(self):
        tasks = self.config.get_audio_tasks(provider="BearerToken")
        self.task_table.setRowCount(0)
        for t in tasks:
            self.insert_task_row(self.task_table.rowCount(), t, is_checked=t.get('checked', True))
        
        if tasks:
            all_checked = all(t.get('checked', True) for t in tasks)
            self.header_checkbox.set_checked(all_checked)
        else:
            self.header_checkbox.set_checked(False)

    def save_all_tasks(self):
        tasks = []
        for r in range(self.task_table.rowCount()):
            chk_container = self.task_table.cellWidget(r, 0)
            checked = True
            if chk_container:
                chk = chk_container.findChild(QCheckBox)
                if chk: checked = chk.isChecked()
            
            original_data = self.task_table.item(r, 1).data(Qt.ItemDataRole.UserRole) or {}
            
            item_name = self.task_table.item(r, 1).text()
            item_content_obj = self.task_table.item(r, 2)
            full_content = item_content_obj.data(Qt.ItemDataRole.UserRole) if item_content_obj else ""
            if not full_content and item_content_obj:
                full_content = item_content_obj.text()
            
            task_data = original_data.copy()
            task_data.update({
                'name': item_name,
                'content': full_content,
                'voice_id': self.task_table.item(r, 3).text(),
                'checked': checked
            })
            tasks.append(task_data)
        
        self.config.set_audio_tasks(tasks, provider="BearerToken")

    def insert_task_row(self, row, data, is_checked=True):
        self.task_table.insertRow(row)
        
        chk_container = QWidget()
        chk_layout = QHBoxLayout(chk_container)
        chk = QCheckBox()
        chk.setChecked(is_checked)
        chk.stateChanged.connect(lambda: self.save_all_tasks())
        chk_layout.addWidget(chk)
        chk_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        chk_layout.setContentsMargins(0, 0, 0, 0)
        self.task_table.setCellWidget(row, 0, chk_container)

        name_item = QTableWidgetItem(data.get('name', ''))
        name_item.setData(Qt.ItemDataRole.UserRole, data)
        self.task_table.setItem(row, 1, name_item)

        content = data.get('content', '')
        short_content = content[:20] + "..." if len(content) > 20 else content
        item_content = QTableWidgetItem(short_content)
        item_content.setData(Qt.ItemDataRole.UserRole, content) 
        self.task_table.setItem(row, 2, item_content)
        self.task_table.setItem(row, 3, QTableWidgetItem(data.get('voice_id', '')))

    def add_new_task(self):
        dialog = AudioItemDialog(self.config, parent=self, provider="ElevenLabs")
        if dialog.exec():
            data = dialog.get_data()
            self.insert_task_row(self.task_table.rowCount(), data)
            self.save_all_tasks()

    def batch_import_tasks(self):
        dialog = BatchImportDialog(self)
        if dialog.exec():
            tasks, clear_existing = dialog.get_data()
            if clear_existing:
                self.task_table.setRowCount(0)
            
            for t in tasks:
                self.insert_task_row(self.task_table.rowCount(), t)
            self.save_all_tasks()

    def edit_task(self):
        row = self.task_table.currentRow()
        if row < 0: return
        
        data = self.task_table.item(row, 1).data(Qt.ItemDataRole.UserRole)
        if not data:
            data = {
                'name': self.task_table.item(row, 1).text(),
                'content': self.task_table.item(row, 2).data(Qt.ItemDataRole.UserRole) or self.task_table.item(row, 2).text(),
                'voice_id': self.task_table.item(row, 3).text()
            }
        
        dialog = AudioItemDialog(self.config, data=data, parent=self, provider="ElevenLabs")
        if dialog.exec():
            new_data = dialog.get_data()
            
            name_item = self.task_table.item(row, 1)
            name_item.setText(new_data['name'])
            name_item.setData(Qt.ItemDataRole.UserRole, new_data)
            
            self.task_table.item(row, 2).setText(new_data['content'][:20] + "...")
            self.task_table.item(row, 2).setData(Qt.ItemDataRole.UserRole, new_data['content'])
            self.task_table.item(row, 3).setText(new_data['voice_id'])
            
            self.save_all_tasks()

    def delete_selected_tasks(self):
        rows_to_delete = []
        for r in range(self.task_table.rowCount()):
            chk_container = self.task_table.cellWidget(r, 0)
            if chk_container:
                chk = chk_container.findChild(QCheckBox)
                if chk and chk.isChecked():
                    rows_to_delete.append(r)
        
        if not rows_to_delete:
            rows_to_delete = sorted(list(set(index.row() for index in self.task_table.selectedIndexes())), reverse=True)
        else:
            rows_to_delete.sort(reverse=True)

        if not rows_to_delete:
            return

        for r in rows_to_delete:
            self.task_table.removeRow(r)
        
        self.save_all_tasks()

    def clear_tasks(self):
        if self.task_table.rowCount() > 0:
            if QMessageBox.question(self, "确认", "确定清空所有任务吗？") == QMessageBox.StandardButton.Yes:
                self.task_table.setRowCount(0)
                self.save_all_tasks()

    def set_all_checked(self, checked):
        for r in range(self.task_table.rowCount()):
            chk_container = self.task_table.cellWidget(r, 0)
            if chk_container:
                chk = chk_container.findChild(QCheckBox)
                if chk: chk.setChecked(checked)
        self.header_checkbox.set_checked(checked)
        self.save_all_tasks()

    # ---------------- 运行逻辑部分 ----------------

    def toggle_generation(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.stop_generation()
        else:
            self.run_generation()

    def stop_generation(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.log_area.append("🛑 用户手动请求停止，正在中止当前生成并结束任务...")
            self.worker.requestInterruption()
        
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳ 正在停止...")

    def update_run_button_state(self, is_running=True):
        if is_running:
            self.run_btn.setText("🛑 停止生成")
            self.run_btn.setStyleSheet("font-weight: bold; background-color: #f44336; color: white;")
        else:
            self.run_btn.setText("🎤 启动 Bearer Token 轮询生成")
            self.run_btn.setStyleSheet("font-weight: bold; background-color: #9C27B0; color: white;")
        self.run_btn.setEnabled(True)

    def run_generation(self):
        # 1. 校验 Token
        tokens = self.config.get_bearer_tokens()
        valid_tokens = [t["token"] for t in tokens if t.get("balance") != "失效/风控"]
        if not valid_tokens:
            QMessageBox.warning(self, "提示", "列表中没有有效的 Bearer Token (请留意是否已过期或被风控)！")
            return
            
        # 2. 收集勾选任务
        row_count = self.task_table.rowCount()
        tasks_to_run = []
        self.process_mapping = {} # worker_index -> row_index
        
        for r in range(row_count):
            chk_container = self.task_table.cellWidget(r, 0)
            if chk_container:
                chk = chk_container.findChild(QCheckBox)
                if chk and chk.isChecked():
                    worker_idx = len(tasks_to_run)
                    self.process_mapping[worker_idx] = r
                    
                    data = self.task_table.item(r, 1).data(Qt.ItemDataRole.UserRole)
                    tasks_to_run.append({
                        'name': self.task_table.item(r, 1).text(),
                        'content': self.task_table.item(r, 2).data(Qt.ItemDataRole.UserRole),
                        'voice_id': self.task_table.item(r, 3).text(),
                    })
                    
        if not tasks_to_run:
            QMessageBox.warning(self, "提示", "请先在任务列表中勾选要处理的项目！")
            return
            
        output_dir = self.out_edit.text().strip()
        if not output_dir:
            QMessageBox.warning(self, "错误", "请指定输出目录！")
            return
            
        self.log_area.append(f"🚀 启动生成，将轮询 {len(valid_tokens)} 个 Token...")
        self.update_run_button_state(True)
        
        clear_out = self.chk_clear_out.isChecked()
        model_id = self.config.get_elevenlabs_model_id()
        default_voice_id = self.config.get_elevenlabs_voice_id()
        
        self.current_batch_tasks = tasks_to_run
        
        self.worker = BearerTokenWorker(
            tokens=valid_tokens,
            tasks=tasks_to_run,
            output_dir=output_dir,
            model_id=model_id,
            default_voice_id=default_voice_id,
            clear_output=clear_out
        )
        
        self.worker.progress_log.connect(self.log_area.append)
        self.worker.item_result.connect(self._on_item_result)
        self.worker.item_finished.connect(self._on_item_success)
        self.worker.fatal_error.connect(self._on_fatal_error)
        self.worker.finished.connect(self._on_worker_finished)
        
        self.worker.start()

    def _on_item_success(self, worker_idx):
        if hasattr(self, 'process_mapping') and worker_idx in self.process_mapping:
            row = self.process_mapping[worker_idx]
            chk_container = self.task_table.cellWidget(row, 0)
            if chk_container:
                chk = chk_container.findChild(QCheckBox)
                if chk: 
                    chk.setChecked(False) # 取消勾选，视作完成
                    self.save_all_tasks()

    def _on_item_result(self, worker_idx, success, error_msg):
        # 记录历史
        if hasattr(self, 'current_batch_tasks') and worker_idx < len(self.current_batch_tasks):
            task = self.current_batch_tasks[worker_idx]
            status = "success" if success else "failed"
            HistoryManager().add_record(
                name=task.get('name', 'unknown'),
                content=task.get('content', ''),
                voice_id=task.get('voice_id', ''),
                status=status,
                error_msg=error_msg
            )
            
            # 通知历史刷新
            from .history_widget import HistoryWidget
            parent = self.parentWidget()
            while parent and not isinstance(parent, QTabWidget):
                parent = parent.parentWidget()
            if parent:
                for i in range(parent.count()):
                    w = parent.widget(i)
                    if isinstance(w, HistoryWidget):
                        w.load_history()
                        break

    def _on_fatal_error(self, err_msg):
        self.update_run_button_state(False)
        QMessageBox.critical(self, "🚨 发生致命错误 (任务熔断)", f"已自动停止所有未完成的任务，原因：\n\n{err_msg}")
        # 触发全量查询刷新余额/状态，标记已死Token
        self.refresh_all_tokens_balance()

    def _on_worker_finished(self, msg):
        self.update_run_button_state(False)
        if "⏹" not in msg:  # User interrupted message shouldn't popup info
             QMessageBox.information(self, "完成", msg)
        self.refresh_all_tokens_balance()
