---
name: desktop-auto-update
pack: frontend:desktop
description: 桌面应用自动更新规范——强制代码签名后校验、分通道(stable/beta)、增量(delta)下发、可回滚、更新失败静默降级不砸用户会话。
when_to_use: 接入或改动自动更新(electron-updater、Tauri updater)、发布通道、签名/公钥校验、回滚逻辑时。
when_NOT_to_use: 无自更新能力的应用(走应用商店分发,由商店托管更新)。
---

# Skill: 桌面自动更新

更新链路 = 向用户机器投递可执行代码。一旦被中间人替换即 RCE。签名校验是 BLOCK 级红线。

## 强制规则
1. **必须代码签名 + 安装前校验签名/公钥**。Electron 用签名安装包(macOS notarized、Windows Authenticode);Tauri updater 必须配 `pubkey` 校验 minisign 签名,禁止空签名。
2. **更新源走 HTTPS 且校验证书**;禁止 HTTP 或忽略 TLS 错误。
3. **分通道**:`stable` 面向全量、`beta` 面向自愿用户;通道来自用户设置,不硬编码,发布 feed 按通道隔离。
4. **增量更新(delta/blockmap)优先**,减小下载量;但完整包必须始终可用作回退。
5. **可回滚**:保留上一版本或记录版本号,更新后启动自检失败能回退到已知好版本。
6. **失败不砸会话**:下载/校验失败只记日志并按当前版本继续运行,下次再试;绝不在用户工作中途强制退出。
7. **不静默重装**:下载完成后提示用户,由用户选择"重启更新",除非明确的企业策略。

## 代码

Electron(electron-updater)—— 通道 + 失败降级:
```js
const { autoUpdater } = require('electron-updater')
autoUpdater.channel = settings.get('updateChannel', 'stable') // stable | beta
autoUpdater.autoDownload = true
autoUpdater.autoInstallOnAppQuit = true   // 退出时装,不打断会话

autoUpdater.on('update-downloaded', (info) => {
  // 提示用户,由用户决定;不强制 quitAndInstall()
  notifyUser(`新版本 ${info.version} 就绪`, () => autoUpdater.quitAndInstall())
})
autoUpdater.on('error', (err) => {
  log.warn('update failed, keep running current version', err) // 降级,不崩
})
autoUpdater.checkForUpdates()
```
> electron-updater 会自动校验安装包签名(需正确配置签名证书),blockmap 支持差量下载。

Tauri(v2 updater)—— 强制公钥校验:
```json
// tauri.conf.json
{ "plugins": { "updater": {
  "active": true,
  "pubkey": "dW50cnVzdGVkI...",         // 缺失则拒绝安装
  "endpoints": ["https://dl.example.com/{{target}}/{{current_version}}"],
  "dialog": true                          // 提示用户,不静默
}}}
```
```rust
// 回滚思路:更新后启动自检,失败则标记并提示回退
if let Err(e) = self_check() { mark_bad_update(current_version); prompt_rollback(); }
```

## 反模式
- ❌ HTTP 更新源 / `rejectUnauthorized: false`(中间人可注入)
- ❌ Tauri updater 不配 `pubkey`(等于接受任意包)
- ❌ 下载完立刻 `quitAndInstall()` 打断用户工作
- ❌ 通道字符串硬编码,beta 包混入 stable feed
- ❌ 更新失败即 `app.quit()` 或抛未捕获异常
- ❌ 无回退:新版启动崩溃后用户被永久卡死

## 判定标准
- 安装包有效签名 + updater 有签名/公钥校验 → 通过
- feed 按通道隔离且通道读自用户设置 → 通过
- 失败路径只记日志继续跑、成功路径提示后由用户触发重启 → 通过
- 存在回退到上一已知好版本的机制 → 通过
