import os
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
    QFileDialog, QMessageBox, QLineEdit, QTextEdit, QSlider, QComboBox,
    QListWidget, QTabWidget, QListWidgetItem, QSizePolicy, QStyle, QStackedLayout
)
from PyQt6.QtCore import Qt, QUrl, QThread, pyqtSignal, QSize
from PyQt6.QtGui import QIcon, QImage, QPixmap
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from ..services.studio_worker import VideoStudioWorker

class ThumbnailWorker(QThread):
    finished_pixmap = pyqtSignal(str, object) # listWidgetItem path, QImage result

    def __init__(self, path):
        super().__init__()
        self.path = path

    def run(self):
        try:
            try:
                from moviepy.editor import VideoFileClip
            except ImportError:
                from moviepy import VideoFileClip
                
            import numpy as np
            clip = VideoFileClip(self.path)
            t = min(1.0, clip.duration / 2.0) if hasattr(clip, 'duration') and clip.duration else 0.0
            frame = clip.get_frame(t)
            clip.close()
            
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            frame_copy = np.ascontiguousarray(frame) # Avoid segfault when numpy array gets GC'd
            qimg = QImage(frame_copy.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            self.finished_pixmap.emit(self.path, qimg)
        except Exception as e:
            print(f"Failed generating thumbnail for {self.path}: {e}")

class PreviewWorker(QThread):
    finished_preview = pyqtSignal(object)
    
    def __init__(self, path, t_sec, params):
        super().__init__()
        self.path = path
        self.t_sec = t_sec
        self.params = params

    def run(self):
        try:
            try:
                from moviepy.editor import VideoFileClip
                import moviepy.video.fx.all as vfx
            except ImportError:
                from moviepy import VideoFileClip
                import moviepy.video.fx as vfx
                
            import numpy as np
            clip = VideoFileClip(self.path)
            t = min(self.t_sec, clip.duration if hasattr(clip, 'duration') and clip.duration else self.t_sec)
            
            vid_effects = []
            b = self.params.get("brightness", 1.0)
            if b != 1.0:
                if hasattr(vfx, "MultiplyColor"): vid_effects.append(vfx.MultiplyColor(b))
                elif hasattr(vfx, "Colorx"): vid_effects.append(vfx.Colorx(b))
                elif hasattr(vfx, "colorx"): clip = clip.fx(vfx.colorx, b)
                
            c = self.params.get("contrast", 1.0)
            s = self.params.get("saturation", 1.0)
            if c != 1.0 or s != 1.0:
                if hasattr(vfx, "LumContrast"): vid_effects.append(vfx.LumContrast(contrast=c, lum=0))
                elif hasattr(vfx, "lum_contrast"): clip = clip.fx(vfx.lum_contrast, contrast=c)
                
            if vid_effects and hasattr(clip, "with_effects"):
                clip = clip.with_effects(vid_effects)
                
            frame = clip.get_frame(t)
            clip.close()
            
            h, w, ch = frame.shape
            bytes_per_line = ch * w
            frame_copy = np.ascontiguousarray(frame)
            qimg = QImage(frame_copy.data, w, h, bytes_per_line, QImage.Format.Format_RGB888).copy()
            self.finished_preview.emit(qimg)
        except Exception as e:
            print("Preview error:", e)

class VideoStudioWidget(QWidget):
    SUB_FOLDER_OUTPUT = "视频工作室"

    def __init__(self, config=None):
        super().__init__()
        self.config = config
        self.thumb_workers = []
        self.init_ui()
        if self.config:
            self.update_default_path(self.config.get_global_output_dir())
            
    def closeEvent(self, event):
        if hasattr(self, 'media_player'):
            self.media_player.stop()
        super().closeEvent(event)
        
    def init_ui(self):
        main_layout = QHBoxLayout()
        
        # === Left Column: Video List ===
        left_layout = QVBoxLayout()
        left_layout.addWidget(QLabel("🎬 视频列表:"))
        
        btn_layout = QHBoxLayout()
        btn_add = QPushButton("导入多个视频...")
        btn_add.clicked.connect(self.select_videos)
        btn_clear = QPushButton("清空列表")
        btn_clear.clicked.connect(self.clear_videos)
        btn_layout.addWidget(btn_add)
        btn_layout.addWidget(btn_clear)
        left_layout.addLayout(btn_layout)
        
        self.video_list = QListWidget()
        self.video_list.setIconSize(QSize(90, 60))
        self.video_list.itemClicked.connect(self.on_video_selected)
        left_layout.addWidget(self.video_list)
        
        left_panel = QWidget()
        left_panel.setLayout(left_layout)
        main_layout.addWidget(left_panel, stretch=2)
        
        # === Middle Column: Preview ===
        mid_layout = QVBoxLayout()
        mid_layout.addWidget(QLabel("📺 视频预览:"))
        
        # Real Video Player setup with a stacked layout for overlay
        vid_stack = QWidget()
        stack_layout = QStackedLayout(vid_stack)
        stack_layout.setStackingMode(QStackedLayout.StackingMode.StackAll)
        
        self.video_widget = QVideoWidget()
        self.video_widget.setStyleSheet("background-color: black; border-radius: 5px;")
        self.video_widget.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        stack_layout.addWidget(self.video_widget)
        
        self.preview_overlay = QLabel()
        self.preview_overlay.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_overlay.hide()
        stack_layout.addWidget(self.preview_overlay)
        
        mid_layout.addWidget(vid_stack)
        
        self.media_player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.media_player.setAudioOutput(self.audio_output)
        self.media_player.setVideoOutput(self.video_widget)
        
        # Timeline and Play controls
        play_layout = QHBoxLayout()
        self.btn_play = QPushButton("▶ 播放")
        self.btn_play.setMinimumHeight(35)
        self.btn_play.clicked.connect(self.toggle_playback)
        play_layout.addWidget(self.btn_play)
        
        self.timeline_slider = QSlider(Qt.Orientation.Horizontal)
        self.timeline_slider.setRange(0, 0)
        self.timeline_slider.sliderMoved.connect(self.set_position)
        play_layout.addWidget(self.timeline_slider)
        
        self.time_label = QLabel("00:00 / 00:00")
        play_layout.addWidget(self.time_label)
        
        mid_layout.addLayout(play_layout)
        
        self.media_player.positionChanged.connect(self.position_changed)
        self.media_player.durationChanged.connect(self.duration_changed)
        self.media_player.playbackStateChanged.connect(self.playback_state_changed)
        
        mid_panel = QWidget()
        mid_panel.setLayout(mid_layout)
        main_layout.addWidget(mid_panel, stretch=5)
        
        # === Right Column: Parameters & Operations ===
        right_layout = QVBoxLayout()
        
        self.tabs = QTabWidget()
        
        # Tab 1: 署名及字幕 (Signature)
        tab_sign = QWidget()
        tab_sign_layout = QVBoxLayout()
        tab_sign_layout.addWidget(QLabel("🖋️ 署名设置:"))
        self.sign_text_edit = QLineEdit()
        self.sign_text_edit.setPlaceholderText("输入署名文本")
        tab_sign_layout.addWidget(self.sign_text_edit)
        
        tab_sign_layout.addWidget(QLabel("位置:"))
        self.sign_pos_combo = QComboBox()
        self.sign_pos_combo.addItems(["右下角", "左下角", "右上角", "左上角", "居中"])
        tab_sign_layout.addWidget(self.sign_pos_combo)
        tab_sign_layout.addStretch()
        tab_sign.setLayout(tab_sign_layout)
        
        # Tab 2: 调色 (Color)
        tab_color = QWidget()
        tab_color_layout = QVBoxLayout()
        
        def create_slider(label_txt, min_v, max_v, default_v, unit_div=100.0):
            layout = QHBoxLayout()
            layout.addWidget(QLabel(label_txt))
            slider = QSlider(Qt.Orientation.Horizontal)
            slider.setRange(min_v, max_v)
            slider.setValue(default_v)
            val_label = QLabel(str(default_v/unit_div))
            slider.valueChanged.connect(lambda v: val_label.setText(str(v/unit_div)))
            layout.addWidget(slider)
            layout.addWidget(val_label)
            return layout, slider
            
        bright_lyt, self.bright_slider = create_slider("亮度: ", 50, 150, 100)
        contrast_lyt, self.contrast_slider = create_slider("对比: ", 50, 150, 100)
        sat_lyt, self.sat_slider = create_slider("饱和: ", 0, 200, 100)
        
        self.bright_slider.sliderReleased.connect(self.request_preview)
        self.contrast_slider.sliderReleased.connect(self.request_preview)
        self.sat_slider.sliderReleased.connect(self.request_preview)
        
        tab_color_layout.addLayout(bright_lyt)
        tab_color_layout.addLayout(contrast_lyt)
        tab_color_layout.addLayout(sat_lyt)
        tab_color_layout.addStretch()
        tab_color.setLayout(tab_color_layout)
        
        # Tab 3: 背景音 (BGM)
        tab_bgm = QWidget()
        tab_bgm_layout = QVBoxLayout()
        tab_bgm_layout.addWidget(QLabel("🎵 背景音乐合成 (MP3):"))
        
        h_bgm = QHBoxLayout()
        self.bgm_path_edit = QLineEdit()
        h_bgm.addWidget(self.bgm_path_edit)
        btn_bgm = QPushButton("选择...")
        btn_bgm.clicked.connect(self.select_bgm)
        h_bgm.addWidget(btn_bgm)
        tab_bgm_layout.addLayout(h_bgm)
        
        bgm_vol_lyt, self.bgm_vol_slider = create_slider("背景音量: ", 1, 100, 20)
        tab_bgm_layout.addLayout(bgm_vol_lyt)
        tab_bgm_layout.addStretch()
        tab_bgm.setLayout(tab_bgm_layout)
        
        self.tabs.addTab(tab_sign, "字幕与水印")
        self.tabs.addTab(tab_color, "画面调色")
        self.tabs.addTab(tab_bgm, "背景音乐")
        
        # Tab 4: 输出设置 (Export Settings)
        tab_export = QWidget()
        tab_export_layout = QVBoxLayout()
        
        tab_export_layout.addWidget(QLabel("🎬 导出质量设置:"))
        
        h_quality = QHBoxLayout()
        h_quality.addWidget(QLabel("画质级别: "))
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["高 (推荐)", "中 (平衡)", "低 (较小体积)"])
        self.quality_combo.setCurrentIndex(0)
        h_quality.addWidget(self.quality_combo)
        tab_export_layout.addLayout(h_quality)
        
        h_preset = QHBoxLayout()
        h_preset.addWidget(QLabel("编码预设: "))
        self.preset_combo = QComboBox()
        self.preset_combo.addItems(["veryslow", "slower", "slow", "medium", "fast", "faster", "veryfast"])
        self.preset_combo.setCurrentText("medium")
        h_preset.addWidget(self.preset_combo)
        tab_export_layout.addLayout(h_preset)
        
        tab_export_layout.addWidget(QLabel("手动码率 (可选):"))
        self.bitrate_edit = QLineEdit()
        self.bitrate_edit.setPlaceholderText("例如: 10M, 5000k (留空则使用默认)")
        tab_export_layout.addWidget(self.bitrate_edit)
        
        tip_label = QLabel("💡 提示: CRF 越小质量越高。'高'对应 CRF 18，'中'对应 23。")
        tip_label.setStyleSheet("color: gray; font-size: 10px;")
        tab_export_layout.addWidget(tip_label)
        
        tab_export_layout.addStretch()
        tab_export.setLayout(tab_export_layout)
        self.tabs.addTab(tab_export, "输出设置")
        
        right_layout.addWidget(self.tabs)
        
        # 启动处理及日志
        self.run_btn = QPushButton("🚀 批量处理")
        self.run_btn.setMinimumHeight(45)
        self.run_btn.setStyleSheet("font-weight: bold;") 
        self.run_btn.clicked.connect(self.run_studio)
        right_layout.addWidget(self.run_btn)
        
        # Log Area
        self.log_area = QTextEdit()
        self.log_area.setReadOnly(True)
        right_layout.addWidget(self.log_area)
        
        right_panel = QWidget()
        right_panel.setLayout(right_layout)
        main_layout.addWidget(right_panel, stretch=3)
        
        self.setLayout(main_layout)

    def select_videos(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "选择多个视频文件", "", "Video Files (*.mp4 *.mov *.avi *.mkv)"
        )
        if files:
            for f in files:
                paths = [self.video_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.video_list.count())]
                if f not in paths:
                    item = QListWidgetItem(os.path.basename(f))
                    item.setData(Qt.ItemDataRole.UserRole, f)
                    
                    # set a default icon based on style (like a film icon)
                    default_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay)
                    item.setIcon(default_icon)
                    
                    self.video_list.addItem(item)
                    
                    # start thumbnail worker
                    worker = ThumbnailWorker(f)
                    worker.finished_pixmap.connect(self.on_thumbnail_ready)
                    self.thumb_workers.append(worker)
                    worker.start()
                    
    def on_thumbnail_ready(self, path, qimage):
        pixmap = QPixmap.fromImage(qimage).scaled(
            QSize(90, 60), 
            Qt.AspectRatioMode.KeepAspectRatioByExpanding, 
            Qt.TransformationMode.SmoothTransformation
        )
        # Find the item and update its icon
        for i in range(self.video_list.count()):
            item = self.video_list.item(i)
            if item.data(Qt.ItemDataRole.UserRole) == path:
                item.setIcon(QIcon(pixmap))
                break
                
    def clear_videos(self):
        self.video_list.clear()
        self.media_player.stop()
        self.media_player.setSource(QUrl())
        self.btn_play.setText("▶ 播放")
        self.time_label.setText("00:00 / 00:00")
        
    def on_video_selected(self, item):
        path = item.data(Qt.ItemDataRole.UserRole)
        self.current_video_path = path
        if os.path.exists(path):
            self.preview_overlay.hide()
            self.video_widget.show()
            self.media_player.setSource(QUrl.fromLocalFile(path))
            self.media_player.play()
            
    def toggle_playback(self):
        self.preview_overlay.hide()
        self.video_widget.show()
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
        else:
            self.media_player.play()
            
    def request_preview(self):
        if not hasattr(self, 'current_video_path') or not self.current_video_path:
            return
            
        if self.media_player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.media_player.pause()
            
        t_sec = self.media_player.position() / 1000.0
        params = {
            "brightness": self.bright_slider.value() / 100.0,
            "contrast": self.contrast_slider.value() / 100.0,
            "saturation": self.sat_slider.value() / 100.0,
        }
        
        self.preview_overlay.setText("生成预览中...")
        self.preview_overlay.setStyleSheet("background-color: black; color: white; border-radius: 5px;")
        self.video_widget.hide()
        self.preview_overlay.show()
        
        self.preview_worker = PreviewWorker(self.current_video_path, t_sec, params)
        self.preview_worker.finished_preview.connect(self.on_preview_ready)
        self.preview_worker.start()
        
    def on_preview_ready(self, qimage):
        if not qimage.isNull():
            pixmap = QPixmap.fromImage(qimage).scaled(
                self.video_widget.size(),
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation
            )
            self.preview_overlay.setPixmap(pixmap)
            self.preview_overlay.setStyleSheet("background-color: black; border-radius: 5px;")
            self.video_widget.hide()
            self.preview_overlay.show()
        else:
            self.preview_overlay.hide()
            self.video_widget.show()
            
    def playback_state_changed(self, state):
        if state == QMediaPlayer.PlaybackState.PlayingState:
            self.btn_play.setText("⏸ 暂停")
        else:
            self.btn_play.setText("▶ 播放")
            
    def position_changed(self, position):
        self.timeline_slider.setValue(position)
        self.update_time_label()

    def duration_changed(self, duration):
        self.timeline_slider.setRange(0, duration)
        self.update_time_label()

    def set_position(self, position):
        self.media_player.setPosition(position)
        
    def update_time_label(self):
        def format_ms(ms):
            s = ms // 1000
            mins = s // 60
            secs = s % 60
            return f"{mins:02d}:{secs:02d}"
        pos = self.media_player.position()
        dur = self.media_player.duration()
        self.time_label.setText(f"{format_ms(pos)} / {format_ms(dur)}")
            
    def select_bgm(self):
        f, _ = QFileDialog.getOpenFileName(self, "选择背景音乐", "", "Audio Files (*.mp3 *.wav *.m4a)")
        if f: self.bgm_path_edit.setText(f)

    def update_default_path(self, global_path):
        if global_path:
            self.output_dir = os.path.normpath(os.path.join(global_path, self.SUB_FOLDER_OUTPUT))
        else:
            self.output_dir = ""

    def run_studio(self):
        video_paths = [self.video_list.item(i).data(Qt.ItemDataRole.UserRole) for i in range(self.video_list.count())]
        
        if not video_paths:
            QMessageBox.warning(self, "错误", "请先在左侧列表中导入视频文件！")
            return
            
        for vp in video_paths:
            if not os.path.exists(vp):
                QMessageBox.warning(self, "错误", f"路径不存在或已失效：\n{vp}")
                return
            
        if not self.output_dir:
            QMessageBox.warning(self, "错误", "请先在主界面上方设置【全局输出路径】！")
            return
            
        # 映射画质到 CRF
        quality_map = {0: 18, 1: 23, 2: 28}
        crf = quality_map.get(self.quality_combo.currentIndex(), 23)
        
        params = {
            "video_paths": video_paths,
            "signature": self.sign_text_edit.text().strip(),
            "position": self.sign_pos_combo.currentText(),
            "brightness": self.bright_slider.value() / 100.0,
            "contrast": self.contrast_slider.value() / 100.0,
            "saturation": self.sat_slider.value() / 100.0,
            "bgm_path": self.bgm_path_edit.text().strip(),
            "bgm_volume": self.bgm_vol_slider.value() / 100.0,
            "output_dir": self.output_dir,
            "crf": crf,
            "preset": self.preset_combo.currentText(),
            "bitrate": self.bitrate_edit.text().strip() or None
        }
        
        self.log_area.clear()
        self.run_btn.setEnabled(False)
        self.run_btn.setText("⏳ 批量处理中...")
        
        self.worker = VideoStudioWorker(params)
        self.worker.progress_log.connect(self.log_area.append)
        self.worker.finished.connect(self.on_finished)
        self.worker.error.connect(self.on_error)
        self.worker.start()
        
    def on_finished(self, msg):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("🚀 批量处理")
        QMessageBox.information(self, "完成", msg)
        
    def on_error(self, err_msg):
        self.run_btn.setEnabled(True)
        self.run_btn.setText("🚀 批量处理")
        self.log_area.append(f"❌ 错误: {err_msg}")
        QMessageBox.critical(self, "错误", f"处理视频时发生错误:\n{err_msg}")
