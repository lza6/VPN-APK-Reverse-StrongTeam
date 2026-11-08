# VPN APK Reverse — StagVPN / Wolf Custom / Bee VPN

三个印尼系 VPN APK（同 strongteam.co 后端家族）的逆向知识库：协议、密钥、工具链、demo。

## 状态总表

| APK | 配置端点 | 协议 | 密钥 | 节点存活 | 可入池 |
|-----|---------|------|------|---------|--------|
| StagVPN v19 | `server.stagvpn.com/api/v1/app-data-new`（免鉴权） | OpenVPN UDP 1194 + IKEv2 | 明文 API 直出凭据 | 2/3（DE 通，Dubai 死） | 技术可行，授权风险自评 |
| Wolf Custom v2.8.1.2 | `strongteam.co/api/wolfcustom/newv1.txt`（404） | OVPN/Hysteria/VLESS-WS-TLS | AES-256-GCM 双 key 已还原 | 内置节点已死 | 否 |
| Bee VPN v1.10.11.2 | 同 Wolf 系 | 同 Wolf 内核 | Go 侧 key 未破（Frida 待做） | 未知 | 暂缓 |

## 快速开始

```bash
# 1. 反编译目标 APK
jadx -d out --no-res -j 4 target.apk

# 2. 还原 lsparanoid 混淆字符串（通用工具）
python tools/dump_strings.py out/sources "out/sources/org/lsposed/lsparanoid/Deobfuscator\$<APP>\$app.java" strings.json loc.json

# 3. Wolf 配置解密
python tools/decrypt_wolf.py assets_configfile.json wolf_decrypted.json

# 4. StagVPN 免费节点探测 + ovpn 生成
python tools/gen_ovpn_pool.py ./ovpn_out
```

## 文档

- `docs/REVERSE_REPORT.md` — 完整逆向报告
- `docs/PROTOCOL.md` — 协议手册（密钥/framing/端点/字段语义）
- `docs/NEWAPI_INTEGRATION.md` — **new-api 对接交接包**（对接会话从这里开始）

## 工具

| 文件 | 用途 |
|------|------|
| `tools/lsparanoid_deobf.py` | lsparanoid 字符串混淆还原器（Kotlin PRNG Python 移植，可复用于任何同族 APK） |
| `tools/dump_strings.py` | 全量字符串 dump + 位置映射 |
| `tools/decrypt_wolf.py` | Wolf AES-256-GCM 配置解密（主 key + injector key） |
| `tools/gen_ovpn_pool.py` | StagVPN 免费节点探测 + ovpn/凭据文件生成 |

## 沉淀方法论

见 `docs/PROTOCOL.md` §4「方法学卡」——同族 APK（v2rayNG fork + lsparanoid + Go 侧 AES 配置）的六步通用逆向流程。

## 合规

- 节点 IP/凭据已按 RFC5737 脱敏（`samples/`），真实值在本地运行期产物（gitignored）
- 第三方节点入生产池属未授权使用，需自行评估；本研究仅面向协议分析与安全评估
