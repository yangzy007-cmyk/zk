#!/bin/bash
# 修复 distutils 问题

echo "=========================================="
echo "修复 distutils 问题"
echo "=========================================="

cd ~/文档
source venv/bin/activate

# 方法1: 使用环境变量
echo "[方法1] 设置环境变量..."
export SETUPTOOLS_USE_DISTUTILS=local

# 方法2: 安装兼容版本
echo "[方法2] 安装兼容包..."
pip install --upgrade setuptools wheel

# 方法3: 修改 buildozer 源码
echo "[方法3] 修复 buildozer 源码..."
BUILDozer_FILE="venv/lib/python3.13/site-packages/buildozer/targets/android.py"
if [ -f "$BUILDozer_FILE" ]; then
    # 备份
    cp "$BUILDozer_FILE" "$BUILDozer_FILE.bak"
    
    # 替换导入
    sed -i 's/from distutils.version import LooseVersion/from packaging.version import Version as LooseVersion/g' "$BUILDozer_FILE"
    
    echo "[完成] 已修复 android.py"
else
    echo "[错误] 找不到文件: $BUILDozer_FILE"
fi

# 安装 packaging
echo "[安装] 安装 packaging..."
pip install packaging

echo "=========================================="
echo "修复完成，请重试:"
echo "  buildozer android debug"
echo "=========================================="
