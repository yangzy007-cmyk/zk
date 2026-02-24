#!/bin/bash
# 完全重新安装 buildozer

echo "=========================================="
echo "完全重新安装 buildozer"
echo "=========================================="

# 删除旧的虚拟环境
echo "[1/6] 删除旧的虚拟环境..."
cd ~/文档
rm -rf venv

# 创建新的虚拟环境
echo "[2/6] 创建新的虚拟环境..."
python3 -m venv venv
source venv/bin/activate

# 升级 pip
echo "[3/6] 升级 pip..."
pip install --upgrade pip setuptools wheel

# 安装依赖
echo "[4/6] 安装依赖..."
pip install Cython
pip install pyjnius

# 安装 buildozer
echo "[5/6] 安装 buildozer..."
pip install buildozer

# 验证
echo "[6/6] 验证安装..."
ls -la venv/bin/buildozer
file venv/bin/buildozer
head -1 venv/bin/buildozer

echo "=========================================="
echo "安装完成！"
echo "请运行: source venv/bin/activate && buildozer android debug"
echo "=========================================="
