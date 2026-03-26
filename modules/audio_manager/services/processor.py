import os
import subprocess
import tempfile
import wave
import numpy as np
import imageio_ffmpeg
from PyQt6.QtCore import QThread, pyqtSignal

# 尝试导入 MoviePy
try:
    from moviepy.editor import AudioFileClip
except ImportError:
    from moviepy.audio.io.AudioFileClip import AudioFileClip

class AudioUtils:
    @staticmethod
    def get_audio_info(file_path):
        if not os.path.exists(file_path): return None
        try:
            audio = AudioFileClip(file_path)
            info = {
                "channels": getattr(audio, 'nchannels', 2),
                "frame_rate": audio.fps,
                "duration_seconds": audio.duration,
            }
            audio.close()
            return info
        except:
            return None

class AudioSplitter:
    @staticmethod
    def find_best_cut_point(clip, search_start, search_end, fps=22050):
        try:
            if hasattr(clip, "subclipped"):
                 subclip = clip.subclipped(search_start, search_end)
            else:
                 subclip = clip.subclip(search_start, search_end)
            arr = subclip.to_soundarray(fps=fps)
        except Exception as e:
            print(f"Warning: Failed to analyze audio for silence: {e}")
            return search_end

        if len(arr) == 0:
            return search_end
            
        window_size = int(fps * 0.1)
        if window_size == 0: window_size = 1
        
        volumes = []
        timestamps = []
        
        for i in range(0, len(arr), window_size):
            chunk = arr[i:i+window_size]
            if len(chunk) == 0: continue
            rms = np.sqrt(np.mean(chunk**2))
            volumes.append(rms)
            timestamps.append(search_start + i / float(fps))
            
        if not volumes:
            return search_end

        volumes = np.array(volumes)
        timestamps = np.array(timestamps)
        
        min_vol = np.min(volumes)
        threshold = min_vol + 0.005
        
        candidates_indices = np.where(volumes <= threshold)[0]
        
        if len(candidates_indices) > 0:
            return timestamps[candidates_indices[-1]]
        else:
            return timestamps[np.argmin(volumes)]

    @staticmethod
    def split_audio(file_path, max_duration_sec=29.0, output_dir=None, mode="fixed", 
                    multiple_val=1, target_long_count=None, short_duration_sec=28.0,
                    min_duration_sec=5.0):
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件未找到: {file_path}")
            
        if output_dir is None:
            output_dir = os.path.dirname(file_path)

        audio = None
        try:
            audio = AudioFileClip(file_path)
            total_duration = audio.duration
            chunks_paths = []
            
            cut_points = [0.0]
            current_pos = 0.0
            long_count_generated = 0
            
            while current_pos < total_duration:
                remaining = total_duration - current_pos
                # 决定当前段的时长
                if target_long_count is not None and long_count_generated < target_long_count:
                    if remaining >= max_duration_sec:
                        current_target_dur = max_duration_sec
                        is_long = True
                    else:
                        current_target_dur = short_duration_sec
                        is_long = False
                else:
                    current_target_dur = short_duration_sec
                    is_long = False
                
                # 开始切分
                if remaining <= current_target_dur:
                    cut_points.append(total_duration)
                    if is_long and remaining >= (current_target_dur - 1.5):
                        long_count_generated += 1
                    break
                
                search_limit = current_pos + current_target_dur
                min_search_seg = min(10.0, current_target_dur * 0.5)
                search_start = max(current_pos + min_search_seg, search_limit - min_search_seg)
                search_end = search_limit
                
                best_cut = AudioSplitter.find_best_cut_point(audio, search_start, search_end)
                if best_cut - current_pos < min_search_seg:
                    best_cut = search_limit
                
                cut_points.append(best_cut)
                current_pos = best_cut
                if is_long: long_count_generated += 1

            # --- 优化：片段最小值重分配 (借时间) ---
            if len(cut_points) >= 3:
                last_dur = cut_points[-1] - cut_points[-2]
                if last_dur < min_duration_sec:
                    # 不直接合并，而是向上个片段“要”几秒钟，凑够最小值
                    new_pt = cut_points[-1] - min_duration_sec
                    # 确保重分配后，倒数第二个片段仍有意义 (> 5s 或 > min_duration/2)
                    if new_pt > cut_points[-3] + 5.0:
                        cut_points[-2] = new_pt
                    else:
                        # 如果上个片段太短给不起时间，则回退到合并模式
                        cut_points.pop(-2)
            elif len(cut_points) == 2:
                # 只有一个片段，即使短也没法借，只能保留
                pass

            # 写入文件
            base_name = os.path.splitext(os.path.basename(file_path))[0]
            ext = os.path.splitext(file_path)[1].replace('.', '')
            for i in range(len(cut_points) - 1):
                start_t = cut_points[i]
                end_t = cut_points[i+1]
                if end_t - start_t < 0.5: continue
                
                chunk_name = f"{base_name}_part{i+1}.{ext}"
                target_path = os.path.join(output_dir, chunk_name)
                
                if hasattr(audio, "subclipped"):
                     chunk = audio.subclipped(start_t, end_t)
                else:
                     chunk = audio.subclip(start_t, end_t)
                
                chunk.write_audiofile(target_path, codec=None, logger=None)
                chunks_paths.append(target_path)
                
            audio.close()
            return chunks_paths, long_count_generated
        except Exception as e:
            if audio: audio.close()
            raise RuntimeError(f"分割出错: {str(e)}")

