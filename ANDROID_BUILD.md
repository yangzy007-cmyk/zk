# 中控空 - Android APK 构建指南

## 方法1：使用 Docker（推荐，Windows/Mac/Linux 都支持）

### 1. 安装 Docker
- Windows: 安装 Docker Desktop
- Mac: 安装 Docker Desktop
- Linux: `sudo apt install docker.io`

### 2. 使用 Kivy 官方 Docker 镜像构建

```bash
# 拉取 Kivy 构建镜像
docker pull kivy/buildozer

# 进入项目目录
cd g:\python\zhonkgongkong

# 运行构建容器
docker run -it --rm \
  -v "$(pwd):/home/user/hostcwd" \
  kivy/buildozer \
  android debug
```

构建完成后，APK 文件会在 `bin/` 目录下。

## 方法2：在 Linux 虚拟机中构建

### 1. 安装 Ubuntu 虚拟机
使用 VirtualBox 或 VMware 安装 Ubuntu 20.04/22.04。

### 2. 安装依赖

```bash
# 更新系统
sudo apt update
sudo apt upgrade -y

# 安装 Python 和依赖
sudo apt install -y python3 python3-pip

# 安装 buildozer 依赖
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev

# 安装 buildozer
pip3 install buildozer

# 安装 cython
pip3 install cython
```

### 3. 构建 APK

```bash
# 克隆或复制项目到 Linux
cd ~/zhonkgongkong

# 运行构建脚本
chmod +x build_android.sh
./build_android.sh

# 或者直接使用 buildozer
buildozer android debug
```

### 4. 获取 APK
构建完成后，APK 文件在 `bin/` 目录下：
- `zhonkgongkong-1.0-arm64-v8a_armeabi-v7a-debug.apk`

## 方法3：使用 GitHub Actions 自动构建（最简单）

### 1. 创建 GitHub 仓库
将代码推送到 GitHub。

### 2. 创建构建工作流

创建 `.github/workflows/build-android.yml`:

```yaml
name: Build Android APK

on: [push, pull_request]

jobs:
  build:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.10'
    
    - name: Install dependencies
      run: |
        sudo apt update
        sudo apt install -y git zip unzip openjdk-17-jdk autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
        pip install buildozer cython
    
    - name: Build APK
      run: |
        buildozer android debug
    
    - name: Upload APK
      uses: actions/upload-artifact@v3
      with:
        name: android-apk
        path: bin/*.apk
```

### 3. 自动构建
每次推送到 GitHub，Actions 会自动构建 APK，你可以在 Actions 页面下载。

## 安装 APK 到安卓设备

### 方法1：直接安装
1. 将 APK 复制到安卓手机
2. 在文件管理器中点击 APK 安装
3. 允许"未知来源"安装

### 方法2：使用 ADB
```bash
# 连接手机，开启 USB 调试
adb install bin/zhonkgongkong-1.0-arm64-v8a_armeabi-v7a-debug.apk
```

## 常见问题

### 1. 构建失败，提示缺少依赖
```bash
# 安装所有依赖
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake libffi-dev libssl-dev
```

### 2. 构建时间过长
首次构建需要下载 Android SDK 和 NDK，可能需要 30-60 分钟。后续构建会快很多。

### 3. APK 安装后闪退
- 检查日志：`adb logcat | grep python`
- 确保所有依赖都在 `buildozer.spec` 的 `requirements` 中
- 检查文件路径是否正确

### 4. 无法访问网络
确保 `buildozer.spec` 中包含了网络权限：
```
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE
```

## 配置说明

### buildozer.spec 关键配置

```ini
# 应用名称
title = 中控空

# 包名
package.name = zhonkgongkong

# 依赖库
requirements = python3,flask,werkzeug,jinja2,markupsafe,itsdangerous,click,colorama

# 权限
android.permissions = INTERNET,ACCESS_NETWORK_STATE,ACCESS_WIFI_STATE

# 支持的架构
android.archs = arm64-v8a, armeabi-v7a

# 端口
android.port = 5000
```

## 调试

### 查看日志
```bash
# 连接手机后
adb logcat | grep -i "中控空\|zhonkgongkong\|python"
```

### 浏览器访问
安装后，在同一局域网的电脑/手机上访问：
```
http://手机IP:5000
```

## 发布

构建 release 版本：
```bash
buildozer android release
```

需要配置签名密钥。
