#!/bin/bash
# Linux 依赖安装脚本

echo "安装系统依赖..."

# 检测系统类型
if command -v apt-get &> /dev/null; then
    # Debian/Ubuntu
    sudo apt-get update
    sudo apt-get install -y python3 python3-pip python3-venv
elif command -v yum &> /dev/null; then
    # CentOS/RHEL
    sudo yum install -y python3 python3-pip
elif command -v dnf &> /dev/null; then
    # Fedora
    sudo dnf install -y python3 python3-pip
elif command -v pacman &> /dev/null; then
    # Arch Linux
    sudo pacman -S --noconfirm python python-pip
else
    echo "不支持的系统类型，请手动安装 Python3 和 pip"
    exit 1
fi

echo "安装 Python 依赖..."

# 使用系统 pip 安装依赖
pip3 install --user flask jinja2 werkzeug requests

# 尝试安装 PySide6（用于系统托盘）
pip3 install --user PySide6 || echo "PySide6 安装失败，系统托盘功能将不可用"

echo "依赖安装完成！"
echo "现在可以直接运行: python3 run.py"
