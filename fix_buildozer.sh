#!/bin/bash
# 修复 buildozer 安装脚本

echo "=========================================="
echo "修复 buildozer 安装"
echo "=========================================="

# 确保在虚拟环境中
if [ -z "$VIRTUAL_ENV" ]; then
    echo "[提示] 未检测到虚拟环境，正在创建..."
    python3 -m venv venv
    source venv/bin/activate
fi

echo "[1/5] 升级 pip..."
pip install --upgrade pip

echo "[2/5] 安装 Cython..."
pip install Cython

echo "[3/5] 安装 buildozer..."
pip install buildozer

echo "[4/5] 检查安装..."
which buildozer
buildozer --version

echo "[5/5] 安装系统依赖..."
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

echo "=========================================="
echo "安装完成！"
echo "请运行: buildozer android debug"
echo "=========================================="
