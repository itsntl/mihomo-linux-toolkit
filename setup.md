# Clash / Mihomo 代理环境搭建指南

> 适用系统：Ubuntu 22.04+ / Debian / 其他 Linux x86_64 发行版  
> 核心工具：[Mihomo](https://github.com/MetaCubeX/mihomo)（原 Clash.Meta，原版 Clash 已停止维护）

---

## 1. 安装 Mihomo 核心

### 1.1 检查是否已安装

```bash
which mihomo
mihomo -v
```

如果输出类似 `Mihomo Meta v1.19.x`，则跳过下载步骤。

### 1.2 下载最新版 Mihomo

```bash
cd ~/Downloads
# 查看最新版：https://github.com/MetaCubeX/mihomo/releases
wget https://github.com/MetaCubeX/mihomo/releases/download/v1.19.26/mihomo-linux-amd64-compatible-v1.19.26.gz

gunzip mihomo-linux-amd64-compatible-v1.19.26.gz
chmod +x mihomo-linux-amd64-compatible-v1.19.26
mkdir -p ~/.local/bin
mv mihomo-linux-amd64-compatible-v1.19.26 ~/.local/bin/mihomo
```

确保 `~/.local/bin` 在 PATH 中：

```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc
source ~/.bashrc
mihomo -v
```

### 1.3 如果 GitHub 下载超时

国内访问 GitHub Releases 经常超时或中断。如果上面的 `wget` 长时间无响应，可以尝试 GitHub 镜像加速地址：

```bash
wget "https://gh-proxy.com/https://github.com/MetaCubeX/mihomo/releases/download/v1.19.26/mihomo-linux-amd64-compatible-v1.19.26.gz"
```

如果该镜像仍不可用，可换用其他镜像：

- `https://ghproxy.com/https://github.com/...`
- `https://github.moeyy.xyz/https://github.com/...`
- `https://hub.gitmirror.com/https://github.com/...`

镜像地址的可用性会随网络环境变化，多试几个，选择一个能稳定下载的即可。

---

## 2. 配置订阅

### 2.1 准备配置目录

```bash
mkdir -p ~/.config/mihomo
```

### 2.2 使用脚本自动转换订阅

机场订阅通常是 base64 编码的 `trojan://` / `vmess://` 链接列表，Mihomo 需要 YAML 格式。可以用以下脚本自动下载并转换。

将脚本保存为 `~/.config/mihomo/convert_sub.py`，并替换你自己的订阅地址：

```python
#!/usr/bin/env python3
import base64, json, os, socket, urllib.parse, urllib.request, re, yaml

# ============================
# 订阅地址配置
# 优先从 ~/.config/mihomo/sub_url 文件读取，文件不存在则使用下面的占位地址
SUB_URL_FILE = os.path.expanduser("~/.config/mihomo/sub_url")
SUB_URL = None
if os.path.exists(SUB_URL_FILE):
    with open(SUB_URL_FILE, "r", encoding="utf-8") as f:
        SUB_URL = f.read().strip()

# 如果上面没有读到，就在这里手动填写订阅地址
if not SUB_URL:
    SUB_URL = "http://你的订阅地址"
# ============================

if not SUB_URL:
    print("No subscription URL configured.")
    print("Set it in the script or save it to ~/.config/mihomo/sub_url")
    exit(1)

raw = urllib.request.urlopen(SUB_URL, timeout=15).read()
text = base64.b64decode(raw).decode("utf-8", errors="ignore")

proxies = []
seen = set()


def norm_name(s):
    s = urllib.parse.unquote(s).strip()
    s = re.sub(r"[^\w\u4e00-\u9fa5\-_.|]", "_", s)
    s = re.sub(r"_+", "_", s)
    return s[:60]


for line in text.strip().split("\n"):
    line = line.strip()
    if not line:
        continue

    if line.startswith("trojan://"):
        try:
            p = urllib.parse.urlparse(line)
            pw = urllib.parse.unquote(p.username or "")
            server = p.hostname or ""
            port = p.port or 443
            name = norm_name(urllib.parse.unquote(p.fragment) or f"trojan_{server}")
            qs = urllib.parse.parse_qs(p.query)
            allow_insecure = qs.get("allowInsecure", ["0"])[0] == "1"
            sni = qs.get("sni", [""])[0] or qs.get("peer", [""])[0]

            key = f"trojan:{server}:{port}:{pw}"
            if key in seen:
                continue
            seen.add(key)

            node = {
                "name": name,
                "type": "trojan",
                "server": server,
                "port": port,
                "password": pw,
                "skip-cert-verify": allow_insecure,
            }
            if sni:
                node["sni"] = sni
            proxies.append(node)
        except Exception as e:
            print("trojan parse error:", e, line[:80])

    elif line.startswith("vmess://"):
        try:
            b64 = line[8:]
            b64 += "=" * (-len(b64) % 4)
            info = json.loads(base64.b64decode(b64).decode("utf-8", errors="ignore"))
            server = info.get("add", "")
            port = int(info.get("port", 443))
            uuid = info.get("id", "")
            name = norm_name(info.get("ps", f"vmess_{server}"))
            network = info.get("net", "tcp")
            tls = info.get("tls", "") == "tls"
            sni = info.get("sni", "") or info.get("host", "")
            path = info.get("path", "")
            host = info.get("host", "")

            key = f"vmess:{server}:{port}:{uuid}"
            if key in seen:
                continue
            seen.add(key)

            node = {
                "name": name,
                "type": "vmess",
                "server": server,
                "port": port,
                "uuid": uuid,
                "alterId": int(info.get("aid", 0)),
                "cipher": "auto",
                "tls": tls,
                "network": network,
            }
            if sni:
                node["servername"] = sni
            if network == "ws" and (path or host):
                node["ws-opts"] = {}
                if path:
                    node["ws-opts"]["path"] = path
                if host:
                    node["ws-opts"]["headers"] = {"Host": host}
            proxies.append(node)
        except Exception as e:
            print("vmess parse error:", e, line[:80])

# 过滤掉本地无法解析的失效节点
alive_proxies = []
for p in proxies:
    try:
        socket.getaddrinfo(p["server"], None)
        alive_proxies.append(p)
    except Exception as e:
        print(f"SKIP unreachable node {p['server']}: {e}")

proxies = alive_proxies
if not proxies:
    print("No valid proxies!")
    exit(1)

# 去重名
name_counts = {}
for p in proxies:
    n = p["name"]
    if n in name_counts:
        name_counts[n] += 1
        p["name"] = f"{n}_{name_counts[n]}"
    else:
        name_counts[n] = 0

proxy_names = [p["name"] for p in proxies]

# 把你验证过好用的节点放在第一位作为默认
DEFAULT_NODE = proxy_names[0]

config = {
    "mixed-port": 7890,
    "socks-port": 7891,
    "external-controller": "127.0.0.1:9090",
    "allow-lan": False,
    "mode": "rule",
    "log-level": "info",
    "ipv6": False,
    "dns": {
        "enable": True,
        "listen": "127.0.0.1:1053",
        "enhanced-mode": "fake-ip",
        "fake-ip-range": "198.18.0.1/16",
        "nameserver": ["223.5.5.5", "119.29.29.29"],
        "default-nameserver": ["223.5.5.5", "119.29.29.29"],
    },
    "proxies": proxies,
    "proxy-groups": [
        {
            "name": "PROXY",
            "type": "select",
            "proxies": [DEFAULT_NODE] + [n for n in proxy_names if n != DEFAULT_NODE] + ["DIRECT"],
        }
    ],
    "rules": [
        "DOMAIN-SUFFIX,local,DIRECT",
        "IP-CIDR,127.0.0.0/8,DIRECT",
        "IP-CIDR,172.16.0.0/12,DIRECT",
        "IP-CIDR,192.168.0.0/16,DIRECT",
        "IP-CIDR,10.0.0.0/8,DIRECT",
        "MATCH,PROXY",
    ],
}

out_path = os.path.expanduser("~/.config/mihomo/config.yaml")
with open(out_path, "w", encoding="utf-8") as f:
    yaml.dump(config, f, allow_unicode=True, sort_keys=False)

print(f"Wrote {len(proxies)} proxies to {out_path}")
print(f"Default node: {DEFAULT_NODE}")
```

运行转换：

```bash
python3 ~/.config/mihomo/convert_sub.py
```

> 注：实际已创建的 `~/.config/mihomo/convert_sub.py` 做了改进，会自动从 `~/.config/mihomo/sub_url` 读取订阅地址，无需再手动修改脚本内的 `SUB_URL`。

### 2.3 验证配置

```bash
mihomo -t -f ~/.config/mihomo/config.yaml
```

看到 `configuration file ... test is successful` 即表示配置格式正确。

---

## 3. 手动启动 Mihomo

本章提供两种手动启动方式，按需选择。**不会开机自启**，用的时候开，不用的时候关。

### 方式一：前台运行（推荐调试时使用）

```bash
mihomo -f ~/.config/mihomo/config.yaml
```

- 日志直接输出在终端
- 按 `Ctrl + C` 即可关闭

### 方式二：后台运行（推荐日常使用时）

```bash
nohup mihomo -f ~/.config/mihomo/config.yaml > /tmp/mihomo.log 2>&1 &
echo $! > /tmp/mihomo.pid
```

关闭时：

```bash
kill "$(cat /tmp/mihomo.pid)"
# 或者
pkill mihomo
```

查看日志：

```bash
tail -f /tmp/mihomo.log
```

### 方式三：用 systemd 用户服务手动启停（可选）

如果你习惯用 `systemctl`，可以保留用户级服务，但**不启用开机自启**：

```bash
mkdir -p ~/.config/systemd/user

cat > ~/.config/systemd/user/mihomo.service << 'EOF'
[Unit]
Description=Mihomo Daemon
After=network.target

[Service]
Type=simple
ExecStart=%h/.local/bin/mihomo -f %h/.config/mihomo/config.yaml
Restart=on-failure
RestartSec=5

[Install]
WantedBy=default.target
EOF

systemctl --user daemon-reload
```

然后手动控制：

```bash
# 启动
systemctl --user start mihomo

# 停止
systemctl --user stop mihomo

# 查看状态
systemctl --user status mihomo --no-pager

# 查看日志
journalctl --user -u mihomo -n 50 --no-pager
```

> 注意：
> - 不要执行 `systemctl --user enable mihomo`，否则会变成开机自启。
> - 如果配置格式错误，mihomo 会启动失败，systemd 会因 `Restart=on-failure` 不断自动重启。此时先停止服务，修复配置后再启动：
>   ```bash
>   systemctl --user stop mihomo
>   mihomo -t -f ~/.config/mihomo/config.yaml   # 验证配置
>   systemctl --user start mihomo
>   ```

---

### 方式四：快捷管理脚本（推荐日常使用）

如果你希望用更简短的命令来管理 mihomo，可以使用以下脚本。

#### 主控脚本 `clashctl`

`~/.local/bin/clashctl` 是一个统一的管理脚本，兼容 systemd 用户服务和 nohup 后台运行两种方式。

```bash
# 启动 / 停止 / 重启
clashctl on
clashctl off
clashctl restart

# 查看状态
clashctl status

# 查看实时日志
clashctl log

# 列出节点（带序号）
clashctl nodes

# 切换节点（支持名称或序号）
clashctl use 3
clashctl use "_香港-1|津新|X2"

# 测试代理连通性
clashctl test

# 设置当前终端代理环境变量
clashctl proxy

# 更新现有订阅
clashctl update           # 优先运行 ~/.config/mihomo/convert_sub.py，否则重新下载已保存的地址

# 设置/查看订阅地址
clashctl sub              # 查看当前保存的订阅地址
clashctl sub <url>        # 设置新订阅地址并自动下载更新

# 编辑配置文件
clashctl edit
```

#### 超短快捷脚本

为了更方便，还准备了以下更短的命令：

| 命令 | 作用 |
|---|---|
| `pxon` | 启动 mihomo |
| `pxoff` | 停止 mihomo |
| `pxstatus` | 查看综合状态面板（运行状态、当前节点、连通性、日志） |
| `pxnodes` | 查看节点列表 |
| `pxuse <序号或名称>` | 切换节点 |
| `pxlog` | 实时查看日志 |
| `pxtest` | 测试代理连通性 |
| `pxupdate` | 更新现有订阅（优先运行 ~/.config/mihomo/convert_sub.py，否则重新下载） |
| `pxsub` | 查看当前保存的订阅地址 |
| `pxsub <url>` | 设置新订阅地址并自动下载更新 |

这些脚本本质上都是 `clashctl` 的快捷封装，位于 `~/.local/bin/` 下。

---

## 4. 使用教程

### 4.1 本地代理端口

| 用途 | 地址 |
|---|---|
| HTTP / SOCKS5 混合代理 | `127.0.0.1:7890` |
| SOCKS5 代理 | `127.0.0.1:7891` |
| RESTful API（切换节点/看状态） | `127.0.0.1:9090` |
| DNS（fake-ip） | `127.0.0.1:1053` |

### 4.2 测试代理是否可用

```bash
# 直接访问 Google（应返回 200）
curl -x http://127.0.0.1:7890 -I https://www.google.com

# SOCKS5 方式
curl --socks5-hostname 127.0.0.1:7891 -I https://www.youtube.com
```

### 4.3 终端临时走代理

```bash
export http_proxy=http://127.0.0.1:7890
export https_proxy=http://127.0.0.1:7890
export ALL_PROXY=socks5://127.0.0.1:7891

# 取消代理
unset http_proxy https_proxy ALL_PROXY
```

### 4.4 浏览器走代理

推荐安装浏览器扩展，例如：

- Chrome/Edge: **Proxy SwitchyOmega**
- Firefox: **FoxyProxy**

添加情景模式：

- 协议：`HTTP` 或 `SOCKS5`
- 服务器：`127.0.0.1`
- 端口：`7890`

### 4.5 查看所有节点列表

**前提：mihomo 必须正在运行。** 如果提示 `Expecting value: line 1 column 1 (char 0)`，说明 mihomo 没启动，先执行 `mihomo -f ~/.config/mihomo/config.yaml`。

> 快速命令：`pxnodes` 或 `clashctl nodes`（推荐）

#### 方法 1：列出所有节点名

```bash
curl -s http://127.0.0.1:9090/proxies/PROXY | python3 -c "
import sys, json
d = json.load(sys.stdin)
for name in d.get('all', []):
    if name != 'DIRECT':
        print(name)
"
```

#### 方法 2：从配置文件查看

```bash
grep -E '^  - name:' ~/.config/mihomo/config.yaml
```

#### 方法 3：详细列表（带类型和服务器地址）

```bash
python3 -c "
import os, yaml
cfg = yaml.safe_load(open(os.path.expanduser('~/.config/mihomo/config.yaml')))
for p in cfg.get('proxies', []):
    print(f'{p[\"name\"]:40s}  [{p[\"type\"]:8s}] {p[\"server\"]}:{p[\"port\"]}')
"
```

---

### 4.6 切换节点

> 快速命令：`pxuse <序号或名称>` 或 `clashctl use <序号或名称>`（推荐）

```bash
# 查看当前选中节点
curl -s http://127.0.0.1:9090/proxies/PROXY | python3 -m json.tool

# 切换到指定节点（将 "节点名" 替换为你要的节点）
curl -X PUT http://127.0.0.1:9090/proxies/PROXY \
  -H 'Content-Type: application/json' \
  -d '{"name":"节点名"}'
```

示例：

```bash
curl -X PUT http://127.0.0.1:9090/proxies/PROXY \
  -H 'Content-Type: application/json' \
  -d '{"name":"_Singapore-1|aws|X1.5"}'
```

### 4.7 启停与日志

如果你使用了上面的快捷脚本，直接用 `pxon`、`pxoff`、`pxlog` 即可。

否则，根据你选择的启动方式，对应使用以下命令：

**前台运行：**

```bash
# 直接按 Ctrl + C 关闭
```

**后台运行：**

```bash
# 启动
nohup mihomo -f ~/.config/mihomo/config.yaml > /tmp/mihomo.log 2>&1 &

# 关闭
pkill mihomo

# 看日志
tail -f /tmp/mihomo.log
```

**systemd 用户服务（如果按方式三配置）：**

```bash
# 启动
systemctl --user start mihomo

# 停止
systemctl --user stop mihomo

# 查看状态
systemctl --user status mihomo --no-pager

# 查看日志
journalctl --user -u mihomo -n 50 --no-pager

# 修改配置后重载
systemctl --user restart mihomo
```

---

## 5. 进阶：国内直连 + 国外代理分流

当前配置是 `MATCH,PROXY`（所有流量走代理）。如果你希望国内网站直连、国外走代理，需要引入 GeoIP / GeoSite 规则。

由于默认的 GeoData 从 GitHub 下载，在国内可能失败，建议手动下载后放到指定目录：

```bash
mkdir -p ~/.config/mihomo

# 在有代理的环境下下载（或者找国内镜像）
cd ~/.config/mihomo
curl -L -o geoip.metadb https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geoip.metadb
curl -L -o geosite.dat https://github.com/MetaCubeX/meta-rules-dat/releases/download/latest/geosite.dat
```

然后在 `~/.config/mihomo/config.yaml` 的 `rules` 部分改为：

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

重启生效：

```bash
systemctl --user restart mihomo
```

---

## 6. 更新订阅

订阅过期或节点失效时，直接运行：

```bash
pxupdate
```

这会优先运行 `~/.config/mihomo/convert_sub.py` 重新转换订阅，然后自动重启 mihomo。

如果是换了全新的订阅地址，先用 `pxsub` 设置：

```bash
pxsub "https://你的新订阅地址"
```

后续再用 `pxupdate` 刷新即可。

---

## 7. 常见问题

### Q1: mihomo 启动失败，提示 `can't initial GeoIP`

A: 当前配置已移除 GeoIP 规则避免此问题。如需分流，请按第 5 节手动下载 geodata。

### Q2: curl 测试返回 `000` 或超时

A: 可能是默认节点失效。切换到其他节点再试：

```bash
# 快捷方式
pxnodes          # 查看节点列表
pxuse 3          # 切换到第 3 个节点

# 或者手动通过 API
curl -s http://127.0.0.1:9090/proxies/PROXY | python3 -m json.tool
curl -X PUT http://127.0.0.1:9090/proxies/PROXY -H 'Content-Type: application/json' -d '{"name":"另一个节点名"}'
```

### Q3: 访问国内网站变慢

A: 当前规则是全局代理。请参考第 5 节配置 `GEOSITE,cn,DIRECT` 和 `GEOIP,CN,DIRECT`。

### Q4: 想使用图形界面管理

A: 可以安装 GUI 客户端，推荐：

- [Clash Verge Rev](https://github.com/clash-verge-rev/clash-verge-rev)（基于 Tauri，支持 Linux）
- [Mihomo Party](https://github.com/mihomo-party-org/mihomo-party)

安装后导入同一订阅地址即可。

### Q5: 安装时下载 mihomo 超时

A: 国内访问 GitHub Releases 通常不稳定。安装时若 `wget https://github.com/...` 长时间卡住，可改用 GitHub 镜像：

```bash
wget "https://gh-proxy.com/https://github.com/MetaCubeX/mihomo/releases/download/v1.19.26/mihomo-linux-amd64-compatible-v1.19.26.gz"
```

如果该镜像仍然超时，可尝试：

- `https://ghproxy.com/https://github.com/...`
- `https://github.moeyy.xyz/https://github.com/...`
- `https://hub.gitmirror.com/https://github.com/...`

不同网络环境下镜像可用性不同，多换几个即可。

---

## 附录：本次实际使用的配置信息（参考）

-  Mihomo 路径：`~/.local/bin/mihomo`
-  配置文件：`~/.config/mihomo/config.yaml`
-  订阅转换脚本：`~/.config/mihomo/convert_sub.py`
-  已保存订阅地址：`~/.config/mihomo/sub_url`
-  systemd 服务文件（可选，手动启停）：`~/.config/systemd/user/mihomo.service`
-  快捷管理脚本：`~/.local/bin/clashctl`
-  快捷命令脚本（均位于 `~/.local/bin/`）：
   - `pxon`、`pxoff`、`pxstatus`、`pxnodes`、`pxuse`、`pxlog`、`pxtest`、`pxupdate`、`pxsub`
-  本次验证可用节点（示例）：
   - `_Singapore-1|aws|X1.5`（trojan）
   - `_Singapore_-3|中转|X2`（vmess）
