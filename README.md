# Mihomo Linux Toolkit

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

一个用于在 Linux 下快速安装、配置和管理 [Mihomo](https://github.com/MetaCubeX/mihomo)（原 Clash.Meta）代理的工具箱。

```bash
git clone https://github.com/itsntl/mihomo-linux-toolkit.git
```

---

## 这是什么

Mihomo 是 Clash 停止维护后最受欢迎的替代核心之一，功能强大但上手门槛较高。本项目提供了一整套脚本和指南，帮你把「下载核心 → 转换订阅 → 启动代理 → 日常管理」这条链路打通，做到几条命令就能在 Linux 上跑起来。

## 解决什么问题

| 痛点 | 本项目的方案 |
|---|---|
| 原版 Clash 已停更 | 使用 Mihomo（Clash.Meta）作为代理核心 |
| 机场订阅是 base64 链接，Mihomo 需要 YAML | `convert_sub.py` 自动转换 `trojan://` / `vmess://` 为 `config.yaml` |
| 启动、切节点、看日志命令太杂 | `clashctl` 统一管理 + `pxon/pxoff/pxuse` 等超短快捷命令 |
| 国内下载 GitHub Release 超时 | `setup.md` 中提供多种 GitHub 镜像加速地址 |
| 不想开机自启，想用的时候再开 | 默认使用手动启停（nohup / systemd 用户服务均不启用开机自启） |

## 项目结构

| 文件/目录 | 说明 |
|---|---|
| `setup.md` | 完整安装与配置指南，建议第一次使用时对照阅读 |
| `clashctl` | 统一管理脚本，支持启动、停止、切节点、看日志、测试、更新订阅等 |
| `mihomo-shortcuts.sh` | 快捷函数定义，`source` 到 shell 后可用 `pxon`、`pxuse` 等命令 |
| `convert_sub.py` | 将机场 base64 订阅转换为 Mihomo 可用的 `config.yaml` |
| `pxon` / `pxoff` / `pxstatus` / `pxnodes` / `pxuse` / `pxlog` / `pxtest` / `pxupdate` / `pxsub` | `clashctl` 的快捷封装 |
| `skills/mihomo-linux-toolkit/SKILL.md` | 给 AI Agent 使用的操作指南 |

## 快速开始

### 1. 安装 Mihomo 核心

详细步骤见 [`setup.md`](./setup.md)。简版：

```bash
cd ~/Downloads
wget https://github.com/MetaCubeX/mihomo/releases/download/v1.19.26/mihomo-linux-amd64-compatible-v1.19.26.gz
gunzip mihomo-linux-amd64-compatible-v1.19.26.gz
chmod +x mihomo-linux-amd64-compatible-v1.19.26
mkdir -p ~/.local/bin
mv mihomo-linux-amd64-compatible-v1.19.26 ~/.local/bin/mihomo
```

确保 `~/.local/bin` 在 `PATH` 中：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
mihomo -v
```

国内下载超时请参考 `setup.md` 中的镜像加速方案。

### 2. 配置订阅

```bash
mkdir -p ~/.config/mihomo
# 将你的机场订阅地址写入文件
echo "https://你的订阅地址" > ~/.config/mihomo/sub_url

# 转换订阅并生成 config.yaml
python3 convert_sub.py
```

### 3. 启动代理

```bash
./pxon        # 或 clashctl on
./pxstatus    # 查看运行状态
./pxtest      # 测试是否能访问 Google
```

## 日常使用

### 快捷命令

| 命令 | 作用 |
|---|---|
| `pxon` | 启动 Mihomo |
| `pxoff` | 停止 Mihomo |
| `pxstatus` | 查看综合状态面板 |
| `pxnodes` | 列出所有节点（带序号） |
| `pxuse 3` | 切换到第 3 个节点 |
| `pxuse "节点名称"` | 按名称切换节点 |
| `pxlog` | 实时查看日志 |
| `pxtest` | 测试代理连通性 |
| `pxupdate` | 更新订阅并重启 |
| `pxsub` | 查看当前订阅地址 |
| `pxsub <url>` | 设置新订阅地址并自动更新 |

> 这些快捷命令本质上是 `clashctl` 的封装。如果你把 `mihomo-shortcuts.sh` 放到 `~/.local/bin/` 并 `source` 进 shell，也可以直接用函数形式调用。

### 统一入口 `clashctl`

```bash
clashctl on|off|restart|status|log
clashctl nodes
clashctl use 3
clashctl test
clashctl update
clashctl sub <url>
clashctl edit      # 编辑 config.yaml
clashctl proxy     # 为当前终端设置代理环境变量
```

### 本地代理端口

| 用途 | 地址 |
|---|---|
| HTTP / SOCKS5 混合代理 | `127.0.0.1:7890` |
| SOCKS5 代理 | `127.0.0.1:7891` |
| RESTful API | `127.0.0.1:9090` |

浏览器推荐安装 **Proxy SwitchyOmega**（Chrome/Edge）或 **FoxyProxy**（Firefox），指向 `127.0.0.1:7890`。

## 进阶

### 国内直连、国外代理分流

默认规则是全局代理。如需分流，请手动下载 GeoData 并按 `setup.md` 第 5 节修改 `rules`：

```yaml
rules:
  - DOMAIN-SUFFIX,local,DIRECT
  - IP-CIDR,127.0.0.0/8,DIRECT
  - IP-CIDR,172.16.0.0/12,DIRECT
  - IP-CIDR,192.168.0.0/16,DIRECT
  - IP-CIDR,10.0.0.0/8,DIRECT
  - GEOSITE,cn,DIRECT
  - GEOIP,CN,DIRECT
  - MATCH,PROXY
```

## 常见问题

**Q: mihomo 启动失败，提示 `can't initial GeoIP`**  
A: 当前配置已移除 GeoIP 规则避免此问题。如需分流，请按进阶部分手动下载 geodata。

**Q: `pxtest` 返回超时或 `000`**  
A: 先用 `pxnodes` 查看节点，再用 `pxuse` 切换到其他节点重试。

**Q: 访问国内网站变慢**  
A: 当前规则是全局代理。参考进阶部分配置 `GEOSITE,cn,DIRECT` 和 `GEOIP,CN,DIRECT`。

**Q: 想下载 mihomo 但 GitHub 超时**  
A: 使用镜像加速，例如：

```bash
wget "https://gh-proxy.com/https://github.com/MetaCubeX/mihomo/releases/download/v1.19.26/mihomo-linux-amd64-compatible-v1.19.26.gz"
```

更多镜像见 `setup.md`。

## 许可证

本项目基于 [MIT License](./LICENSE) 开源。
