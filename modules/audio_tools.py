import os
import math
import numpy as np

# 尝试导入 MoviePy
try:
    # MoviePy v1.x
    from moviepy.editor import AudioFileClip
except ImportError:
    # MoviePy v2.x
    from moviepy.audio.io.AudioFileClip import AudioFileClip

class AudioSplitter:
    """
    [模块 1] 音频分割器
    职责: 仅负责音频的智能切割、分段导出。
    """
    
    @staticmethod
    def find_best_cut_point(clip, search_start, search_end, fps=22050):
        """在指定时间范围内寻找最佳切割点（音量最低点）。"""
        try:
            # 兼容 subclip/subclipped
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
            
        # 计算 RMS 音量
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
        
        # 找最低音量 + 严格阈值
        min_vol = np.min(volumes)
        threshold = min_vol + 0.005 # 绝对容差 0.005
        
        candidates_indices = np.where(volumes <= threshold)[0]
        
        if len(candidates_indices) > 0:
            return timestamps[candidates_indices[-1]]
        else:
            return timestamps[np.argmin(volumes)]

    @staticmethod
    def split_audio(file_path, max_duration_sec=29.0, output_dir=None):
        """智能切割音频流程"""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"文件未找到: {file_path}")
            
        if output_dir is None:
            output_dir = os.path.dirname(file_path)

        base_name = os.path.splitext(os.path.basename(file_path))[0]
        ext = os.path.splitext(file_path)[1].replace('.', '')
        
        audio = None
        try:
            audio = AudioFileClip(file_path)
            total_duration = audio.duration
            chunks_paths = []
            
            cut_points = [0.0]
            current_pos = 0.0
            
            print(f"Start analyzing: Duration={total_duration}s, Max Slice={max_duration_sec}s")
            
            while current_pos < total_duration:
                if total_duration - current_pos <= max_duration_sec:
                    cut_points.append(total_duration)
                    break
                
                search_limit = current_pos + max_duration_sec
                search_start = max(current_pos + 5, search_limit - 10)
                search_end = search_limit
                
                best_cut = AudioSplitter.find_best_cut_point(audio, search_start, search_end)
                
                if best_cut - current_pos < 5.0:
                    best_cut = search_limit
                
                cut_points.append(best_cut)
                current_pos = best_cut
            
            # 导出循环
            for i in range(len(cut_points) - 1):
                start_t = cut_points[i]
                end_t = cut_points[i+1]
                
                if end_t - start_t < 0.5: continue
                
                chunk_name = f"{base_name}_part{i+1}.{ext}"
                target_path = os.path.join(output_dir, chunk_name)
                
                print(f"Exporting Part {i+1}: {start_t:.2f}s -> {end_t:.2f}s")
                
                if hasattr(audio, "subclipped"):
                     chunk = audio.subclipped(start_t, end_t)
                else:
                     chunk = audio.subclip(start_t, end_t)
                
                chunk.write_audiofile(target_path, codec=None, logger=None)
                chunks_paths.append(target_path)
                
            audio.close()
            return chunks_paths

        except Exception as e:
            if audio: audio.close()
            import traceback
            traceback.print_exc()
            raise RuntimeError(f"分割出错: {str(e)}")


class AudioComparator:
    """
    [模块 2] 音频比对器 (待实现)
    职责: 负责因为的波形对比、相似度分析等。
    """
    
    @staticmethod
    def compare_files(file1, file2):
        # 预留接口
        pass


class AudioUtils:
    """
    [模块 3] 通用音频工具
    职责: 获取元数据、格式转换等通用操作。
    """
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
