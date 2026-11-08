# 三 APK 逆向报告（Wolf Custom VPN / StagVPN / Bee VPN）

日期：2026-11-09 · 工作目录 `D:\apk-analysis\` · demo `http://127.0.0.1:8951`

## 1. StagVPN v19.0.0 (com.doracone.stagvpn)

**协议**：OpenVPN UDP 1194 + IKEv2，业务 API 为 Retrofit REST。

**端点**（明文，无混淆）：
- `https://server.stagvpn.com/api/v1/config` — 应用配置
- `https://server.stagvpn.com/api/v1/app-data-new` — **免鉴权全量节点表**
- 其他：v1/login、v1/heartbeat、v1/registration、v1/update-connect-status

**关键发现**：`app-data-new` 无需任何 token 即返回 `ikev2servers[]`，每条含：
- `ip`、`opnconfig`（完整内联 OpenVPN client 配置 + CA 证书，`proto udp4 remote <ip> 1194`）
- `ikev2_user_name` / `ikev2_user_password` 即 `auth-user-pass` 凭据

**节点**（2026-11-09 实测）：
| ID | 名称 | IP | ping | TCP 1194 |
|----|------|----|------|----------|
| 837 | Falkenstein DE | 198.51.100.10 | ✅ | 超时（UDP-only） |
| 846 | Nuremberg DE | 198.51.100.11 | ✅ | 超时（UDP-only） |
| 851 | MENA-01 Dubai | 198.51.100.12 | ❌ | 超时 |

其余：免费计时 14700s、max_login_device 限制、`servers[]`/`packages[]` 当前为空（全部流量走 ikev2servers）。

## 2. Wolf Custom VPN v2.8.1.2 (core.vpn3jx.xtreme)

**内核**：v2rayNG fork + AndroidLibXrayLite + OpenVPN(hrovatmartin) + hev-socks5-tunnel + SSH。混淆两层：
1. **lsparanoid** 字符串混淆 — 已完整移植还原器 `tools/lsparanoid_deobf.py`（Python 复刻 Kotlin PRNG，全部 5440 条字符串还原）
2. Go 侧 AES-256-GCM 配置加密

**还原密钥**（GCM，nonce12/ct/tag16）：
- 主 key：`qkKG+glMDxozePe5/Kcm+ZLeba+jJIrF`（libgojni.so VA 0x363810）
- Injector key：`Li96biGlJWFeNwKxWR6RrC3IGBu0CsXO`（Payload/SNI/CustomProxy 字段，libgoinjector）

**云端配置** `https://strongteam.co/api/wolfcustom/newv1.txt` → **404 已下架**；`/nets/` → 403（IP/UA 屏蔽）。

**内置兜底** `assets/configfile.json` 已全解密（`wolf_config_full.json`）：
- 唯一节点：`sg.phfiles.com` → 203.0.113.50（SG），OVPN TCP 110 / UDP 53，凭据 `<user>/<pass>`，UDP obfs `sandok`
- 3 条 Network：Direct / WS 域前置（speedtest.net）/ research.net 分片 payload
- 本机实测：TCP 110/53/443/22 全部超时，ICMP 不通 → **节点疑似已废弃或地域锁**

**慢 DNS**：SlowDNS key `5d30d19aa2524d7bd89afdffd9c2141575b21a728ea61c8cd7c8bf3839f97032`

## 3. Bee VPN v1.10.11.2 (co.strongteam.beevpn)

同 strongteam.co 系（`/nets/` 图标缓存复用同一域名），v2rayNG fork。
- lsparanoid 已破（7109 条全还原，`bee_strings_all.json`）
- 配置解密走 `Libv2ray.do_`（Go 原生，密钥名风格 `MMCONFIGKEY1` 是 MMKV 存储键而非 AES key）
- Go 侧 key 提取进行中：`configfile.json` 为 624KB GCM 密文，穷举 crib-drag 扫描已排除符号区误报，待真 key

## 4. 代理池评估（对接 proxy_pool / gateway）

| 来源 | 结论 |
|------|------|
| StagVPN 3 节点 | 接口公开、凭据齐全 → 技术上 OpenVPN→SOCKS5 即可入池（沿用 VPN-Super 的 xray/ovpn 实例池架构）。**但属第三方生产设施，未授权使用风险自负**；建议仅作压测/协议验证靶标 |
| Wolf SG | 节点已死，无产出 |
| Bee | 待 key |

**本机代理安全**：全程仅使用每请求代理参数（urllib/requests 直连目标 API），未触碰任何系统代理设置、未启动本地代理进程；demo server 仅监听 127.0.0.1:8951。

## 5. 工具产出

| 文件 | 说明 |
|------|------|
| `tools/lsparanoid_deobf.py` | lsparanoid 混淆还原器（可复用于其他同族 APK） |
| `wolf_strings_all.json` / `bee_strings_all.json` | 全量还原字符串 + 位置映射 |
| `wolf_config_full.json` | Wolf 完整解密目录 |
| `demo/server.py` + `demo/index.html` | 本地 demo（8951） |
| `stag_appdata.json` / `stag_config.json` | StagVPN 原始 API 响应 |
