import os
import tempfile
import uuid
from PyQt6.QtCore import QThread, pyqtSignal
from PIL import Image, ImageDraw, ImageFont
import numpy as np

try:
    # MoviePy v1.x
    from moviepy.editor import (
        VideoFileClip, AudioFileClip,
        CompositeAudioClip, CompositeVideoClip, ImageClip
    )
    import moviepy.video.fx.all as vfx
    import moviepy.audio.fx.all as afx
except ImportError:
    # MoviePy v2.x
    from moviepy import (
        VideoFileClip, AudioFileClip,
        CompositeAudioClip, CompositeVideoClip, ImageClip
    )
    import moviepy.video.fx as vfx
    import moviepy.audio.fx as afx

class VideoStudioWorker(QThread):
    progress_log = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, params):
        super().__init__()
        self.params = params

    def create_signature_clip(self, text, duration, video_size):
        """由于 MoviePy TextClip 经常需要 ImageMagick，我们改用 Pillow 生成图片再导入"""
        try:
            # 1. 估算 Canvas 大小
            w, h = video_size
            font_size = int(h * 0.05) # 动态字体大小，约高度的 5%
            if font_size < 20: font_size = 20
            
            # 尝试加载中文字体，Windows 下常用黑体或微软雅黑
            font_paths = [
                "C:\\Windows\\Fonts\\msyh.ttc",   # 微软雅黑
                "C:\\Windows\\Fonts\\msyhl.ttc",  # 微软雅黑 Light
                "C:\\Windows\\Fonts\\simhei.ttf",  # 黑体
                "C:\\Windows\\Fonts\\simsun.ttc",  # 宋体
                "C:\\Windows\\Fonts\\arial.ttf",   # Arial
                "arial.ttf"                       # 兜底
            ]
            font = None
            for p in font_paths:
                if os.path.exists(p):
                    try:
                        font = ImageFont.truetype(p, font_size)
                        break
                    except: continue
            if not font: 
                try: font = ImageFont.load_default()
                except: font = None

            if not font:
                self.progress_log.emit("⚠️ 无法加载任何字体，署名可能无法显示。")
                return None

            # 2. 计算文本尺寸
            # 使用 getbbox 替代 getsize (Pillow 10.0+)
            dummy_img = Image.new("RGBA", (1, 1))
            draw = ImageDraw.Draw(dummy_img)
            bbox = draw.textbbox((0, 0), text, font=font)
            tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
            
            # 加一点内边距
            canvas_w, canvas_h = tw + 20, th + 20
            img = Image.new("RGBA", (canvas_w, canvas_h), (0, 0, 0, 0))
            draw = ImageDraw.Draw(img)
            
            # 画一个半透明深色背景（可选，为了看清文字）
            # draw.rectangle([0, 0, canvas_w, canvas_h], fill=(0, 0, 0, 80))
            
            # 画文字
            draw.text((10, 5), text, font=font, fill=(255, 255, 255, 200))
            
            # 3. 转换为 MoviePy ImageClip
            img_np = np.array(img)
            clip = ImageClip(img_np)
            if hasattr(clip, "with_duration"): clip = clip.with_duration(duration)
            else: clip = clip.set_duration(duration)
            
            # 4. 计算位置
            pos_map = {
                "右下角": ("right", "bottom"),
                "左下角": ("left", "bottom"),
                "右上角": ("right", "top"),
                "左上角": ("left", "top"),
                "居中": ("center", "center")
            }
            pos = pos_map.get(self.params.get("position"), ("right", "bottom"))
            
            # 留出边距 (15 像素)
            margin = 20
            final_pos = list(pos)
            if pos[0] == "right": final_pos[0] = w - canvas_w - margin
            if pos[0] == "left": final_pos[0] = margin
            if pos[1] == "bottom": final_pos[1] = h - canvas_h - margin
            if pos[1] == "top": final_pos[1] = margin
            
            if hasattr(clip, "with_position"): return clip.with_position(tuple(final_pos))
            else: return clip.set_position(tuple(final_pos))
        except Exception as e:
            self.progress_log.emit(f"⚠️ 署名生成失败: {e}")
            return None

    def run(self):
        video_paths = self.params.get("video_paths", [])
        output_dir = self.params.get("output_dir")
        
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            
        total = len(video_paths)
        success_count = 0
        
        for idx, video_path in enumerate(video_paths, 1):
            video = None
            try:
                self.progress_log.emit(f"\n🎞️ [{idx}/{total}] 正在加载视频: {os.path.basename(video_path)}")
                video = VideoFileClip(video_path)
                
                # --- 1. 调色处理 ---
                self.progress_log.emit("🎨 正在应用调色参数...")
                vid_effects = []
                
                brightness = self.params.get("brightness", 1.0)
                if brightness != 1.0:
                    if hasattr(vfx, "MultiplyColor"): vid_effects.append(vfx.MultiplyColor(brightness))
                    elif hasattr(vfx, "Colorx"): vid_effects.append(vfx.Colorx(brightness))
                    elif hasattr(vfx, "colorx"): video = video.fx(vfx.colorx, brightness) # Fallback for v1

                contrast = self.params.get("contrast", 1.0)
                saturation = self.params.get("saturation", 1.0)
                if contrast != 1.0 or saturation != 1.0:
                    if hasattr(vfx, "LumContrast"): vid_effects.append(vfx.LumContrast(contrast=contrast, lum=0))
                    elif hasattr(vfx, "lum_contrast"): video = video.fx(vfx.lum_contrast, contrast=contrast) # Fallback for v1

                if vid_effects and hasattr(video, "with_effects"):
                    video = video.with_effects(vid_effects)

                # --- 2. 署名处理 ---
                signature = self.params.get("signature")
                if signature:
                    self.progress_log.emit(f"🖋️ 正在添加署名: {signature}")
                    # 确保 duration 有效
                    dur = video.duration if video.duration else 1.0 
                    sign_clip = self.create_signature_clip(signature, dur, video.size)
                    if sign_clip:
                        # 明确指定 size 和 use_bgclip 以兼容 MoviePy v2
                        if hasattr(CompositeVideoClip, "__init__"):
                            video = CompositeVideoClip([video, sign_clip], size=video.size, use_bgclip=True)
                        else:
                            video = CompositeVideoClip([video, sign_clip])

                # --- 3. 背景音混音 ---
                bgm_path = self.params.get("bgm_path")
                if bgm_path and os.path.exists(bgm_path):
                    self.progress_log.emit("🎵 正在合成背景音乐...")
                    bgm = AudioFileClip(bgm_path)
                    
                    bgm_vol = self.params.get("bgm_volume", 0.2)
                    bgm_effects = []
                    
                    if hasattr(afx, "MultiplyVolume"): bgm_effects.append(afx.MultiplyVolume(bgm_vol))
                    elif hasattr(afx, "volumex"): bgm = bgm.fx(afx.volumex, bgm_vol) # Fallback for v1
                    elif hasattr(bgm, "volumex"): bgm = bgm.volumex(bgm_vol) # Fallback for v1 (method on clip)

                    if bgm.duration < video.duration:
                        if hasattr(afx, "AudioLoop"): bgm_effects.append(afx.AudioLoop(duration=video.duration))
                        elif hasattr(afx, "audio_loop"): bgm = bgm.fx(afx.audio_loop, duration=video.duration) # Fallback for v1
                    else:
                        if hasattr(bgm, "subclipped"): bgm = bgm.subclipped(0, video.duration)
                        else: bgm = bgm.subclip(0, video.duration)
                    
                    if bgm_effects and hasattr(bgm, "with_effects"):
                        bgm = bgm.with_effects(bgm_effects)
                    
                    if hasattr(video, "audio") and video.audio:
                        final_audio = CompositeAudioClip([video.audio, bgm])
                    else:
                        final_audio = bgm
                        
                    if hasattr(video, "with_audio"): video = video.with_audio(final_audio)
                    else: video = video.set_audio(final_audio)

                # --- 4. 生成输出 ---
                base_name = os.path.splitext(os.path.basename(video_path))[0]
                output_name = f"{base_name}_已编辑_{uuid.uuid4().hex[:4]}.mp4"
                output_path = os.path.join(output_dir, output_name)
                
                self.progress_log.emit(f"🚀 正在渲染并导出: {output_name}")
                
                # 画质参数
                crf = self.params.get("crf", 23)
                bitrate = self.params.get("bitrate")  # 如 "5000k" 或 "10M"
                preset = self.params.get("preset", "medium")
                
                write_kwargs = {
                    "codec": "libx264",
                    "audio_codec": "aac",
                    "temp_audiofile": "temp-audio.m4a",
                    "remove_temp": True,
                    "logger": None,
                    "threads": 4,
                    "preset": preset
                }
                
                # 如果指定了码率，则使用码率；否则使用 CRF
                if bitrate:
                    write_kwargs["bitrate"] = bitrate
                else:
                    write_kwargs["ffmpeg_params"] = ["-crf", str(crf)]
                
                # MoviePy v2 兼容性
                if hasattr(video, "fps") and video.fps:
                    write_kwargs["fps"] = video.fps
                elif not hasattr(video, "fps"):
                     write_kwargs["fps"] = 24 # 兜底
                
                video.write_videofile(output_path, **write_kwargs)
                success_count += 1
                
            except Exception as e:
                self.progress_log.emit(f"❌ 视频 {os.path.basename(video_path)} 处理失败: {str(e)}")
            finally:
                if video:
                    try: video.close()
                    except: pass
                    
        if success_count > 0:
            self.finished.emit(f"🎉 成功处理了 {success_count}/{total} 个视频！\n文件保存在:\n{output_dir}")
        else:
            self.error.emit(f"批量处理失败，没有视频成功完成。")
