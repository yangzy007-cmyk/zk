#!/bin/bash
# 修复 Python 3.13 兼容性问题

echo "=========================================="
echo "修复 Python 3.13 兼容性"
echo "=========================================="

cd ~/文档
source venv/bin/activate

# 安装 distutils 替代包
echo "[1/3] 安装 setuptools（包含 distutils 兼容层）..."
pip install --upgrade setuptools

# 安装 distutils 替代包
echo "[2/3] 安装 distutils 替代包..."
pip install distutils

# 如果不行，尝试安装特定版本的 buildozer
echo "[3/3] 重新安装 buildozer..."
pip uninstall -y buildozer
pip install buildozer

echo "=========================================="
echo "修复完成，请重试:"
echo "  buildozer android debug"
echo "=========================================="
