#!/bin/bash
# 安卓 APK 构建脚本

echo "=========================================="
echo "中控空 - Android APK 构建脚本"
echo "=========================================="

# 检查 buildozer 是否安装
if ! command -v buildozer &> /dev/null; then
    echo "[错误] buildozer 未安装"
    echo "[提示] 请先安装 buildozer: pip install buildozer"
    exit 1
fi

# 清理之前的构建
echo "[清理] 清理之前的构建..."
rm -rf .buildozer bin build

# 构建 APK
echo "[构建] 开始构建 APK..."
buildozer android debug

# 检查构建结果
if [ -f "bin/*.apk" ]; then
    echo "=========================================="
    echo "[成功] APK 构建完成!"
    echo "[位置] bin/"
    ls -lh bin/*.apk
    echo "=========================================="
else
    echo "[错误] APK 构建失败"
    exit 1
fi
