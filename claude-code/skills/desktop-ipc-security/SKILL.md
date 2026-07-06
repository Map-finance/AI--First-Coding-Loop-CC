---
name: desktop-ipc-security
pack: frontend:desktop
description: Electron/Tauri 主进程↔渲染进程 IPC 的最小权限规范——禁 nodeIntegration、开 contextIsolation、preload 白名单暴露、校验每个 IPC 入参、Tauri 收窄 allowlist/capabilities。
when_to_use: 新增或改动 IPC 通道(ipcMain/ipcRenderer、preload、Tauri command/invoke)、BrowserWindow 安全选项、Tauri allowlist/capabilities 时。
when_NOT_to_use: 纯渲染层 UI、与主进程无数据往来的改动。
---

# Skill: 桌面 IPC 安全

渲染进程 = 不可信区(可能加载远程内容/被 XSS)。主进程 = 有 OS 权限。IPC 是唯一闸口,每条都是 BLOCK 级。应用级安全判断见 secure-coding。

## 强制规则
1. **禁 nodeIntegration + 开 contextIsolation**(Electron 默认已如此,不要改回)。渲染进程永不直接拿到 `require`/`fs`/`child_process`。
2. **preload 只暴露具体函数,不暴露通道字符串**。用 `contextBridge` 暴露语义化 API(`readConfig()`),禁止暴露裸 `ipcRenderer` 或 `ipcRenderer.send`。
3. **每个 IPC handler 校验入参**——类型、范围、白名单。把渲染传来的值当外部输入(见 secure-coding:注入/路径穿越/SSRF)。
4. **禁止把参数直接拼进 fs 路径/shell/SQL**;路径必须 `resolve` 后校验落在允许目录内。
5. **Tauri:allowlist/capabilities 按需最小开**——只开用到的 command,`fs.scope`/`shell` 收窄到具体路径,禁 `all: true`。
6. **限制导航与新窗口**:`will-navigate`/`setWindowOpenHandler` 拦截外链,禁止渲染进程被导航到任意 URL。

## 代码

Electron —— preload 白名单 + handler 校验:
```js
// preload.js —— 只暴露语义函数
const { contextBridge, ipcRenderer } = require('electron')
contextBridge.exposeInMainWorld('api', {
  readConfig: (name) => ipcRenderer.invoke('config:read', name),
})

// main.js —— 校验入参 + 路径收敛
const ALLOWED = new Set(['ui', 'network'])
ipcMain.handle('config:read', async (_e, name) => {
  if (typeof name !== 'string' || !ALLOWED.has(name)) throw new Error('bad key')
  const p = path.resolve(CONFIG_DIR, `${name}.json`)
  if (!p.startsWith(CONFIG_DIR + path.sep)) throw new Error('path escape') // 防穿越
  return JSON.parse(await fs.promises.readFile(p, 'utf8'))
})

new BrowserWindow({ webPreferences: {
  nodeIntegration: false, contextIsolation: true, sandbox: true,
}})
```

Tauri —— command 校验 + 收窄能力:
```rust
#[tauri::command]
fn read_config(name: String) -> Result<String, String> {
    if !matches!(name.as_str(), "ui" | "network") { return Err("bad key".into()); }
    std::fs::read_to_string(config_dir().join(format!("{name}.json"))).map_err(|e| e.to_string())
}
```
```json
// tauri.conf.json —— 只开用到的,scope 收窄
{ "allowlist": { "all": false,
  "fs": { "readFile": true, "scope": ["$APPCONFIG/*"] },
  "shell": { "all": false, "open": false } } }
```

## 反模式
- ❌ `contextBridge.exposeInMainWorld('ipc', ipcRenderer)`(暴露整个 ipcRenderer,等于开后门)
- ❌ `nodeIntegration: true` + 加载远程 URL(XSS 直接提权到 OS)
- ❌ `ipcMain.handle('run', (_e, cmd) => exec(cmd))`(渲染可执行任意命令)
- ❌ `fs.readFile(path.join(DIR, userInput))` 未校验 `..` 穿越
- ❌ Tauri `allowlist.all: true` 或 `shell.scope` 用通配 `.*`

## 判定标准
- preload 暴露面可枚举且全是具体函数 → 通过
- 每个 handler/command 首行即做类型+白名单校验 → 通过
- Electron 三选项(nodeIntegration=false/contextIsolation=true/sandbox=true)齐备,Tauri `all:false` 且 scope 具体 → 通过
