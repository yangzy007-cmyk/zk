#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
安卓 APK 入口文件
"""
import os
import sys

# 设置工作目录为应用目录
if hasattr(sys, '_MEIPASS'):
    # PyInstaller 打包后的路径
    base_dir = sys._MEIPASS
elif 'ANDROID_ARGUMENT' in os.environ:
    # Android 路径
    base_dir = os.path.dirname(os.path.abspath(__file__))
else:
    base_dir = os.path.dirname(os.path.abspath(__file__))

os.chdir(base_dir)

# 导入并运行主程序
from run import app, start_status_check_thread, check_license_status
import threading
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

if __name__ == '__main__':
    print("=" * 60)
    print("中控空 - Android 版")
    print("=" * 60)
    
    # 检查许可证
    valid, message = check_license_status()
    if not valid:
        print(f"[错误] 许可证无效: {message}")
        print("[提示] 请在浏览器中访问 http://localhost:5000 进行注册")
    else:
        print(f"[许可证] 有效，过期时间: {message}")
    
    # 启动状态检测线程
    print("[状态检测] 启动状态检测线程...")
    start_status_check_thread()
    
    # 启动 Flask 服务器
    print("[服务器] 启动 Flask 服务器...")
    print("[服务器] 访问地址: http://0.0.0.0:5000")
    print("=" * 60)
    
    # 在 Android 上使用 0.0.0.0 允许外部访问
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)
