---
name: desktop-packaging
pack: frontend:desktop
description: 桌面多平台打包规范——mac/win/linux 三端产物矩阵、体积优化(裁 devDeps/asar/瘦运行时)、原生依赖按平台预编译、macOS 签名+公证(notarization)、CI 各平台原生构建。
when_to_use: 配置或改动打包(electron-builder、Tauri bundle)、产物格式、签名公证、原生模块(.node)、CI 跨平台构建时。
when_NOT_to_use: 仅本地 dev 运行、不出安装包的改动。
---

# Skill: 桌面多平台打包

产物直接进用户机器,签名/公证缺失会被系统拦截,体积臃肿劝退安装。

## 强制规则
1. **三端产物明确格式**:mac=`dmg`/`zip`(arm64+x64,优先 universal 或分架构)、win=`nsis`(+可选 msi/portable)、linux=`AppImage`+`deb`/`rpm`。
2. **必须签名**:macOS 用 Developer ID 签名并 **notarize + staple**;Windows 用 Authenticode(EV 证书免 SmartScreen 冷启动警告)。不签的包在新系统会被 Gatekeeper/SmartScreen 拦。
3. **原生依赖按目标平台/架构预编译**;禁止在错误架构上打包 prebuilt `.node`。交叉打包时用对应平台的 runner。
4. **体积优化**:`files` 白名单只打运行期文件、排除 `devDependencies`/源码/测试;开 `asar`;大资源走 `extraResources` 或按需下载。
5. **CI 在各自原生平台构建**(mac→macos runner、win→windows runner);签名密钥经加密 secret 注入,禁止入库。
6. **产物可复现且带版本/校验和**,配合自动更新的 `latest.yml`/blockmap 一并产出。

## 代码

Electron(electron-builder)—— 产物矩阵 + 瘦身 + 公证:
```jsonc
// electron-builder.yml
"files": ["dist/**", "!**/*.map", "!node_modules/**/{test,__tests__}/**"],
"asar": true,
"mac": {
  "target": [{ "target": "dmg", "arch": ["arm64", "x64"] }],
  "hardenedRuntime": true,
  "notarize": { "teamId": "TEAMID" }        // 需 APPLE_ID / APPLE_APP_SPECIFIC_PASSWORD
},
"win": { "target": ["nsis"], "signtoolOptions": { "certificateSubjectName": "MyCorp" } },
"linux": { "target": ["AppImage", "deb"], "category": "Utility" }
```
原生模块用 `@electron/rebuild` 对 Electron ABI 重编:
```bash
npx electron-rebuild -f -w better-sqlite3   # 按 Electron 的 Node ABI 重编 .node
```

Tauri —— bundle 目标 + 签名:
```json
// tauri.conf.json
{ "bundle": { "active": true, "targets": ["dmg", "nsis", "appimage", "deb"],
  "macOS": { "signingIdentity": "Developer ID Application: MyCorp (TEAMID)",
             "hardenedRuntime": true, "entitlements": "entitlements.plist" } } }
```
```bash
# macOS 公证(Tauri 输出后)
xcrun notarytool submit App.dmg --apple-id "$APPLE_ID" --team-id TEAMID --wait
xcrun stapler staple App.dmg
```
> Tauri 因不打包 Chromium(用系统 WebView)天然体积小;仍需确保原生 crate 按目标 target 编译。

## 反模式
- ❌ macOS 产物只签不公证(Gatekeeper 首次打开报"已损坏/无法验证")
- ❌ 在 x64 机器上直接产 arm64 dmg 而不做交叉/原生构建
- ❌ 把整个 `node_modules`(含 devDeps)打进 asar,包体翻倍
- ❌ 签名证书/私钥提交入库或写死在 CI 脚本
- ❌ prebuilt `.node` 与 Electron ABI 不匹配 → 运行时 `MODULE_VERSION` 崩

## 判定标准
- 三端各有明确 target 且架构齐备 → 通过
- mac 包已 notarize+staple、win 包已 Authenticode 签名 → 通过
- `files` 为白名单、asar 开启、devDeps 被排除 → 通过
- 原生模块按目标 ABI/target 重编,CI 用原生 runner → 通过
