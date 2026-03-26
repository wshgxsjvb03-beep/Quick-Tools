import os
import requests
import re
import datetime
import json
import sys
import subprocess
import tempfile
from bs4 import BeautifulSoup
from PyQt6.QtCore import QThread, pyqtSignal
try:
    import imageio_ffmpeg
except:
    pass

class FileManager:
    @staticmethod
    def parse_clipboard_html(html_text):
        """
        从剪贴板的 HTML 内容中解析表格数据。
        提取列：
        0: 项目名 (主)
        3: 中文
        4: 西班牙语 (会进行清理)
        5: 图片 (提取所有 <a>)
        6: 备注/副标题 (提取文字作为副标，提取所有 <a> 供下载)
        
        返回: list of dicts
        """
        results = []
        if not html_text:
            return results

        try:
            soup = BeautifulSoup(html_text, 'html.parser')
            # 找到所有的 tr 行
            rows = soup.find_all('tr')
            
            for row in rows:
                cols = row.find_all(['td', 'th'])
                if len(cols) < 7: # 至少需要7列
                    continue
                    
                # 第一列：项目主名
                main_name = cols[0].get_text(strip=True)
                
                # 第四列：中文文案 (保留原貌不处理)
                cn_text = FileManager._extract_text_with_newlines(cols[3])
                
                # 第五列：西班牙语文案 (仅对外语执行高级符号清理和数字归一化)
                es_text_raw = FileManager._extract_text_with_newlines(cols[4])
                es_text = FileManager.clean_special_symbols(es_text_raw)
                
                # 第六、七列 (索引为5和6) 提取链接与副标题
                links = []
                # 先提取链接 (包含 <a> 标签的，以及纯文本里的网址)
                for idx in [5, 6]:
                    # 1. HTML <a> 标签
                    a_tags = cols[idx].find_all('a')
                    for a in a_tags:
                        href = a.get('href')
                        if href and href.startswith('http') and href not in links:
                            links.append(href)
                            
                    # 2. 纯文本网址 (如果 Google 表格只是一串文字 没有超链接格式)
                    raw_text = cols[idx].get_text(separator=' ')
                    urls = re.findall(r'(https?://[^\s]+)', raw_text)
                    for u in urls:
                        if u not in links:
                            links.append(u)
                
                # 提取副标题逻辑：严格互斥提取，避免无关说明污染
                has_link_5 = len(cols[5].find_all('a')) > 0 or re.search(r'https?://', cols[5].get_text())
                has_link_6 = len(cols[6].find_all('a')) > 0 or re.search(r'https?://', cols[6].get_text())
                
                def get_clean_text(col):
                    """提取文本并移除其中的原始 URL"""
                    text = col.get_text(separator=' ', strip=True)
                    return re.sub(r'https?://[^\s]+', '', text).strip()
                    
                sub_name_raw = ""
                if has_link_5 and not has_link_6:
                    # 如果只有 5 有链接，说明 6 肯定是专属副标题
                    sub_name_raw = get_clean_text(cols[6])
                elif has_link_6 and not has_link_5:
                    # 如果只有 6 有链接，说明 5 肯定是专属副标题
                    sub_name_raw = get_clean_text(cols[5])
                else:
                    # 如果两者都有链接，或都没有，则只能合并过滤
                    t5 = get_clean_text(cols[5])
                    t6 = get_clean_text(cols[6])
                    sub_name_raw = f"{t5} {t6}".strip()
                    
                # 过滤非法路径字符并截断
                sub_name = re.sub(r'[\\/:*?"<>|]', '', sub_name_raw)
                sub_name = sub_name[:30].strip() # 限制长度
                
                if main_name or cn_text or es_text:
                    results.append({
                        'main_name': main_name,
                        'sub_name': sub_name,
                        'cn_text': cn_text,
                        'es_text': es_text,
                        'links': links,
                        'raw_source': str(row) # 保存一份原始 HTML 便于 debug
                    })

        except Exception as e:
            print(f"HTML Parse Error: {e}")
            
        return results

    @staticmethod
    def _extract_text_with_newlines(cell_element):
        """尽可能保留单元格内的换行"""
        # 将 <br> 替换为换行符
        for br in cell_element.find_all("br"):
            br.replace_with("\n")
        return cell_element.get_text(strip=False).strip()

    @staticmethod
    def clean_special_symbols(text):
        """
        全量清理文案中的无用特殊符号、Emoji、花里胡哨的图形符号等。
        同时把特殊的图文数字（如 1️⃣, ①, ❶, １等）全部转化为正常的阿拉伯数字。
        保留多国语言文字（\w）、空白符（\s）以及大量常用的中英文标点符号和基础符号。
        """
        if not text:
            return ""
            
        import unicodedata
        
        # 1. 替换 NFKC 内置标准里没有覆盖的特殊 emoji 和黑底实心数字
        special_num_map = {
            '🔟': '10',
            '❶': '1', '❷': '2', '❸': '3', '❹': '4', '❺': '5', '❻': '6', '❼': '7', '❽': '8', '❾': '9', '❿': '10',
            '➊': '1', '➋': '2', '➌': '3', '➍': '4', '➎': '5', '➏': '6', '➐': '7', '➑': '8', '➒': '9', '➓': '10',
            '⓿': '0', '⓪': '0'
        }
        for k, v in special_num_map.items():
            if k in text:
                text = text.replace(k, v)
                
        # 2. 使用 NFKC 进行文本标准化
        # 这一步会自动把 1️⃣, ①, １ 全部剥离修饰，转为最普通的 '1'。同时也会修正全角半角字母
        text = unicodedata.normalize('NFKC', text)
            
        # 3. 白名单符号剔除
        # 允许保留的字符集：
        # \w: 所有的字母、汉字、数字、下划线 (含西语带调字符)
        # \s: 所有空白字符 (空格、换行等)
        # 常用英文标点和数学符号: .,!?:;'"()/¡¿%@#+=$€*&^|\
        # 常用中文标点: ，。！？；：“”‘’（）【】《》、
        # 最后加上 - 连字符
        pattern = r'[^\w\s.,!?:;\'"()/¡¿%@#+=$€*&^|\\，。！？；：“”‘’（）【】《》、\-]'
        
        cleaned = re.sub(pattern, '', text)
        
        # 移除多余空白（但保留换行）
        cleaned = re.sub(r'[ \t]+', ' ', cleaned).strip()
        return cleaned

    @staticmethod
    def clean_spanish_text(text):
        return FileManager.clean_special_symbols(text)

    @staticmethod
    def clean_and_merge_text(text, threshold=300):
        """
        整理文本：
        1. 去除空行
        2. 如果行字数少于 threshold，则向下合并
        3. 合并时添加空格（优化英文）
        """
        if not text:
            return ""
            
        # 1. 拆分并去除空行
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        
        if not lines:
            return ""
            
        merged_lines = []
        current_buffer = lines[0]
        
        for i in range(1, len(lines)):
            next_line = lines[i]
            
            # 2. 检查是否需要合并
            if len(current_buffer) < threshold:
                # 合并！添加空格
                current_buffer += " " + next_line
            else:
                # 不需要合并，保存当前行，开始新的一行
                merged_lines.append(current_buffer)
                current_buffer = next_line
                
        # 保存最后一行
        merged_lines.append(current_buffer)
        
        return "\n".join(merged_lines)

    @staticmethod
    def get_google_drive_id(url):
        patterns = [
            r'/file/d/([a-zA-Z0-9_-]+)',
            r'id=([a-zA-Z0-9_-]+)'
        ]
        for p in patterns:
            match = re.search(p, url)
            if match:
                return match.group(1)
        return None

    @staticmethod
    def download_file(url, save_path_base):
        """
        下载文件。
        save_path_base: 这里是文件名（不含扩展名）。
        返回: (success, final_path_or_error)
        """
        try:
            file_id = FileManager.get_google_drive_id(url)
            download_url = url
            
            if file_id:
                download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            response = requests.get(download_url, stream=True, timeout=30)
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '')
            ext = '.bin' 
            if 'image/jpeg' in content_type:
                ext = '.jpg'
            elif 'image/png' in content_type:
                ext = '.png'
            elif 'application/pdf' in content_type:
                ext = '.pdf'
            elif 'video/mp4' in content_type:
                ext = '.mp4'
            else:
                if "Content-Disposition" in response.headers:
                    from email.message import EmailMessage
                    msg = EmailMessage()
                    msg['content-disposition'] = response.headers["Content-Disposition"]
                    filename = msg.get_filename()
                    if filename:
                        _, ext = os.path.splitext(filename)
                        if not ext:
                            ext = '.bin'
            
            final_path = f"{save_path_base}{ext}"
            
            if os.path.exists(final_path):
                # 如果文件已存在，为避免覆盖，添加时间戳
                timestamp = datetime.datetime.now().strftime("%H%M%S")
                final_path = f"{save_path_base}_{timestamp}{ext}"
            
            with open(final_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
                    
            return True, final_path
            
        except Exception as e:
            return False, str(e)

    @staticmethod
    def get_unique_base_name(output_root, item_data, index=None):
        """生成无冲突的基础文件名（默认包含顺序编号）"""
        main_name = item_data.get('main_name', '未命名项目')
        # 处理可能的特殊字符
        safe_main_name = re.sub(r'[\\/:*?"<>|]', '_', main_name)
        
        sub_name = item_data.get('sub_name', '')
        base_name = f"{safe_main_name}-{sub_name}" if sub_name else safe_main_name
        
        # 默认加上批处理的编号前缀 (例如 01_主名-副名)，保证在文件夹里按顺序排列
        if index is not None:
            base_name = f"{index:02d}_{base_name}"
        
        final_base = base_name
        counter = 1
        # 只要存在相关的 txt 就认为在此序号冲突
        while os.path.exists(os.path.join(output_root, f"{final_base}.txt")):
            final_base = f"{base_name}_{counter:02d}"
            counter += 1
            
        return final_base

    @staticmethod
    def save_combined_text(output_root, base_name, item_data):
        """将同一项目的中英文案合并保存为单个 txt，通过 --------- 分割"""
        cn_text = FileManager.clean_and_merge_text(item_data.get('cn_text', ''))
        es_text = FileManager.clean_and_merge_text(item_data.get('es_text', ''))
        
        content = ""
        if cn_text:
            content += cn_text
        if cn_text and es_text:
            content += "\n\n----------\n\n"
        if es_text:
            content += es_text
            
        if not content:
            # 即使没文案，也给个空文件代表项目创建了
            content = "无文本内容"
            
        txt_path = os.path.join(output_root, f"{base_name}.txt")
        try:
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True, txt_path
        except Exception as e:
            return False, str(e)

    @staticmethod
    def wrap_spanish_for_subtitles(text, words_per_line=4):
        """
        根据用户需求，将西语文本按每行约 3-4 个单词进行断行。
        """
        if not text:
            return ""
            
        # 先清除现有换行并合并为空格
        text = text.replace('\n', ' ').strip()
        words = text.split()
        
        lines = []
        for i in range(0, len(words), words_per_line):
            line = " ".join(words[i : i + words_per_line])
            if line:
                lines.append(line)
                
        return "\n".join(lines)

    @staticmethod
    def save_subtitle_file(output_root, base_name, content):
        """
        建立统一的字幕文件夹，并将所有项目的字幕 txt 都存入其中
        """
        if not content:
            return True, None
            
        # 统一存放在根目录下的“字幕”文件夹内
        sub_dir = os.path.join(output_root, "字幕")
        try:
            if not os.path.exists(sub_dir):
                os.makedirs(sub_dir)
            
            # 文件名与项目名一样，直接存入统一的“字幕”文件夹
            filename = f"{base_name}.txt"
            txt_path = os.path.join(sub_dir, filename)
            
            with open(txt_path, 'w', encoding='utf-8') as f:
                f.write(content)
                
            return True, txt_path
        except Exception as e:
            return False, str(e)

class SpeedWorker(QThread):
    progress_log = pyqtSignal(str)
    finished = pyqtSignal(bool, str)

    def __init__(self, file_path, speed):
        super().__init__()
        self.file_path = file_path
        self.speed = speed

    def run(self):
        try:
            ext = os.path.splitext(self.file_path)[1].lower()
            is_video = ext in ['.mp4', '.mov', '.avi', '.flv', '.mkv']
            
            try:
                local_ffmpeg = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0] if getattr(sys, 'frozen', False) else __file__)), "ffmpeg.exe")
                if os.path.exists(local_ffmpeg):
                    ffmpeg_exe = local_ffmpeg
                else:
                    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
            except:
                ffmpeg_exe = "ffmpeg"
                
            fd, temp_path = tempfile.mkstemp(suffix=ext)
            os.close(fd)
            
            cmd = [ffmpeg_exe, "-y", "-i", self.file_path]
            if is_video:
                cmd.extend(["-filter:v", f"setpts={1/self.speed}*PTS", "-filter:a", f"atempo={self.speed}"])
            else:
                cmd.extend(["-filter:a", f"atempo={self.speed}"])
            cmd.append(temp_path)
            
            creation_flags = 0
            if os.name == 'nt':
                 creation_flags = subprocess.CREATE_NO_WINDOW
                 
            self.progress_log.emit("⏳ 正在进行变速处理，请稍候...")
            process = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, creationflags=creation_flags)
            
            if process.returncode == 0:
                os.replace(temp_path, self.file_path)
                self.finished.emit(True, "处理成功")
            else:
                if os.path.exists(temp_path):
                    os.remove(temp_path)
                self.finished.emit(False, f"FFmpeg 错误:\n{process.stderr.decode('utf-8', errors='ignore')}")
        except Exception as e:
            self.finished.emit(False, str(e))
