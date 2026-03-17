import os
import json
import datetime

class ProjectManager:
    """
    Manage projects within a specific root directory.
    Metadata is stored in 'projects.json' inside that directory.
    """
    def __init__(self, root_dir):
        self.root_dir = root_dir
        self.data_file = os.path.join(root_dir, "projects.json") if root_dir else None
        self.projects = []
        self.reload()

    def set_root_dir(self, root_dir):
        self.root_dir = root_dir
        self.data_file = os.path.join(root_dir, "projects.json") if root_dir else None
        self.reload()

    def reload(self):
        self.projects = []
        if self.data_file and os.path.exists(self.data_file):
            try:
                with open(self.data_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.projects = data.get("projects", [])
            except Exception:
                pass # Fail silently or log error
    
    def save(self):
        if not self.data_file:
            return
            
        data = {
            "projects": self.projects,
            "updated_at": str(datetime.datetime.now())
        }
        try:
            with open(self.data_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=4, ensure_ascii=False)
        except Exception as e:
            print(f"Error saving projects: {e}")

    def add_project(self, name, description=""):
        """
        Add a new project or update existing one's timestamp.
        """
        # Check if exists
        for p in self.projects:
            if p["name"] == name:
                p["updated_at"] = str(datetime.datetime.now())
                self.save()
                return

        new_project = {
            "name": name,
            "created_at": str(datetime.datetime.now()),
            "updated_at": str(datetime.datetime.now()),
            "description": description
        }
        self.projects.append(new_project)
        self.save()

    def get_projects(self):
        return self.projects

    def rename_project(self, old_name, new_name):
        """
        重命名项目：更新元数据并重命名文件系统中所有相关文件。
        """
        if not self.root_dir or not old_name or not new_name:
            return False, "参数无效"

        # 1. 更新元数据
        found = False
        for p in self.projects:
            if p["name"] == old_name:
                p["name"] = new_name
                p["updated_at"] = str(datetime.datetime.now())
                found = True
                break
        
        if not found:
            return False, "找不到该项目"

        # 2. 重命名文件系统中的文件 (前缀匹配)
        try:
            # 根目录下的文件
            for f in os.listdir(self.root_dir):
                if f.startswith(old_name):
                    old_path = os.path.join(self.root_dir, f)
                    new_filename = f.replace(old_name, new_name, 1)
                    new_path = os.path.join(self.root_dir, new_filename)
                    if os.path.exists(old_path):
                        os.rename(old_path, new_path)
            
            # 字幕目录下的文件
            sub_dir = os.path.join(self.root_dir, "字幕")
            if os.path.exists(sub_dir):
                old_sub = os.path.join(sub_dir, f"{old_name}.txt")
                new_sub = os.path.join(sub_dir, f"{new_name}.txt")
                if os.path.exists(old_sub):
                    os.rename(old_sub, new_sub)
                    
            self.save()
            return True, "重命名成功"
        except Exception as e:
            return False, str(e)

    def delete_project(self, name):
        """
        删除项目：移除元数据并删除所有相关物理文件。
        """
        if not self.root_dir or not name:
            return False, "参数无效"

        # 1. 移除元数据
        self.projects = [p for p in self.projects if p["name"] != name]

        # 2. 删除文件系统中的文件 (前缀匹配)
        try:
            # 根目录
            for f in os.listdir(self.root_dir):
                if f.startswith(name):
                    path = os.path.join(self.root_dir, f)
                    if os.path.isfile(path):
                        os.remove(path)
            
            # 字幕目录
            sub_dir = os.path.join(self.root_dir, "字幕")
            if os.path.exists(sub_dir):
                sub_file = os.path.join(sub_dir, f"{name}.txt")
                if os.path.exists(sub_file):
                    os.remove(sub_file)
            
            self.save()
            return True, "删除成功"
        except Exception as e:
            return False, str(e)
