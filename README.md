# Mihomo Linux Toolkit

本目录包含 Mihomo（原 Clash.Meta）代理在 Linux 下的完整安装指南、订阅转换脚本以及日常管理脚本。

## 文件说明

| 文件/目录 | 说明 |
|---|---|
| `setup.md` | 完整安装与配置指南（核心、订阅转换、启动方式、使用教程、常见问题） |
| `skills/` | Agent 技能目录，包含 `SKILL.md`，用于指导代理启停、切换节点、更新订阅和故障排查 |
| `clashctl` | 统一管理脚本，支持 `on/off/restart/status/log/nodes/use/test/update/sub/edit/proxy` |
| `mihomo-shortcuts.sh` | 统一快捷函数定义，可被 `source` 到 shell 中使用 |
| `convert_sub.py` | 将机场 base64 订阅转换为 Mihomo 可用的 `config.yaml` |
| `pxon` | 启动 Mihomo |
| `pxoff` | 停止 Mihomo |
| `pxstatus` | 显示综合状态面板 |
| `pxnodes` | 列出代理节点 |
| `pxuse` | 切换代理节点 |
| `pxlog` | 实时查看日志 |
| `pxtest` | 测试代理连通性 |
| `pxupdate` | 更新订阅并重启 |
| `pxsub` | 查看或设置订阅地址 |

## 快速开始

```bash
./pxon        # 启动代理
./pxstatus    # 查看状态
./pxtest      # 测试连通性
```

更多详情请参阅 `setup.md`。
