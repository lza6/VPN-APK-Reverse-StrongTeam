# 协议手册 — Wolf Custom VPN / StagVPN / Bee VPN

逆向日期 2026-11-09。所有密钥/格式均已实测复现（`已验证` 级标注）。

## 1. Wolf Custom VPN v2.8.1.2 (core.vpn3jx.xtreme)

### 1.1 包结构
- 内核：v2rayNG fork（com.v2ray.ang）+ AndroidLibXrayLite(libgojni.so) + OpenVPN(libovpncli.so) + hev-socks5-tunnel + SSH(trilead)
- 签名校验：pairip；另有 ApkSignatureKillerEx 痕迹（mod 版）

### 1.2 lsparanoid 字符串混淆 `已验证`
- 实现：`org.lsposed.lsparanoid.Deobfuscator$WolfCustomVPN$app`（Bee 同款，类名随 app 变）
- 算法：seed(64bit) → splitmix64 变体 PRNG（16-bit 槽宽 + rotl 混合）→ 字符流索引
- 还原器：`tools/lsparanoid_deobf.py`（Python 移植，含符号扩展语义处理）
- 用法：`python lsparanoid_deobf.py <Deobfuscator类.java> <seed1> <seed2> ...`
- seed 常量在调用点形如 `getString(-100221692234812L)`

### 1.3 配置加密（云端 + 内置 assets 同套）`已验证`
- **AES-256-GCM**，framing：`base64( nonce[12] || ciphertext || tag[16] )`
- 主 key（libgojni.so VA 0x363810 固定字节）：`qkKG+glMDxozePe5/Kcm+ZLeba+jJIrF`（32B ASCII 直接当 key，非 b64 非 hash）
- injector key（libgoinjector.so，Payload/SNI/CustomProxy 字段专用）：`Li96biGlJWFeNwKxWR6RrC3IGBu0CsXO`
- 明文结构：JSON `ConfigData`：`{Version, ReleaseNotes, Telegram, ..., DefOVPNUser, DefOVPNPass, HysteriaUser, HysteriaOBFS, DefaultOVPNCert, isTimerOn, timetoadd, Servers[], Networks[]}`
- 二次加密字段：长度≥40 且匹配 b64 字符集的字符串值需再过一次 decrypt（Servers 内的 OVPNUser/OVPNPass/ServerIPHost、Networks 内的 Payload/SNI/V2rayConfig 等）
- 解密器：`tools/decrypt_wolf.py`

### 1.4 端点
- 云端配置：`https://strongteam.co/api/wolfcustom/newv1.txt`（当前 404）
- 图标/网络资源：`https://strongteam.co/nets/`（403 对非浏览器 UA）
- 内置兜底：`assets/configfile.json`（同一套 GCM 加密）

### 1.5 节点字段语义
| 字段 | 含义 |
|------|------|
| ServerIPHost | 服务器域名/IP（二次加密） |
| OpenVPNTCPPort / OpenVPNUdpPort | OVPN 双端口 |
| UDP_obfs | UDP 隧道混淆密码（如 sandok） |
| SlowDNSHost/SlowDNSKey | DNS 隧道参数 |
| TunnelType | Direct TCP / SSL / Hysteria / V2ray |
| V2rayHost/SNI/Path/UUID | VLESS-WS-TLS 模板变量（custom1.json 模板填充） |

## 2. StagVPN v19.0.0 (com.doracone.stagvpn)

### 2.1 API `已验证`
- Base: `https://server.stagvpn.com/api/`
- `v1/config`：应用配置（广告位、timer、max_login_device）
- `v1/app-data-new`：**免鉴权**节点表
- `v1/login` / `v1/registration` / `v1/heartbeat` / `v1/logout` / `v1/update-connect-status`（FormUrlEncoded）
- 无签名、无加密、无设备指纹；UA 不敏感

### 2.2 节点结构
`ikev2servers[]`（当前全部流量）：
- `opnconfig`：完整 OpenVPN client 内联配置，`proto udp4 remote <ip> 1194`，AES-256-GCM 数据信道，CA 内联
- `ikev2_user_name/password`：同时充当 OVPN auth-user-pass
- `is_free`、`status`、`connected_user`、`ping`
- 免费会话时长：`free_server_timer: 14700` 秒（≈4h）

### 2.3 可靠性
- 三节点（DE x2 + Dubai）：DE 两台 ICMP 通，Dubai 完全不通
- UDP-only：TCP 1194 全超时，勿试

## 3. Bee VPN v1.10.11.2 (co.strongteam.beevpn)

### 3.1 与 Wolf 的关系
同 strongteam.co 系（域名复用 `/nets/`），同为 v2rayNG fork，lsparanoid 混淆同款。

### 3.2 差异
- 混淆类名：`Deobfuscator$BEEVPN$app`，seed 空间不同
- JNI 方法名混淆：`Libv2ray.do_`（=Wolf 的 `decrypt`）、`gv`、`gc`、`cu`、`gfc` 等
- `MMCONFIGKEY1` 是 **MMKV 存储键**（云端配置缓存），不是 AES key
- Go 侧解密：`configfile.json` 624KB，len%16=9 → 支持分块流式 GCM 假设；key 静态穷举已排除（全库 crib-drag ×17 偏移无 tag 验证通过）
- 待做：Frida hook `Hometab$Companion.a()` → `Libv2ray.do_(str)` 运行时取明文

### 3.3 已还原资产
- `bee_strings_all.json`：7109 条混淆字符串全量 + 位置映射
- 遥测加密（HomeFragment.b0）：AES-GCM，key=混淆字符串常量 `nIiQlr+O9jX8NhJL5jSaqP7+/2W8aqLG`，随机 12B nonce，输出 `base64(nonce||ct||tag)` —— 这是**上报加密**，与配置解密无关

## 4. 方法学卡（同族 APK 通用流程）

1. jadx 反编译（-j 并行，2 万+ 类正常）
2. 查 `org/lsposed/lsparanoid/` → 有则先写/复用还原器破字符串层
3. assets 里找 `configfile.json` 类密文 → base64 解后看 framing（nonce12/ct/tag16 → 单块 GCM）
4. key 来源三查：Go 二进制固定字节区（wolf 命中）、Java 常量（遥测 key 命中）、运行时 hook（bee 走此路）
5. 云端端点从还原字符串里捞 `https://` 域名 → 立即验证存活性（本单两处已死）
6. 节点表拿到后先 ping/TCP 探测再谈入池