class SmartBatchSplitWorker(QThread):
    progress_log = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, root_dir, target_58s, min_duration=5.0):
        super().__init__()
        self.root_dir = root_dir
        self.target_58s = target_58s
        self.min_duration = min_duration

    def run(self):
        try:
            if not os.path.exists(self.root_dir):
                self.error.emit("根目录不存在")
                return

            # 1. 扫描已有的 58s 片段
            out_dir = os.path.join(self.root_dir, "分段音频")
            if not os.path.exists(out_dir): os.makedirs(out_dir)
            
            existing_count = 0
            if os.path.exists(out_dir):
                for f in os.listdir(out_dir):
                    if "_part" in f.lower():
                        try:
                            f_path = os.path.join(out_dir, f)
                            import subprocess
                            cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "default=noprint_wrappers=1:nokey=1", f_path]
                            res = subprocess.run(cmd, capture_output=True, text=True, creationflags=0x08000000)
                            if res.returncode == 0:
                                dur = float(res.stdout.strip())
                                if 56.5 <= dur <= 59.5: 
                                    existing_count += 1
                        except:
                            pass

            self.progress_log.emit(f"📊 当前库中已存在约 {existing_count} 个 58s 片段。")
            total_58s_done = existing_count
            
            # 2. 扫描原始音频
            audio_exts = ('.mp3', '.wav', '.m4a')
            all_files = os.listdir(self.root_dir)
            files_to_process = []
            for f in all_files:
                if f.lower().endswith(audio_exts) and "_part" not in f.lower():
                    files_to_process.append(os.path.join(self.root_dir, f))

            if not files_to_process:
                self.finished.emit(f"未发现原始音频。目前已有 {existing_count} 个 58s。")
                return

            self.progress_log.emit(f"🚀 开始批量智能切割，目标 58s 总数: {self.target_58s} (片段≥{self.min_duration}s)...")
            
            for audio_path in files_to_process:
                needed = max(0, self.target_58s - total_58s_done)
                self.progress_log.emit(f"📦 处理: {os.path.basename(audio_path)} (补齐数: {needed})")
                
                _, long_gen = AudioSplitter.split_audio(
                    audio_path, 
                    max_duration_sec=58.0, 
                    output_dir=out_dir, 
                    target_long_count=needed,
                    short_duration_sec=28.0,
                    min_duration_sec=self.min_duration
                )
                total_58s_done += long_gen
                if long_gen > 0:
                    self.progress_log.emit(f"   生成 58s: {long_gen} 个 | 总进度: {total_58s_done}/{self.target_58s}")

            self.finished.emit(f"任务完成！库中目前共有约 {total_58s_done} 个 58s 片段。")

        except Exception as e:
            self.error.emit(f"智能切割异常: {str(e)}")

