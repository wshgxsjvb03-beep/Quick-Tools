import os
import shutil
import subprocess
from PyQt6.QtCore import QThread, pyqtSignal

# 支持的压缩格式后缀
ARCHIVE_EXTS = ('.zip', '.7z', '.rar', '.tar', '.gz', '.bz2', '.xz', '.tar.gz', '.tar.bz2', '.tar.xz')

# 支持的视频格式后缀
VIDEO_EXTS = ('.mp4', '.mov', '.avi', '.mkv', '.ts', '.mts', '.wmv', '.flv', '.m4v', '.webm', '.rmvb')


class UnpackWorker(QThread):
    progress_log = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, archive_dir: str, seven_zip_path: str):
        super().__init__()
        self.archive_dir = archive_dir
        self.seven_zip_path = seven_zip_path

    def run(self):
        try:
            archive_dir = self.archive_dir
            seven_zip = self.seven_zip_path

            # ── Step 0: 验证 7z 可执行文件 ──
            if not os.path.isfile(seven_zip):
                self.error.emit(f"找不到 7z.exe：{seven_zip}\n请检查路径是否正确。")
                return

            # ── Step 1: 扫描压缩包 ──
            self.progress_log.emit("🔍 [Step 1] 扫描压缩包...")
            archives = [
                f for f in os.listdir(archive_dir)
                if f.lower().endswith(ARCHIVE_EXTS)
                and os.path.isfile(os.path.join(archive_dir, f))
            ]

            if not archives:
                self.error.emit("❌ 文件夹内没有找到任何压缩包！\n支持格式: .zip .7z .rar .tar .gz .bz2 .xz")
                return

            self.progress_log.emit(f"✅ 共找到 {len(archives)} 个压缩包。")

            # ── Step 2: 临时解压目录 ──
            tmp_dir = os.path.join(archive_dir, "_tmp_unpack")
            os.makedirs(tmp_dir, exist_ok=True)

            archived_dir = os.path.join(archive_dir, "_已解压")
            os.makedirs(archived_dir, exist_ok=True)

            total_videos = 0

            for idx, archive_name in enumerate(archives, 1):
                archive_path = os.path.join(archive_dir, archive_name)
                self.progress_log.emit(f"\n📦 [{idx}/{len(archives)}] 正在解压: {archive_name}")

                # 每个压缩包解到单独的子目录，防止互相干扰
                extract_sub = os.path.join(tmp_dir, f"pkg_{idx}")
                os.makedirs(extract_sub, exist_ok=True)

                # 调用 7z 解压
                cmd = [seven_zip, "x", archive_path, f"-o{extract_sub}", "-y"]
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace"
                )

                if result.returncode != 0:
                    self.progress_log.emit(f"  ⚠️ 解压失败 (返回码 {result.returncode})，跳过。")
                    self.progress_log.emit(f"  stderr: {result.stderr.strip()[:200]}")
                    continue

                # 递归找视频
                videos_found = []
                for root, dirs, files in os.walk(extract_sub):
                    for fname in files:
                        if fname.lower().endswith(VIDEO_EXTS):
                            videos_found.append(os.path.join(root, fname))

                self.progress_log.emit(f"  🎬 从压缩包中找到 {len(videos_found)} 个视频文件")

                # 平铺到 archive_dir 根目录，重名自动加序号
                for src_path in videos_found:
                    dest_name = os.path.basename(src_path)
                    dest_path = os.path.join(archive_dir, dest_name)
                    dest_path = self._safe_dest(dest_path)
                    shutil.move(src_path, dest_path)
                    self.progress_log.emit(f"  ✅ 移动: {os.path.basename(dest_path)}")
                    total_videos += 1

                # 移动压缩包到 _已解压/
                dest_archive = os.path.join(archived_dir, archive_name)
                if os.path.exists(dest_archive):
                    base, ext = os.path.splitext(archive_name)
                    dest_archive = self._safe_dest(dest_archive)
                shutil.move(archive_path, dest_archive)
                self.progress_log.emit(f"  📁 压缩包已移至 _已解压/")

            # ── Step 3: 清理临时目录 ──
            self.progress_log.emit("\n🧹 [Step 3] 清理临时目录...")
            try:
                shutil.rmtree(tmp_dir)
                self.progress_log.emit("  ✅ 临时目录已清理。")
            except Exception as e:
                self.progress_log.emit(f"  ⚠️ 清理临时目录时出错（可手动删除 _tmp_unpack）: {e}")

            self.progress_log.emit(f"\n🎉 全部完成！共提取 {total_videos} 个视频文件。")
            self.progress_log.emit(f"📂 视频已放置在: {archive_dir}")
            self.progress_log.emit(f"📁 压缩包已归档至: {archived_dir}")
            self.finished.emit(
                f"解包完成！\n共提取 {total_videos} 个视频文件。\n压缩包已移至 _已解压/ 文件夹。"
            )

        except Exception as e:
            self.error.emit(f"解包过程发生异常: {str(e)}")

    def _safe_dest(self, dest_path: str) -> str:
        """如果目标路径已存在，自动在文件名后加 _1, _2, ... 直到不重名。"""
        if not os.path.exists(dest_path):
            return dest_path
        base, ext = os.path.splitext(dest_path)
        counter = 1
        while True:
            candidate = f"{base}_{counter}{ext}"
            if not os.path.exists(candidate):
                return candidate
            counter += 1
