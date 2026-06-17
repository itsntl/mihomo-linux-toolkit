---
name: mihomo-linux-toolkit-operation
description: 在 Linux 下操作已配置好的 Mihomo（Clash.Meta）代理服务，包括启停、切换节点、更新订阅、测试连通性和故障排查。
whenToUse: 当用户需要启动、停止、重启、切换节点、更新订阅、测试或排查 Clash/Mihomo 代理时使用。
disableModelInvocation: false
---

# Clash / Mihomo 代理操作指南

> 本 Skill 用于指导 agent 在 Linux 环境（Ubuntu/Debian x86_64）下操作已配置好的 Mihomo（原 Clash.Meta）代理服务。
> 完整安装与配置说明请参考：`../setup.md`

---

## 1. 核心路径与端口

| 项目 | 路径 / 地址 |
|---|---|
| Mihomo 可执行文件 | `~/.local/bin/mihomo` |
| 配置文件 | `~/.config/mihomo/config.yaml` |
| 订阅转换脚本 | `~/.config/mihomo/convert_sub.py` |
| 已保存订阅地址 | `~/.config/mihomo/sub_url` |
| HTTP/SOCKS5 混合代理 | `127.0.0.1:7890` |
| SOCKS5 代理 | `127.0.0.1:7891` |
| RESTful API | `127.0.0.1:9090` |

---

## 2. 常用管理命令

推荐优先使用已安装的快捷脚本：

| 命令 | 作用 |
|---|---|
| `pxon` | 启动 mihomo |
| `pxoff` | 停止 mihomo |
| `pxrestart` | 重启 mihomo |
| `pxstatus` | 查看综合状态面板 |
| `pxnodes` | 列出所有节点 |
| `pxuse <序号或名称>` | 切换节点 |
| `pxlog` | 实时查看日志 |
| `pxtest` | 测试代理连通性 |
| `pxupdate` | 更新订阅并重启 |
| `pxsub` | 查看当前订阅地址 |
| `pxsub <url>` | 设置新订阅地址并更新 |
| `clashctl` | 统一入口脚本，支持 `on/off/restart/status/log/nodes/use/test/update/sub/edit` |

如果快捷脚本不可用，使用底层命令：

```bash
# 前台运行（调试）
mihomo -f ~/.config/mihomo/config.yaml

# 后台运行
nohup mihomo -f ~/.config/mihomo/config.yaml > /tmp/mihomo.log 2>&1 &
echo $! > /tmp/mihomo.pid

# 停止
pkill mihomo
# 或 kill "$(cat /tmp/mihomo.pid)"

# 验证配置
mihomo -t -f ~/.config/mihomo/config.yaml
```

---

## 3. 代理状态检查

### 3.1 检查 mihomo 是否在运行

```bash
pgrep -a mihomo
# 或
pxstatus
```

### 3.2 测试代理连通性

```bash
pxtest
# 或

curl -x http://127.0.0.1:7890 -I https://www.google.com
```

期望返回 `HTTP/2 200` 或 `HTTP/1.1 200`。

### 3.3 查看当前选中节点

```bash
curl -s http://127.0.0.1:9090/proxies/PROXY | python3 -m json.tool
```

---

## 4. 切换节点

优先使用快捷命令：

```bash
# 查看节点列表（带序号）
pxnodes

# 按序号切换
pxuse 3

# 按名称切换（名称含特殊字符时加引号）
pxuse "_Singapore-1|aws|X1.5"
```

如果快捷命令不可用，使用 API：

```bash
curl -s http://127.0.0.1:9090/proxies/PROXY | python3 -c "
import sys, json
d = json.load(sys.stdin)
for i, name in enumerate(d.get('all', [])):
    if name != 'DIRECT':
        print(f'{i}: {name}')
"

curl -X PUT http://127.0.0.1:9090/proxies/PROXY \
  -H 'Content-Type: application/json' \
  -d '{"name":"节点名"}'
```

---

## 5. 更新订阅

```bash
# 使用当前保存的订阅地址更新
pxupdate

# 或手动运行转换脚本
python3 ~/.config/mihomo/convert_sub.py
```

如果需要更换订阅地址：

```bash
pxsub "https://你的新订阅地址"
pxupdate
```

---

## 6. 在当前终端使用代理

```bash
# 设置代理环境变量
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export ALL_PROXY=socks5://127.0.0.1:7891

# 取消代理
unset http_proxy https_proxy ALL_PROXY
```

或使用快捷命令：

```bash
clashctl proxy
```

---

## 7. 故障排查

### 7.1 mihomo 无法启动

1. 检查配置文件语法：
   ```bash
   mihomo -t -f ~/.config/mihomo/config.yaml
   ```
2. 检查端口是否被占用：
   ```bash
   ss -tlnp | grep -E '7890|7891|9090'
   ```
3. 查看日志：
   ```bash
   pxlog
   # 或
   tail -n 100 /tmp/mihomo.log
   ```

### 7.2 curl 测试返回 000 / 超时

1. 确认 mihomo 已启动：`pxstatus`
2. 切换节点：`pxnodes` → `pxuse <序号>`
3. 重新测试：`pxtest`

### 7.3 国内网站变慢

当前规则可能是全局代理。如需国内直连、国外代理，请参考安装文档第 5 节配置 `GEOSITE,cn,DIRECT` 和 `GEOIP,CN,DIRECT`。

---

## 8. 操作原则

- **不要**执行 `systemctl --user enable mihomo`，避免开机自启。
- 优先使用 `pxon`/`pxoff`/`pxuse` 等快捷脚本，降低操作失误。
- 修改配置后先执行 `mihomo -t` 验证，再重启服务。
- 切换节点、更新订阅前，先确认 mihomo 正在运行。
