import os
import re
from PyQt6.QtCore import QThread, pyqtSignal

class CheckerWorker(QThread):
    progress_log = pyqtSignal(str)
    finished = pyqtSignal(str, bool) # msg, is_success
    error = pyqtSignal(str)

    def __init__(self, audio_dir, video_dir, output_dir):
        super().__init__()
        self.audio_dir = audio_dir
        self.video_dir = video_dir
        self.output_dir = output_dir

    def run(self):
        try:
            self.progress_log.emit("🔍 [Step 1] 正在读取音频和视频目录...")
            
            # 支持扫描的文件后缀
            audio_exts = ('.mp3', '.wav', '.ogg', '.flac', '.m4a')
            video_exts = ('.mp4', '.mov', '.avi', '.mkv', '.flv')
            
            # 获取所有目标文件
            audio_files = [f for f in os.listdir(self.audio_dir) if f.lower().endswith(audio_exts)]
            video_files = [f for f in os.listdir(self.video_dir) if f.lower().endswith(video_exts)]
            
            if not audio_files:
                self.error.emit("❌ 基准音频文件夹为空！无法进行检查。")
                return
                
            self.progress_log.emit(f"✅ 找到 {len(audio_files)} 个音频基准文件，{len(video_files)} 个匹配视频文件。")
            self.progress_log.emit("\n⚙️ [Step 2] 开始交叉对比...")

            # 提取名字前缀 (去除后缀)
            def get_basename(filename):
                return os.path.splitext(filename)[0].lower()

            audio_basenames = {get_basename(f): f for f in audio_files}
            video_basenames = {get_basename(f) for f in video_files}
            
            missing_items = []
            matched_count = 0
            
            # 建立分组帮助排序展示错误
            grouped_missing = {}

            # 开始查缺
            for base_aud, full_aud_name in audio_basenames.items():
                if base_aud not in video_basenames:
                    missing_items.append(full_aud_name)
                    
                    # 尝试拆解分组 (例如 郑宇司机1_part2 -> 郑宇司机1 和 part2)
                    match = re.match(r"^(.*?)_part(\d+)$", base_aud, re.IGNORECASE)
                    if match:
                        group_name = match.group(1)
                        part_num = int(match.group(2))
                    else:
                        group_name = "未命名组"
                        part_num = base_aud
                        
                    if group_name not in grouped_missing:
                        grouped_missing[group_name] = []
                    grouped_missing[group_name].append(part_num)
                else:
                    matched_count += 1
            
            # 整理结果并准备日志
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                
            log_file_path = os.path.join(self.output_dir, "缺失片段检查报告.txt")
            
            if len(missing_items) == 0:
                self.progress_log.emit("\n🎉 [Step 3] 检查通过！")
                self.progress_log.emit(f"   -> 所有 {matched_count} 个基准音频节点都在视频文件夹中找到了对应的片段。")
                self.progress_log.emit("   -> 现在您可以放心地去 [拼接视频] 啦！")
                
                # 写个覆盖的好消息报告
                with open(log_file_path, 'w', encoding='utf-8') as f:
                    f.write("=== 视频片段完整性检查报告 ===\n")
                    f.write("检查结果：✅ 完美！没有任何缺失。\n")
                    f.write(f"共检查 {matched_count} 个对应片段，全部一致。\n")
                
                self.finished.emit("检查通过！无需补齐，可以直接拼接\n您可以去【半成品】目录查看完整报告文件。", True)
                
            else:
                self.progress_log.emit(f"\n⚠️ [Step 3] 发现缺失！共缺少 {len(missing_items)} 个片段。")
                
                # 写入持久化日志
                with open(log_file_path, 'w', encoding='utf-8') as f:
                    f.write("=== ⚠️ 视频片段缺失报告 ===\n")
                    f.write("这些基准音频未能找到对应的视频文件段，请手动修补或重新匹配：\n\n")
                    
                    for group_name, parts in grouped_missing.items():
                        parts.sort(key=lambda x: x if isinstance(x, int) else 0)
                        
                        part_strs = [f"part{p}" if isinstance(p, int) else str(p) for p in parts]
                        log_line = f"❌ [{group_name}] 组缺少: {', '.join(part_strs)}"
                        
                        self.progress_log.emit(f"   {log_line}")
                        f.write(log_line + "\n")
                        
                    f.write("\n===========================\n")
                    
                self.progress_log.emit(f"\n📝 详细缺失报告已永久保存至: {log_file_path}")
                self.finished.emit(f"发现 {len(missing_items)} 个缺失片段！\n请查看右侧详情或前往输出目录查看日志文件。", False)
                
        except Exception as e:
            self.error.emit(f"检查过程发生异常: {str(e)}")
