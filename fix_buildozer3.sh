#!/bin/bash
# 完整修复 buildozer 安装

echo "=========================================="
echo "完整修复 buildozer 安装"
echo "=========================================="

cd ~/文档

# 检查是否在虚拟环境中
echo "[检查] 当前 Python: $(which python3)"
echo "[检查] 当前 Pip: $(which pip)"

# 安装 buildozer
echo "[安装] 安装 buildozer..."
pip3 install --user buildozer 2>/dev/null || pip3 install buildozer

# 检查安装位置
echo "[检查] 查找 buildozer..."
find ~/.local -name "buildozer" 2>/dev/null
find /usr -name "buildozer" 2>/dev/null | head -5

# 尝试直接运行
echo "[测试] 尝试运行 buildozer..."
~/.local/bin/buildozer --version 2>/dev/null || /usr/local/bin/buildozer --version 2>/dev/null || echo "未找到 buildozer"

echo "=========================================="
echo "如果安装成功，请使用完整路径运行:"
echo "~/.local/bin/buildozer android debug"
echo "=========================================="
