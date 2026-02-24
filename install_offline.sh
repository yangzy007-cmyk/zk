#!/bin/bash
# 离线/手动安装 buildozer

echo "=========================================="
echo "手动安装 buildozer"
echo "=========================================="

cd ~/文档

# 删除旧的
rm -rf venv

# 创建虚拟环境
python3 -m venv venv
source venv/bin/activate

# 安装 pip 工具
pip install --upgrade pip setuptools wheel

# 安装依赖（逐个安装，看哪个失败）
echo "[1/4] 安装 Cython..."
pip install Cython || echo "Cython 安装失败"

echo "[2/4] 安装 sh..."
pip install sh || echo "sh 安装失败"

echo "[3/4] 安装 docopt..."
pip install docopt || echo "docopt 安装失败"

echo "[4/4] 安装 buildozer..."
pip install buildozer

# 检查是否安装成功
echo "[检查] 检查安装结果..."
ls -la venv/lib/python*/site-packages/ | grep buildozer

# 尝试运行
echo "[测试] 尝试运行..."
python3 -c "import buildozer; print('buildozer 模块已安装')" || echo "模块导入失败"

# 创建 wrapper 脚本
cat > buildozer << 'EOF'
#!/bin/bash
source ~/文档/venv/bin/activate
python3 -m buildozer "$@"
EOF
chmod +x buildozer

echo "=========================================="
echo "安装完成！"
echo "使用方法:"
echo "  source ~/文档/venv/bin/activate"
echo "  buildozer android debug"
echo "=========================================="
