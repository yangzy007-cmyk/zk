#!/bin/bash
# Linux 运行脚本 - 无需虚拟环境

echo "中控服务器启动脚本 (Linux)"
echo "=========================="

# 检查 Python3
if ! command -v python3 &> /dev/null; then
    echo "错误: 未找到 Python3，请先安装 Python3"
    echo "Ubuntu/Debian: sudo apt-get install python3 python3-pip"
    echo "CentOS/RHEL: sudo yum install python3 python3-pip"
    exit 1
fi

echo "Python 版本:"
python3 --version

# 检查依赖
echo ""
echo "检查依赖..."

# 检查 Flask
python3 -c "import flask" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "Flask 未安装，正在安装..."
    pip3 install --user flask
fi

# 检查其他依赖
python3 -c "import jinja2, werkzeug, requests" 2>/dev/null
if [ $? -ne 0 ]; then
    echo "安装其他依赖..."
    pip3 install --user jinja2 werkzeug requests
fi

echo "依赖检查完成"
echo ""

# 运行服务器
echo "启动中控服务器..."
echo "访问地址: http://localhost:5000"
echo "按 Ctrl+C 停止服务器"
echo ""

python3 run.py
