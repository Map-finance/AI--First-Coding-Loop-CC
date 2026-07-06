---
name: desktop-native-integration
pack: frontend:desktop
description: 桌面原生集成规范——系统托盘/应用菜单/全局快捷键/文件关联/系统通知的实现、权限申请与跨平台差异处理,资源与监听必须随生命周期释放。
when_to_use: 接入托盘、原生菜单、全局快捷键、文件/协议关联、系统通知,或处理其跨平台差异/权限时。
when_NOT_to_use: 纯渲染层的应用内菜单/应用内提示(非系统级),不触达 OS 能力。
---

# Skill: 桌面原生集成

托盘、快捷键、通知触达 OS,平台差异大且需权限;句柄不释放会泄漏、快捷键不注销会残留。

## 强制规则
1. **权限先申请再用**:macOS 通知需授权、全局快捷键在部分平台受辅助功能权限限制;未授权时降级(如应用内提示),不静默失败也不崩。
2. **快捷键注销、句柄释放**:退出时 `unregister` 快捷键(注册前检测冲突),`Tray`/`Menu`/监听器在 `before-quit`/卸载时销毁,避免占用组合键、泄漏与幽灵图标。
3. **处理跨平台差异,不假设 mac 行为**:菜单角色(mac 有 app 菜单、Win/Linux 无)、托盘左右键、通知能力(Linux 依赖 libnotify)、修饰键(`CmdOrCtrl`)分别处理。
4. **文件/协议关联在打包配置声明**,主进程处理 `open-file`(macOS)与 `second-instance` argv(Win/Linux)两条不同入口。
5. **单实例**:注册文件/协议关联的应用应 `requestSingleInstanceLock`,新调用转交已有实例。

## 代码

Electron —— 托盘 + 全局快捷键 + 跨平台差异 + 释放:
```js
const { app, Tray, Menu, globalShortcut, Notification } = require('electron')

let tray
app.whenReady().then(() => {
  tray = new Tray(trayIcon())
  tray.setContextMenu(Menu.buildFromTemplate([{ role: 'quit' }]))

  const ok = globalShortcut.register('CmdOrCtrl+Shift+K', () => toggleWindow()) // 跨平台修饰键
  if (!ok) log.warn('shortcut taken, degrade to in-app only')                    // 冲突则降级
  if (Notification.isSupported()) new Notification({ title: 'Ready' }).show()
})

app.on('open-file', (e, p) => { e.preventDefault(); openPath(p) })   // macOS 文件关联入口
app.on('second-instance', (_e, argv) => openPath(argv.pop()))        // Win/Linux 文件关联入口
app.on('will-quit', () => globalShortcut.unregisterAll())            // 必注销
app.on('before-quit', () => { tray?.destroy(); tray = null })        // 必释放
```

Tauri —— 托盘 + 快捷键 + 通知先查/求权限:
```rust
tauri::Builder::default()
  .plugin(tauri_plugin_notification::init())
  .plugin(tauri_plugin_global_shortcut::Builder::new().build())
  .setup(|app| {
    tauri::tray::TrayIconBuilder::new().build(app)?;
    app.global_shortcut().register("CmdOrCtrl+Shift+K")?; // 退出前 unregister_all
    Ok(())
  });
```
```ts
import { isPermissionGranted, requestPermission, sendNotification } from '@tauri-apps/plugin-notification'
let ok = await isPermissionGranted()
if (!ok) ok = (await requestPermission()) === 'granted'   // 未授权则降级为应用内提示
if (ok) sendNotification({ title: 'Ready' })
```

## 反模式
- ❌ 注册全局快捷键却从不 `unregister`(占用系统组合键,残留)
- ❌ 直接发通知不查权限(macOS 静默丢失,以为成功)
- ❌ 假设有 app 菜单/托盘左键行为一致(Win/Linux 与 mac 不同)
- ❌ 只处理 `open-file` 漏掉 Win/Linux 的 `second-instance` argv;未 `requestSingleInstanceLock` 致双开抢文件
- ❌ `Tray` 存局部变量被 GC → 图标消失;退出不 `destroy` → 幽灵图标

## 判定标准
- 通知/快捷键有权限查询与降级路径,快捷键退出时注销、托盘/菜单退出时释放 → 通过
- 菜单/托盘/通知按平台分支,快捷键用 `CmdOrCtrl` → 通过
- 文件关联同时处理 macOS `open-file` 与 Win/Linux argv,且启用单实例锁 → 通过
