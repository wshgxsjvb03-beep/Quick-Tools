import os
import re
import sys
import tempfile
import subprocess
import imageio_ffmpeg
from PyQt6.QtCore import QThread, pyqtSignal

class ScanWorker(QThread):
    """扫描并对比解析项目片段状态"""
    finished = pyqtSignal(list) # list of project dicts
    error = pyqtSignal(str)

    def __init__(self, audio_dir, video_dir):
        super().__init__()
        self.audio_dir = audio_dir
        self.video_dir = video_dir

    def run(self):
        try:
            if not os.path.exists(self.audio_dir) or not os.path.exists(self.video_dir):
                self.finished.emit([])
                return

            audio_exts = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
            video_exts = ('.mp4', '.mov', '.avi', '.mkv', '.flv')

            audio_files = [f for f in os.listdir(self.audio_dir) if f.lower().endswith(audio_exts)]
            video_files = [f for f in os.listdir(self.video_dir) if f.lower().endswith(video_exts)]

            def parse_info(filename):
                # e.g. "ProjectName_part1.mp3" -> ("ProjectName", 1)
                match = re.match(r"^(.*?)_part(\d+)$", os.path.splitext(filename)[0], re.IGNORECASE)
                if match:
                    return match.group(1), int(match.group(2))
                return os.path.splitext(filename)[0], 0

            projects = {}

            # 从音频建立预期
            for f in audio_files:
                p_name, part_num = parse_info(f)
                if p_name not in projects:
                    projects[p_name] = {"name": p_name, "expected": set(), "actual": set(), "all_video_files": []}
                projects[p_name]["expected"].add(part_num)

            # 填充视频现状
            for f in video_files:
                p_name, part_num = parse_info(f)
                if p_name in projects:
                    projects[p_name]["actual"].add(part_num)
                    projects[p_name]["all_video_files"].append(f)

            # 整理结果
            result = []
            for p_name, data in projects.items():
                expected = data["expected"]
                actual = data["actual"]
                missing = expected - actual
                
                # 排序视频片段
                def sort_key(filename):
                    _, num = parse_info(filename)
                    return num
                data["all_video_files"].sort(key=sort_key)

                result.append({
                    "name": p_name,
                    "is_complete": len(missing) == 0,
                    "missing_parts": sorted(list(missing)),
                    "total_expected": len(expected),
                    "found_actual": len(actual),
                    "video_files": data["all_video_files"]
                })

            # 按名称排序项目
            result.sort(key=lambda x: x["name"])
            self.finished.emit(result)

        except Exception as e:
            self.error.emit(str(e))

class MultiAssembleWorker(QThread):
    """支持批量或单个项目合并的任务"""
    progress_log = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_dir, output_dir, projects_to_merge):
        super().__init__()
        self.video_dir = video_dir
        self.output_dir = output_dir
        self.projects_to_merge = projects_to_merge # List of project dicts

    def run(self):
        try:
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)

            success_count = 0
            total = len(self.projects_to_merge)

            for i, proj in enumerate(self.projects_to_merge):
                name = proj["name"]
                files = proj["video_files"]

                if not files:
                    self.progress_log.emit(f"⚠️ [{i+1}/{total}] 项目 '{name}' 没有可合并的视频片段。")
                    continue

                if len(files) == 1:
                    # 如果只有一个片段，直接复制或提示？通常合并至少需要两个。
                    # 这里可以选择直接复制到输出目录并重命名。
                    self.progress_log.emit(f"ℹ️ [{i+1}/{total}] 项目 '{name}' 只有一个片段，直接复制...")
                    src = os.path.join(self.video_dir, files[0])
                    dst = os.path.join(self.output_dir, f"{name}{os.path.splitext(files[0])[1]}")
                    import shutil
                    shutil.copy2(src, dst)
                    success_count += 1
                    continue

                self.progress_log.emit(f"🚀 [{i+1}/{total}] 正在合并项目: {name} ({len(files)} 个片段)...")

                # 创建临时列表文件
                fd, list_file_path = tempfile.mkstemp(suffix=".txt", text=True)
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    for v_file in files:
                        safe_path = os.path.join(self.video_dir, v_file).replace("'", "'\\''")
                        safe_path = safe_path.replace("\\", "/")
                        f.write(f"file '{safe_path}'\n")

                output_file = os.path.join(self.output_dir, f"{name}.mp4")
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except:
                        import time
                        output_file = os.path.join(self.output_dir, f"{name}_{int(time.time())}.mp4")

                # 获取 ffmpeg
                try:
                    local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__)), "ffmpeg.exe")
                    ffmpeg_exe = local_ffmpeg if os.path.exists(local_ffmpeg) else imageio_ffmpeg.get_ffmpeg_exe()
                except:
                    ffmpeg_exe = "ffmpeg"

                cmd = [ffmpeg_exe, "-y", "-f", "concat", "-safe", "0", "-i", list_file_path, "-c", "copy", output_file]
                
                creation_flags = 0
                if os.name == 'nt': creation_flags = subprocess.CREATE_NO_WINDOW

                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, creationflags=creation_flags, encoding='utf-8', errors='replace')
                stdout, stderr = process.communicate()

                try: os.remove(list_file_path)
                except: pass

                if process.returncode == 0:
                    success_count += 1
                    self.progress_log.emit(f"   ✅ 完成: {os.path.basename(output_file)}")
                else:
                    self.progress_log.emit(f"   ❌ 失败 ({name}): {stderr}")

            self.finished.emit(f"任务完成！成功合并了 {success_count}/{total} 个项目。")

        except Exception as e:
            self.error.emit(f"合并过程发生异常: {str(e)}")
