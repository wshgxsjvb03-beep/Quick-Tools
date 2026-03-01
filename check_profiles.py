import os
import json

def get_chrome_profiles():
    local_state_path = os.path.join(os.environ['LOCALAPPDATA'], r"Google\Chrome\User Data\Local State")
    if not os.path.exists(local_state_path):
        return "找不到 Chrome 配置文件目录"
    
    with open(local_state_path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    profiles = []
    info_cache = data.get('profile', {}).get('info_cache', {})
    for folder_name, info in info_cache.items():
        profiles.append({
            'folder': folder_name,
            'name': info.get('name'),
            'user_name': info.get('user_name')
        })
    return profiles

if __name__ == "__main__":
    print("正在读取 Chrome 配置文件列表...")
    profiles = get_chrome_profiles()
    if isinstance(profiles, str):
        print(profiles)
    else:
        for p in profiles:
            print(f"名称: {p['name']:<15} 文件夹: {p['folder']}")
