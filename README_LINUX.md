# Linux 运行说明

## 方法一：使用系统 Python（推荐）

### 1. 安装依赖（只需执行一次）

```bash
# 给脚本执行权限
chmod +x install_deps.sh

# 运行安装脚本
./install_deps.sh
```

或者手动安装：

```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y python3 python3-pip

# CentOS/RHEL
sudo yum install -y python3 python3-pip

# 安装 Python 依赖
pip3 install --user flask jinja2 werkzeug requests
```

### 2. 运行服务器

```bash
# 给脚本执行权限
chmod +x run_linux.sh

# 运行服务器
./run_linux.sh
```

或者直接运行：

```bash
python3 run.py
```

**注意**：Linux 下必须使用 `python3` 命令，而不是 `python`。

## 方法二：使用虚拟环境（传统方式）

```bash
# 创建虚拟环境
python3 -m venv venv

# 激活虚拟环境
source venv/bin/activate

# 安装依赖
pip install flask jinja2 werkzeug requests

# 运行服务器
python run.py
```

## 访问服务器

启动后，在浏览器中访问：

```
http://localhost:5000
```

## 注意事项

1. **系统托盘**：Linux 下系统托盘功能已禁用，因为 Linux 的桌面环境多样，系统托盘实现复杂
2. **依赖安装**：如果使用 `--user` 选项安装依赖，可能需要将 `~/.local/bin` 添加到 PATH
3. **端口**：默认使用 5000 端口，如果被占用可以修改 `config.ini` 中的 `web_port`

## 故障排除

### 问题：找不到 flask 模块

**解决**：
```bash
pip3 install --user flask
```

### 问题：权限 denied

**解决**：
```bash
# 使用用户模式安装
pip3 install --user flask jinja2 werkzeug requests

# 或者使用 sudo（不推荐）
sudo pip3 install flask jinja2 werkzeug requests
```

### 问题：端口被占用

**解决**：
修改 `config.ini` 文件：
```ini
[network]
web_port = 5001
```