class AudioComparator:
    @staticmethod
    def get_head_signature(file_path, duration=5.0, fps=12000):
        if not os.path.exists(file_path): return None
        try:
            ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            fd, temp_wav = tempfile.mkstemp(suffix=".wav")
            os.close(fd) 
            try:
                cmd = [
                    ffmpeg_exe, "-y", "-i", file_path,
                    "-ss", "0", "-t", str(duration),
                    "-vn", "-acodec", "pcm_s16le",
                    "-ar", str(fps), "-ac", "1",
                    temp_wav
                ]
                creation_flags = 0
                if os.name == 'nt':
                     creation_flags = subprocess.CREATE_NO_WINDOW
                subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True, creationflags=creation_flags)
                
                with wave.open(temp_wav, 'rb') as wf:
                    raw_frames = wf.readframes(wf.getnframes())
                    arr = np.frombuffer(raw_frames, dtype=np.int16).astype(np.float32)
                
                if len(arr) == 0: return None
                
                # Create an audio energy/volume envelope (50ms windows)
                # This makes the signature incredibly robust to phase shifts and compression artifacts
                window_size = int(fps * 0.05) 
                if window_size == 0: window_size = 1
                
                num_windows = len(arr) // window_size
                if num_windows == 0: return None
                
                arr = arr[:num_windows * window_size].reshape(num_windows, window_size)
                # Compute RMS Volume for each window
                envelope = np.sqrt(np.mean(arr**2, axis=1))
                
                if np.std(envelope) < 1e-6: return None
                envelope = envelope - np.mean(envelope)
                norm = np.linalg.norm(envelope)
                if norm > 0: envelope = envelope / norm
                return envelope
            finally:
                if os.path.exists(temp_wav):
                    try: os.remove(temp_wav)
                    except: pass
        except:
            return None

    @staticmethod
    def find_best_match_from_db_cached(audio_head_sig, audio_duration, video_db):
        if audio_head_sig is None: return None
        best_match_name = None
        best_score = -1.0
        duration_tolerance = 60.0 
        len_aud = len(audio_head_sig)
        scan_step = 20 
        fps = 12000

        for item in video_db:
            if item.get('matched'): continue
            if abs(item['duration'] - audio_duration) > duration_tolerance: continue
            vid_sig = item.get('head_sig')
            if vid_sig is None: continue
            
            len_vid = len(vid_sig)
            if len_vid < len_aud:
                val_len = min(len_vid, len_aud)
                if val_len < 20: continue # need at least 1 second of envelope
                s1 = audio_head_sig[:val_len]
                s2 = vid_sig[:val_len]
                try: score = np.corrcoef(s1, s2)[0,1]
                except: score = 0.0
            else:
                max_offset_val = -1.0
                search_range = len_vid - len_aud
                
                if search_range <= 0:
                    try: 
                        max_offset_val = np.corrcoef(audio_head_sig, vid_sig[:len_aud])[0,1]
                    except: max_offset_val = 0.0
                else:
                    # Simple sliding window on the condensed envelope array is extremely fast
                    local_max = -1.0
                    for start_idx in range(search_range + 1):
                        v_slice = vid_sig[start_idx : start_idx + len_aud]
                        try:
                            # np.corrcoef is safe here since envelope array is tiny (~200 items)
                            s = np.corrcoef(audio_head_sig, v_slice)[0,1]
                            if s > local_max:
                                local_max = s
                        except:
                            continue
                    max_offset_val = local_max
                score = max_offset_val

            if score > best_score:
                best_score = score
                best_match_name = item['name']

        # 0.55 threshold handles volume envelope comparisons well
        if best_match_name and best_score > 0.55:
            return (best_match_name, best_score)
        return None

