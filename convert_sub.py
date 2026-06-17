#!/usr/bin/env python3
import base64, json, socket, urllib.parse, urllib.request, re, yaml, os

# ============================
# 优先从文件读取订阅地址
SUB_URL_FILE = os.path.expanduser("~/.config/mihomo/sub_url")
SUB_URL = None
if os.path.exists(SUB_URL_FILE):
    with open(SUB_URL_FILE, "r", encoding="utf-8") as f:
        SUB_URL = f.read().strip()

# 如果文件不存在，可在此手动填写备用地址
if not SUB_URL:
    SUB_URL = ""
# ============================

if not SUB_URL:
    print("No subscription URL found. Set it with: clashctl sub <url>")
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
