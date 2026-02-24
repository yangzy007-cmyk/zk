#!/bin/bash
# Ubuntu 25 专用构建脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "中控空 - Android APK 构建脚本 (Ubuntu 25)"
echo "=========================================="

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 检查系统版本
echo -e "${YELLOW}[检查] 系统版本...${NC}"
if ! grep -q "Ubuntu" /etc/os-release; then
    echo -e "${RED}[错误] 这不是 Ubuntu 系统${NC}"
    exit 1
fi

UBUNTU_VERSION=$(grep VERSION_ID /etc/os-release | cut -d'"' -f2)
echo -e "${GREEN}[信息] Ubuntu 版本: $UBUNTU_VERSION${NC}"

# 检查 Java
echo -e "${YELLOW}[检查] Java 环境...${NC}"
if ! command -v java &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Java，请先安装 OpenJDK${NC}"
    echo "运行: sudo apt install openjdk-21-jdk"
    exit 1
fi

java -version
echo -e "${GREEN}[信息] Java 环境正常${NC}"

# 检查 Python
echo -e "${YELLOW}[检查] Python 环境...${NC}"
if ! command -v python3 &> /dev/null; then
    echo -e "${RED}[错误] 未找到 Python3${NC}"
    exit 1
fi

PYTHON_VERSION=$(python3 --version)
echo -e "${GREEN}[信息] Python 版本: $PYTHON_VERSION${NC}"

# 检查 buildozer
echo -e "${YELLOW}[检查] Buildozer...${NC}"
if ! command -v buildozer &> /dev/null; then
    echo -e "${YELLOW}[警告] 未找到 buildozer，正在安装...${NC}"
    pip3 install --user buildozer cython
    export PATH=$PATH:~/.local/bin
fi

buildozer --version
echo -e "${GREEN}[信息] Buildozer 已安装${NC}"

# 检查项目文件
echo -e "${YELLOW}[检查] 项目文件...${NC}"
if [ ! -f "buildozer.spec" ]; then
    echo -e "${RED}[错误] 未找到 buildozer.spec 文件${NC}"
    exit 1
fi

if [ ! -f "main.py" ]; then
    echo -e "${RED}[错误] 未找到 main.py 文件${NC}"
    exit 1
fi

echo -e "${GREEN}[信息] 项目文件检查通过${NC}"

# 清理旧构建（可选）
read -p "是否清理之前的构建缓存? (y/N): " clean_build
if [[ $clean_build =~ ^[Yy]$ ]]; then
    echo -e "${YELLOW}[清理] 清理构建缓存...${NC}"
    buildozer android clean
    rm -rf .buildozer
    echo -e "${GREEN}[清理] 完成${NC}"
fi

# 开始构建
echo ""
echo "=========================================="
echo -e "${GREEN}开始构建 APK...${NC}"
echo "=========================================="
echo ""

# 记录开始时间
START_TIME=$(date +%s)

# 执行构建
if buildozer android debug; then
    END_TIME=$(date +%s)
    BUILD_TIME=$((END_TIME - START_TIME))
    MINUTES=$((BUILD_TIME / 60))
    SECONDS=$((BUILD_TIME % 60))
    
    echo ""
    echo "=========================================="
    echo -e "${GREEN}✓ 构建成功!${NC}"
    echo "=========================================="
    echo -e "构建耗时: ${MINUTES}分 ${SECONDS}秒"
    echo ""
    
    # 显示生成的 APK
    echo -e "${GREEN}生成的 APK 文件:${NC}"
    ls -lh bin/*.apk 2>/dev/null || echo "APK 文件在 bin/ 目录中"
    echo ""
    echo -e "${YELLOW}下载命令:${NC}"
    echo "scp user@your-server:$(pwd)/bin/*.apk ./"
    
else
    echo ""
    echo "=========================================="
    echo -e "${RED}✗ 构建失败!${NC}"
    echo "=========================================="
    echo ""
    echo -e "${YELLOW}常见解决方法:${NC}"
    echo "1. 检查依赖是否完整安装"
    echo "2. 查看详细日志: buildozer android debug -v"
    echo "3. 清理缓存后重试: buildozer android clean"
    echo ""
    exit 1
fi
