# new-api 对接指南 — StagVPN / Wolf / Bee VPN 三 APK 逆向产出

> 交接包。逆向会话职责已闭环；对接由另一会话执行。先读本文 §1 判断你要接哪条线。

## 0. TL;DR

| 线 | 可接入性 | 接法 | 优先级 |
|----|---------|------|--------|
| StagVPN 3 节点 | 端点+凭据齐全，OpenVPN UDP 1194 | OpenVPN 客户端实例 → SOCKS5 转换 → 入池 | 技术可行，**授权风险自评**（第三方生产设施） |
| Wolf SG 节点 | 已死（TCP 110/53/443/22 全超时） | 无 | 放弃 |
| Bee VPN | 密钥未破（Frida 路线待做） | 无 | 暂缓 |

**合规铁律（继承 VPN-US 单）**：本项目只探测/接入 `source==free` 的节点；自有 VPS 不入生产池；第三方节点入生产池前需用户明确拍板。

## 1. StagVPN 线（唯一可接的）

### 1.1 数据源

```
GET https://server.stagvpn.com/api/v1/config        → 应用配置
GET https://server.stagvpn.com/api/v1/app-data-new  → 全量节点（免鉴权）
```

`app-data-new` 返回结构：

```json
{
  "servers": [],            // 当前恒为空
  "ikev2servers": [          // 真正的节点表
    {
      "id": 837, "server_name": "Falkenstein",
      "ip": "<IPv4>",
      "ikev2_user_name": "<user>",       // 即 OpenVPN auth-user-pass 用户名
      "ikev2_user_password": "<pass>",   // 即 OpenVPN 密码
      "is_free": 1, "status": 1,
      "protocol": "2",
      "opnconfig": "client\r\ndev tun\r\nproto udp4\r\nremote <ip> 1194\r\n...<ca>PEM...</ca>"
    }
  ],
  "countries": [...], "packages": []
}
```

关键点：
- `opnconfig` 是**完整内联 OpenVPN client 配置**（含 CA 证书），直接可喂给 openvpn 客户端，无需额外证书文件。
- 只取 `is_free==1 && status==1` 的节点。
- 无鉴权、无签名、无设备指纹 → 可定时轮询做节点发现（建议 ≥30min 间隔，别打爆人家）。

### 1.2 拨号验证（对接会话第一步）

需要本机装 OpenVPN 客户端（OpenVPN Community `openvpn.exe` 即可，不需要 GUI）。

```powershell
# 1. 拉节点表
python -c "import urllib.request,json; d=json.load(urllib.request.urlopen('https://server.stagvpn.com/api/v1/app-data-new')); print(json.dumps(d['ikev2servers'],indent=1))"

# 2. 取 is_free==1 的第一条, 把 opnconfig 写成 .ovpn 文件（原样, 不改内容）
# 3. 测试拨号 (Windows 需管理员权限, 会创建 TAP 适配器)
openvpn.exe --config node.ovpn --auth-user-pass cred.txt --connect-retry-max 2 --verb 3
# cred.txt 两行: 用户名\n密码

# 4. 拨通后验证出口 IP
curl --interface <tap适配器> https://api.ipify.org
```

已知事实（逆向会话实测）：
- `proto udp4 remote <ip> 1194` — **UDP only**，TCP 1194 全部超时，不要浪费时间去试 TCP。
- 德国两台 ping 通，迪拜那台 ICMP 都不通，大概率已死或地域锁。

### 1.3 OpenVPN → SOCKS5 入池

拨通的 OpenVPN 是 L3 隧道，池子要 SOCKS/HTTP 入口。两条路：

**路线 A（推荐）：每节点一台 openvpn 进程 + VPN 内跑 microsocks/3proxy 转 SOCKS5**
```
openvpn(node i) → tap/tun 网段 i → 在该网段内监听 socks5://127.0.0.1:1081x
→ proxy_pool AddProxy(socks5, 127.0.0.1:1081x, source='free', tags=['stagvpn'])
```
Windows 下每实例需要独立 TAP 子网（`--ifconfig` 错开 10.x 网段），配置模板见 `tools/gen_ovpn_pool.py`（本文档同仓库）。

**路线 B（轻量备选）：openvpn + hev-socks5-tunnel**
APK 里就带 `libhev-socks5-tunnel.so`，同款用户态实现可作单机 socks 转换器，但 Windows 原生支持一般，路线 A 更省事。

### 1.4 对接 gateway/proxy_pool

沿用 VPN-US 的既有接口（`proxy_pool.go`）：
- `AddProxy(socks5, host, port, source='free')` — `source` 必须标 `free`，铁律是探测调度只碰 free 源。
- 二轮测活：不只 TCP 连通，要求**真实出口 IP**（经代理访问 `api.ipify.org`）与节点 IP 一致才算 alive。
- StagVPN 的 `free_server_timer: 14700`（≈4 小时）暗示免费会话有时限 → 池子需要 4h 级别的拨号重建逻辑。

## 2. Wolf Custom 线（存档价值，不可用）

- 密钥体系已完整还原，方法学可复用到同族 APK（见 docs/PROTOCOL.md）。
- 云端 `strongteam.co/api/wolfcustom/newv1.txt` 404；内置节点 `sg.phfiles.com` 全端口超时。
- **没有可接入的活节点**。若后续新版本 APK 更新了云端配置，用 `tools/decrypt_wolf.py` 直接解。

## 3. Bee VPN 线（未闭环）

- lsparanoid 字符串层全破（`bee_strings_all.json` 7109 条）。
- Go 侧 `Libv2ray.do_` 的 AES key 未提取成功：纯穷举（crib-drag 全库扫描 ×17 nonce 偏移）已排除，说明 Bee 的加密与 Wolf 同族但 key 不在常规静态区，或分块流式 GCM（密文 624KB、len%16=9 支持该假设）。
- **待做路线**：重建 Android 模拟器（旧 D:\android-sdk 已删）+ Frida hook `Java_libv2ray_Libv2ray_do_`，运行时取明文。环境要求：AVD API 30+ arm64、frida-server 16.x、装 Bee APK → hook 点在 `com.v2ray.ang.Hometab$Companion.a()` 调用链。

## 4. 文件索引

| 文件 | 说明 |
|------|------|
| `tools/lsparanoid_deobf.py` | lsparanoid 字符串混淆还原器（通用） |
| `tools/dump_strings.py` | 全量字符串 dump（需指定 Deobfuscator 类路径） |
| `tools/decrypt_wolf.py` | Wolf AES-256-GCM 配置解密器 |
| `tools/gen_ovpn_pool.py` | StagVPN 节点 → 批量 ovpn + 拨号编排（本单新增，对接会话用） |
| `docs/PROTOCOL.md` | 三 APK 协议手册（密钥/格式/端点全量） |
| `docs/REVERSE_REPORT.md` | 完整逆向报告 |
| `samples/*.json` | 脱敏样表（RFC5737） |
| `demo/` | 本地面板（127.0.0.1:8951） |
| `.gitignore` | 真实 IP/凭据/运行期产物不入库 |

## 5. 给对接会话的验收标准

1. 能跑 `python tools/gen_ovpn_pool.py --probe` 列出当前免费节点及连通性。
2. 至少 1 个 StagVPN 节点拨号成功且出口 IP 验证通过（`已验证` 级证据：openvpn 日志 + ipify 返回）。
3. SOCKS5 入口进 proxy_pool 且 `TraceProbes` 二轮测活通过。
4. 文档同步：实际接入的节点数、失败原因清单。
5. 不改本机系统代理设置；所有探测走显式代理参数（老规矩）。
