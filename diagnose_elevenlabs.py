"""
ElevenLabs API 连接诊断工具
用于诊断为什么所有 API Key 查询都失败
"""

import sys
import json
import io

# 修复 Windows 控制台编码问题
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

def test_network_connection():
    """测试基本网络连接"""
    print("=" * 60)
    print("1. 测试网络连接...")
    print("=" * 60)
    
    try:
        import urllib.request
        import socket
        
        # 测试 DNS 解析
        print("\n[DNS 解析测试]")
        try:
            ip = socket.gethostbyname("api.elevenlabs.io")
            print(f"✅ DNS 解析成功: api.elevenlabs.io -> {ip}")
        except Exception as e:
            print(f"❌ DNS 解析失败: {e}")
            return False
        
        # 测试 HTTPS 连接
        print("\n[HTTPS 连接测试]")
        try:
            req = urllib.request.Request("https://api.elevenlabs.io/")
            req.add_header('User-Agent', 'Mozilla/5.0')
            
            with urllib.request.urlopen(req, timeout=10) as response:
                status = response.status
                print(f"✅ HTTPS 连接成功: 状态码 {status}")
                return True
        except urllib.error.URLError as e:
            print(f"❌ HTTPS 连接失败: {e}")
            if hasattr(e, 'reason'):
                print(f"   原因: {e.reason}")
            return False
        except Exception as e:
            print(f"❌ 连接测试失败: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ 缺少必要的库: {e}")
        return False

def test_elevenlabs_library():
    """测试 ElevenLabs 库是否正确安装"""
    print("\n" + "=" * 60)
    print("2. 测试 ElevenLabs 库...")
    print("=" * 60)
    
    try:
        from elevenlabs.client import ElevenLabs
        import elevenlabs
        print(f"✅ ElevenLabs 库已安装")
        if hasattr(elevenlabs, '__version__'):
            print(f"   版本: {elevenlabs.__version__}")
        return True
    except ImportError as e:
        print(f"❌ ElevenLabs 库未安装或导入失败: {e}")
        print("   请运行: pip install elevenlabs")
        return False

def test_api_key(api_key):
    """测试单个 API Key"""
    print(f"\n[测试 Key: ****]")
    
    try:
        from elevenlabs.client import ElevenLabs
        import time
        
        start_time = time.time()
        client = ElevenLabs(api_key=api_key)
        
        # 尝试获取订阅信息
        sub = client.user.subscription.get()
        elapsed = time.time() - start_time
        
        print(f"✅ API Key 有效 (响应时间: {elapsed:.2f}秒)")
        print(f"   已用字符数: {sub.character_count}")
        print(f"   字符限额: {sub.character_limit}")
        print(f"   剩余字符: {sub.character_limit - sub.character_count}")
        print(f"   订阅状态: {sub.status}")
        return True, None
        
    except Exception as e:
        error_str = str(e)
        print(f"❌ API Key 查询失败")
        print(f"   错误类型: {type(e).__name__}")
        print(f"   错误信息: {error_str}")
        
        # 分析常见错误
        if "401" in error_str or "Unauthorized" in error_str:
            print("   💡 可能原因: API Key 无效或已过期")
        elif "timeout" in error_str.lower():
            print("   💡 可能原因: 网络超时,请检查网络连接")
        elif "SSL" in error_str or "certificate" in error_str.lower():
            print("   💡 可能原因: SSL 证书验证失败")
        elif "connection" in error_str.lower():
            print("   💡 可能原因: 无法连接到服务器,可能需要代理")
        
        return False, error_str

def load_keys_from_config():
    """从配置文件加载 API Keys"""
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
            
        keys = config.get('elevenlabs_keys', [])
        if not keys:
            print("⚠️ 配置文件中没有找到 API Keys")
            return []
        
        print(f"✅ 从配置文件加载了 {len(keys)} 个 API Keys")
        return keys
    except FileNotFoundError:
        print("❌ 未找到 config.json 文件")
        return []
    except Exception as e:
        print(f"❌ 读取配置文件失败: {e}")
        return []

def main():
    print("\n")
    print("╔" + "=" * 58 + "╗")
    print("║" + " " * 10 + "ElevenLabs API 连接诊断工具" + " " * 18 + "║")
    print("╚" + "=" * 58 + "╝")
    print()
    
    # 步骤 1: 测试网络连接
    network_ok = test_network_connection()
    
    # 步骤 2: 测试库安装
    library_ok = test_elevenlabs_library()
    
    if not library_ok:
        print("\n❌ 无法继续测试,请先安装 elevenlabs 库")
        return
    
    # 步骤 3: 测试 API Keys
    print("\n" + "=" * 60)
    print("3. 测试 API Keys...")
    print("=" * 60)
    
    keys_data = load_keys_from_config()
    
    if not keys_data:
        print("\n请手动输入一个 API Key 进行测试:")
        test_key = input("API Key: ").strip()
        if test_key:
            test_api_key(test_key)
    else:
        success_count = 0
        fail_count = 0
        
        for i, key_data in enumerate(keys_data, 1):
            api_key = key_data.get('key', '')
            label = key_data.get('label', '未命名')
            
            if not api_key:
                continue
            
            print(f"\n[{i}/{len(keys_data)}] {label}")
            success, error = test_api_key(api_key)
            
            if success:
                success_count += 1
            else:
                fail_count += 1
            
            # 避免请求过快
            if i < len(keys_data):
                import time
                time.sleep(0.5)
        
        print("\n" + "=" * 60)
        print("测试总结")
        print("=" * 60)
        print(f"✅ 成功: {success_count}")
        print(f"❌ 失败: {fail_count}")
        print(f"📊 总计: {len(keys_data)}")
        
        if fail_count == len(keys_data) and not network_ok:
            print("\n💡 所有 Key 都失败且网络测试也失败,可能的原因:")
            print("   1. 网络无法访问 ElevenLabs API (需要代理或 VPN)")
            print("   2. 防火墙阻止了连接")
            print("   3. DNS 解析问题")
        elif fail_count == len(keys_data):
            print("\n💡 所有 Key 都失败但网络正常,可能的原因:")
            print("   1. 所有 API Keys 都已失效")
            print("   2. ElevenLabs API 服务异常")
            print("   3. 请求格式或库版本问题")

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️ 用户中断测试")
    except Exception as e:
        print(f"\n\n❌ 程序异常: {e}")
        import traceback
        traceback.print_exc()
    
    print("\n按 Enter 键退出...")
    input()
