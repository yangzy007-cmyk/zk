#!/bin/bash
# Ubuntu 22.04+ 安装 buildozer

echo "=========================================="
echo "Ubuntu 安装 buildozer"
echo "=========================================="

# 方法1: 使用 apt 安装
echo "[尝试1] 使用 apt 安装 buildozer..."
sudo apt update
sudo apt install -y buildozer

if command -v buildozer &> /dev/null; then
    echo "[成功] buildozer 已安装!"
    buildozer --version
    exit 0
fi

# 方法2: 创建虚拟环境并安装
echo "[尝试2] 创建虚拟环境安装..."
cd ~/文档
rm -rf venv
python3 -m venv venv --system-site-packages
source venv/bin/activate

# 升级 pip
pip install --upgrade pip

# 安装 buildozer
pip install buildozer

# 创建启动脚本
cat > ~/文档/run_buildozer.sh << 'EOF'
#!/bin/bash
cd ~/文档
source venv/bin/activate
buildozer "$@"
EOF
chmod +x ~/文档/run_buildozer.sh

# 测试
echo "[测试] 检查 buildozer..."
if ~/文档/venv/bin/buildozer --version; then
    echo "[成功] 安装完成!"
    echo "使用方法: ~/文档/run_buildozer.sh android debug"
else
    echo "[失败] 安装失败，尝试方法3..."
    
    # 方法3: 使用 pipx
    echo "[尝试3] 使用 pipx 安装..."
    sudo apt install -y pipx
    pipx ensurepath
    pipx install buildozer
    
    echo "请重新登录或运行: source ~/.bashrc"
    echo "然后运行: buildozer android debug"
fi

echo "=========================================="
