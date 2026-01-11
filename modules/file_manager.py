
import os
import requests
import re
from urllib.parse import urlparse

class FileManager:
    @staticmethod
    def parse_clipboard_data(text):
        """
        解析剪贴板数据。
        预期格式：Col1 \t Col2 \t Link (或者是空格分隔，视具体情况优化)
        返回: (text1, text2, link) or None
        """
        text = text.strip()
        if not text:
            return None
            
        # 尝试按制表符分割
        parts = text.split('\t')
        
        # 如果不是制表符，尝试按多个空格分割（处理某些复制情况）
        if len(parts) < 3:
            parts = re.split(r'\s{2,}', text) # 至少2个空格
            
        if len(parts) >= 3:
            # 取前三个有效部分
            # 假设最后一个是链接，前两个是文本
            return parts[0].strip(), parts[1].strip(), parts[2].strip()
        
        return None

    @staticmethod
    def save_text(text1, text2, output_path):
        """
        保存两段文本到 txt 文件，使用空行分隔
        """
        content = f"{text1}\n\n{text2}"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(content)
            return True
        except Exception as e:
            print(f"Error saving text: {e}")
            return False

    @staticmethod
    def get_google_drive_id(url):
        """
        从 Google Drive 链接中提取 File ID
        支持 formats:
        - https://drive.google.com/file/d/FILE_ID/view...
        - https://drive.google.com/open?id=FILE_ID
        """
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
        下载文件。尝试自动识别 Google Drive 链接。
        save_path_base: 这里是文件名（不含扩展名），需要检测内容类型后添加扩展名。
        返回: (success, final_path_or_error)
        """
        try:
            # 1. 处理 Google Drive 链接
            file_id = FileManager.get_google_drive_id(url)
            download_url = url
            
            if file_id:
                # 转换为直接下载链接
                download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
            
            # 2. 发起请求
            response = requests.get(download_url, stream=True)
            response.raise_for_status()
            
            # 3. 确定扩展名
            content_type = response.headers.get('content-type', '')
            ext = '.bin' # 默认
            if 'image/jpeg' in content_type:
                ext = '.jpg'
            elif 'image/png' in content_type:
                ext = '.png'
            elif 'application/pdf' in content_type:
                ext = '.pdf'
            else:
                # 尝试从 Content-Disposition 获取文件名
                if "Content-Disposition" in response.headers:
                    import cgi
                    _, params = cgi.parse_header(response.headers["Content-Disposition"])
                    if 'filename' in params:
                        _, ext = os.path.splitext(params['filename'])
            
            final_path = f"{save_path_base}{ext}"
            
            # 4. 保存文件
            with open(final_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
                    
            return True, final_path
            
        except Exception as e:
            return False, str(e)