class SplitWorker(QThread):
    progress_log = pyqtSignal(str)
    finished = pyqtSignal()
    error = pyqtSignal(str)

    def __init__(self, file_paths, segment_length_sec, output_dir, mode="fixed", multiple_val=1):
        super().__init__()
        self.file_paths = file_paths
        self.segment_length_sec = segment_length_sec
        self.output_dir = output_dir
        self.mode = mode
        self.multiple_val = multiple_val

    def run(self):
        try:
            if self.output_dir and not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
            total = len(self.file_paths)
            for i, file_path in enumerate(self.file_paths):
                self.progress_log.emit(f"[{i+1}/{total}] 正在处理: {os.path.basename(file_path)} ...")
                result_paths = AudioSplitter.split_audio(
                    file_path, 
                    max_duration_sec=self.segment_length_sec, 
                    output_dir=self.output_dir,
                    mode=self.mode,
                    multiple_val=self.multiple_val
                )
                self.progress_log.emit(f"   > 完成。生成了 {len(result_paths)} 个片段。")
            self.finished.emit()
        except Exception as e:
            self.error.emit(str(e))

class MatchWorker(QThread):
    progress_log = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_dir, audio_dir, auto_rename):
        super().__init__()
        self.video_dir = video_dir
        self.audio_dir = audio_dir
        self.auto_rename = auto_rename

    def run(self):
        try:
            self.progress_log.emit("🔍 [Step 1] 扫描视频并预加载指纹...")
            video_files = [f for f in os.listdir(self.video_dir) 
                           if f.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', '.flv'))]
            if not video_files:
                self.finished.emit("❌ 视频文件夹为空！")
                return

            video_db = []
            total_vid = len(video_files)
            skipped_duplicates = 0
            for i, v_name in enumerate(video_files):
                if i % 5 == 0:
                     self.progress_log.emit(f"   ... 已索引 {i}/{total_vid} 个视频")
                v_path = os.path.join(self.video_dir, v_name)
                try:
                    info = AudioUtils.get_audio_info(v_path)
                    dur = info['duration_seconds'] if info else 0
                    if dur > 0:
                        # Extract 12 seconds instead of 7 to get more unique volume envelope
                        head_sig = AudioComparator.get_head_signature(v_path, duration=12.0)
                        if head_sig is None:
                            # 无法提取音频指纹的也算作有效条目，后续可能仍可用于时长粗匹配
                            video_db.append({'name': v_name, 'path': v_path, 'duration': dur, 'head_sig': head_sig, 'matched': False})
                            continue

                        # 检测并忽略与已存在条目几乎完全相同的“重复视频”
                        is_duplicate = False
                        for existing in video_db:
                            if existing.get('head_sig') is None:
                                continue
                            # 时长足够接近才认为可能是同一素材
                            if abs(existing['duration'] - dur) > 2.0:
                                continue
                            try:
                                l = min(len(existing['head_sig']), len(head_sig))
                                if l < 40:
                                    continue
                                score = np.corrcoef(existing['head_sig'][:l], head_sig[:l])[0,1]
                            except Exception:
                                score = 0.0
                            # 相关度非常高，视为同一素材的重复拷贝
                            if score > 0.97:
                                skipped_duplicates += 1
                                is_duplicate = True
                                break

                        if not is_duplicate:
                            video_db.append({'name': v_name, 'path': v_path, 'duration': dur, 'head_sig': head_sig, 'matched': False})
                except:
                    pass
            msg_suffix = f"，其中忽略了 {skipped_duplicates} 个重复视频" if skipped_duplicates > 0 else ""
            self.progress_log.emit(f"✅ 视频索引完成. 有效数据: {len(video_db)} 条{msg_suffix}")

            audio_files = [f for f in os.listdir(self.audio_dir) 
                          if f.lower().endswith(('.mp3', '.wav', '.ogg', '.flac', '.m4a'))]
            audio_files.sort()
            total_audio = len(audio_files)
            self.progress_log.emit(f"\n🔍 [Step 2] 开始匹配...")
            
            success_count = 0
            fail_list = []
            report_interval = max(1, total_audio // 20)
            
            for i, aud_name in enumerate(audio_files):
                aud_path = os.path.join(self.audio_dir, aud_name)
                if i % report_interval == 0:
                    self.progress_log.emit(f"   正在处理 {i+1}/{total_audio} ...")
                
                aud_info = AudioUtils.get_audio_info(aud_path)
                if not aud_info:
                    fail_list.append(f"{aud_name} (坏文件)")
                    continue
                aud_dur = aud_info['duration_seconds']
                aud_head_sig = AudioComparator.get_head_signature(aud_path, duration=8.0)
                if aud_head_sig is None:
                    fail_list.append(f"{aud_name} (静音/错误)")
                    continue
                    
                result = AudioComparator.find_best_match_from_db_cached(aud_head_sig, aud_dur, video_db)
                if result:
                    vid_name, score = result
                    self.progress_log.emit(f"   ✅ [匹配] {aud_name} == {vid_name} ({score:.3f})")
                    matched_item = next((v for v in video_db if v['name'] == vid_name), None)
                    if matched_item:
                        matched_item['matched'] = True
                        if self.auto_rename:
                            old_path = matched_item['path']
                            vid_ext = os.path.splitext(vid_name)[1]
                            aud_base = os.path.splitext(aud_name)[0]
                            new_name = f"{aud_base}{vid_ext}"
                            new_path = os.path.join(self.video_dir, new_name)
                            if os.path.normpath(old_path) != os.path.normpath(new_path):
                                try:
                                    if os.path.exists(new_path):
                                         counter = 1
                                         while True:
                                             root, ext = os.path.splitext(new_name)
                                             temp_name = f"{root}_{counter}{ext}"
                                             temp_path = os.path.join(self.video_dir, temp_name)
                                             if not os.path.exists(temp_path):
                                                 new_name = temp_name
                                                 new_path = temp_path
                                                 break
                                             counter += 1
                                    os.rename(old_path, new_path)
                                    matched_item['path'] = new_path
                                    matched_item['name'] = new_name
                                except Exception as e:
                                    self.progress_log.emit(f"      ❌ 重命名出错: {e}")
                    success_count += 1
                else:
                    # 获取一些失败原因
                    reason = "无匹配项"
                    # 这里我们可以对 db 做一个简单的二次扫描，看看是否有虽然落榜但分值最高的
                    best_fail_score = -1.0
                    for item in video_db:
                        if item.get('matched'): continue
                        dur_diff = abs(item['duration'] - aud_dur)
                        if dur_diff > 60.0: continue
                        # 简单计算一下分值 (不做滑动匹配，仅开头)
                        if item.get('head_sig') is not None:
                            v_sig = item['head_sig']
                            l = min(len(v_sig), len(aud_head_sig))
                            if l > 20:
                                try: sc = np.corrcoef(aud_head_sig[:l], v_sig[:l])[0,1]
                                except: sc = 0.0
                                if sc > best_fail_score: best_fail_score = sc
                    
                    if best_fail_score > 0:
                        reason = f"相似度低 (最高: {best_fail_score:.3f})"
                    else:
                        reason = f"时长不匹配或全部排除"
                    
                    self.progress_log.emit(f"      ❌ 未匹配: {aud_name} ({reason})")
                    fail_list.append(aud_name)
            
            unmatched_count = len(fail_list)
            summary = (
                "匹配完成！\n"
                f"总音频数: {total_audio}\n"
                f"成功匹配的音频数: {success_count}\n"
                f"未能匹配上的音频数: {unmatched_count}\n"
            )
            if unmatched_count == 0:
                summary += "\n✅ 所有音频都找到了对应的视频，声画已全部匹配成功。"
            else:
                summary += "❗ 有未匹配成功的音频，请查看日志中标记为“未匹配”的条目。"
            self.finished.emit(summary)
        except Exception as e:
            self.error.emit(str(e))

class AssembleWorker(QThread):
    progress_log = pyqtSignal(str)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_dir, output_dir):
        super().__init__()
        self.video_dir = video_dir
        self.output_dir = output_dir

    def run(self):
        try:
            self.progress_log.emit("🔍 [Step 1] 扫描视频文件夹...")
            
            # 扫描并过滤常见的视频格式
            files = [f for f in os.listdir(self.video_dir) 
                     if f.lower().endswith(('.mp4', '.mov', '.avi', '.mkv', '.flv'))]
            
            if not files:
                self.error.emit("❌ 文件夹中未找到支持的视频文件！")
                return
                
            # 排序（自然排序优先，这里简单使用按名称排序，前提是名称规则统一）
            files.sort()
            
            self.progress_log.emit(f"✅ 找到 {len(files)} 个视频文件:")
            for f in files:
                self.progress_log.emit(f"   - {f}")
                
            self.progress_log.emit("\n⚙️ [Step 2] 按原视频分组...")
            
            # Group files by base name (everything before '_part')
            import re
            groups = {}
            for f in files:
                # e.g. "Name_part1.mp4" -> match "Name"
                match = re.match(r"^(.*?)_part\d+\.(mp4|mov|avi|mkv|flv)$", f, re.IGNORECASE)
                if match:
                    base_name = match.group(1)
                else:
                    # Fallback if naming convention doesn't match perfectly
                    base_name = os.path.splitext(f)[0]
                
                if base_name not in groups:
                    groups[base_name] = []
                groups[base_name].append(f)
                
            self.progress_log.emit(f"✅ 分为 {len(groups)} 个组。")
            
            if not os.path.exists(self.output_dir):
                os.makedirs(self.output_dir)
                
            # Loop through each group and create separate concat processes
            success_count = 0
            for base_name, group_files in groups.items():
                if len(group_files) == 1:
                    self.progress_log.emit(f"⚠️ 跳过组 '{base_name}': 只有一个视频片段。")
                    continue
                    
                self.progress_log.emit(f"🚀 合并视频组: {base_name} ({len(group_files)} 个片段)...")
                
                # Sort the group carefully (handling numeric sorting for _part1, _part2, _part10 etc)
                def sort_key(filename):
                    match = re.search(r'_part(\d+)', filename, re.IGNORECASE)
                    return int(match.group(1)) if match else 0
                group_files.sort(key=sort_key)
                
                # create temp file
                fd, list_file_path = tempfile.mkstemp(suffix=".txt", text=True)
                with os.fdopen(fd, 'w', encoding='utf-8') as f:
                    for v_file in group_files:
                        safe_path = os.path.join(self.video_dir, v_file).replace("'", "'\\''")
                        safe_path = safe_path.replace("\\", "/")
                        f.write(f"file '{safe_path}'\n")
                        
                output_file = os.path.join(self.output_dir, f"{base_name}.mp4")
                    
                # 如果已存在，先删除或重命名
                if os.path.exists(output_file):
                    try:
                        os.remove(output_file)
                    except:
                        import time
                        output_file = os.path.join(self.output_dir, f"{base_name}_{int(time.time())}.mp4")
            
                # 获取 ffmpeg 可执行文件路径
                try:
                    local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__)), "ffmpeg.exe")
                    if os.path.exists(local_ffmpeg):
                        ffmpeg_exe = local_ffmpeg
                    else:
                        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
                except:
                    ffmpeg_exe = "ffmpeg"
                    
                cmd = [
                    ffmpeg_exe, "-y",
                    "-f", "concat",
                    "-safe", "0",
                    "-i", list_file_path,
                    "-c", "copy",
                    output_file
                ]
                
                creation_flags = 0
                if os.name == 'nt':
                     creation_flags = subprocess.CREATE_NO_WINDOW
                     
                process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    text=True,
                    creationflags=creation_flags,
                    encoding='utf-8',
                    errors='replace'
                )
                
                stdout, stderr = process.communicate()
                
                try:
                    os.remove(list_file_path)
                except:
                    pass
                    
                if process.returncode == 0:
                    success_count += 1
                    self.progress_log.emit(f"   -> 成功保存在: {output_file}")
                else:
                    self.progress_log.emit(f"⚠️ FFmpeg Error for {base_name}:\n{stderr}")
            
            if success_count > 0:
                self.progress_log.emit(f"\n🎉 [Step 3] 任务完成！成功合并了 {success_count} 个视频。")
                self.finished.emit(f"合并任务完成！\n成功输出了 {success_count} 个拼接好的视频，存放在半成品文件夹中。")
            else:
                self.error.emit(f"未能成功合并任何视频。")
                
        except Exception as e:
            self.error.emit(f"合并过程发生异常: {str(e)}")
