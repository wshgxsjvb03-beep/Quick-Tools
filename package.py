import os
import subprocess
import sys

def package():
    print("开始打包 Quick Tools...")
    
    # 确保安装了 pyinstaller
    try:
        import PyInstaller
    except ImportError:
        print("未检测到 PyInstaller，正在安装...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])

    # 运行打包命令
    # 使用 --noconfirm 覆盖现有构建
    # 使用 --clean 清理临时文件
    cmd = [
        "pyinstaller",
        "QuickTools.spec",
        "--noconfirm",
        "--clean"
    ]
    
    print(f"执行命令: {' '.join(cmd)}")
    try:
        subprocess.check_call(cmd)
        print("\n打包成功！")
        print(f"可执行文件位于: {os.path.join(os.getcwd(), 'dist', 'QuickTools.exe')}")
    except subprocess.CalledProcessError as e:
        print(f"\n打包失败: {e}")
        sys.exit(1)

if __name__ == "__main__":
    package()
