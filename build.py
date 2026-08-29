# -*- coding: utf-8 -*-
"""打包脚本：将 app.py 打包为单个可执行程序，并整理发布包目录。"""
import json
import os
import shutil
import subprocess
import sys

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
ICON_PATH = os.path.join(SRC_DIR, "icon.ico")
CONFIG_PATH = os.path.join(SRC_DIR, "config.json")
DIST_DIR = os.path.join(BASE_DIR, "dist")
BUILD_DIR = os.path.join(BASE_DIR, "build")
SPEC_PATH = os.path.join(BASE_DIR, "app.spec")


def main():
    # 读取版本号
    with open(CONFIG_PATH, "r", encoding="utf-8") as f:
        config = json.load(f)
    version = config.get("version", "v1.0.0")

    # 清理旧的构建产物
    for path in (DIST_DIR, BUILD_DIR, SPEC_PATH):
        if os.path.isdir(path):
            shutil.rmtree(path, ignore_errors=True)
        elif os.path.isfile(path):
            try:
                os.remove(path)
            except OSError:
                pass

    # 使用 PyInstaller 打包为单个 exe
    cmd = [
        os.path.join(BASE_DIR, ".venv", "Scripts", "pyinstaller"),
        "--onefile",
        "--noconsole",
        "--icon", ICON_PATH,
        "--name", "app",
        os.path.join(BASE_DIR, "app.py"),
    ]
    subprocess.check_call(cmd)

    exe = os.path.join(DIST_DIR, "app.exe")
    if not os.path.isfile(exe):
        print("打包失败：未找到 app.exe")
        sys.exit(1)

    # 把 src 目录复制到发布包目录下
    shutil.copytree(SRC_DIR, os.path.join(DIST_DIR, "src"))

    # 将 dist 改名为 "FlierZed {版本号}"
    release_dir = os.path.join(BASE_DIR, f"FlierZed {version}")
    if os.path.isdir(release_dir):
        shutil.rmtree(release_dir, ignore_errors=True)
    os.rename(DIST_DIR, release_dir)

    # 将 app.exe 改名为 FlierZed.exe
    os.rename(os.path.join(release_dir, "app.exe"), os.path.join(release_dir, "FlierZed.exe"))

    # 打包完成后删除 build 目录和 app.spec 文件
    if os.path.isdir(BUILD_DIR):
        shutil.rmtree(BUILD_DIR, ignore_errors=True)
    if os.path.isfile(SPEC_PATH):
        try:
            os.remove(SPEC_PATH)
        except OSError:
            pass

    print(f"打包完成：{release_dir}")


if __name__ == "__main__":
    main()