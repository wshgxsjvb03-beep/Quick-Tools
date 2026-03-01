import requests
API_KEY = 'sk_V2_hgu_ksAonVHRSXk_8ML6HynmXKZOBWtML47FDSwAJjZbiRyH'
# 使用用户日志中提到过的 ID，即使它可能已经不存在了，API 的响应码能告诉我们 endpoint 对不对
group_id = 'b04268cec02e41c99a2acdf13430440a' 

# 猜测的 endpoint
url = f"https://api.heygen.com/v2/photo_avatar/avatar_group/{group_id}"
headers = {"x-api-key": API_KEY}

print(f"Testing GET {url}")
resp = requests.get(url, headers=headers)
print(f"Status: {resp.status_code}")
print(f"Response: {resp.text}")

# 如果上面失败，尝试 list
if resp.status_code == 404:
    url_list = "https://api.heygen.com/v2/photo_avatars" # 猜测
    print(f"\nTesting GET {url_list}")
    resp = requests.get(url_list, headers=headers)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text}")
