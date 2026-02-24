#!/bin/bash
# 运行 buildozer 的脚本

cd ~/文档
source venv/bin/activate

# 运行 buildozer
python3 -m buildozer "$@"
