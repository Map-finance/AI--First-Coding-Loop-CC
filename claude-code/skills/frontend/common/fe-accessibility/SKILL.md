---
name: fe-accessibility
pack: frontend:common
description: 构建可交互 UI 时的无障碍规范——语义化标签优先于 div、键盘完全可达、focus 管理、正确 aria 用法、颜色对比达标、表单控件与 label 关联。
when_to_use: 新增按钮/链接/表单/弹窗/菜单等交互组件,或 review UI 可访问性时。
when_NOT_to_use: 纯后端逻辑、构建配置、与渲染无关的改动。
---

# Skill: 前端无障碍 (a11y)

## 强制规则
1. **语义标签优先** — 能用 `<button>`/`<a>`/`<nav>`/`<main>` 就不用 `<div onClick>`;原生元素自带键盘与焦点行为。
2. **键盘完全可达** — 所有鼠标可做的操作,`Tab` + `Enter`/`Space`/`Esc` 也要能做;禁 `tabIndex > 0`(打乱顺序)。
3. **焦点管理** — 弹窗打开时焦点移入并陷阱在内(focus trap),关闭后归还给触发元素。
4. **aria 补充而非替代** — 只有语义不足时才加 `role`/`aria-*`;别给 `<button>` 再加 `role="button"`。图标按钮必须有 `aria-label`。
5. **对比度达标** — 正文对比 ≥ 4.5:1,大字 ≥ 3:1;禁只靠颜色传达状态(加图标/文字)。
6. **表单 label 关联** — 每个输入用 `<label htmlFor>` 或包裹关联;禁只放 placeholder 当标签。

## 反模式
- ❌ 假按钮:
  ```tsx
  <div onClick={submit}>提交</div>  // 不可 Tab 聚焦、Enter 无效、读屏不识别
  ```
  改用 `<button onClick={submit}>提交</button>`。
- ❌ 图标按钮无名:
  ```tsx
  <button><TrashIcon /></button>  // 读屏只念 "按钮"
  <button aria-label="删除"><TrashIcon /></button>  // 正确
  ```
- ❌ placeholder 当 label:`<input placeholder="邮箱" />` —— 聚焦后提示消失,读屏不稳。
- ❌ 仅颜色表意:红色边框表示错误但无 `aria-invalid`/文字 —— 色盲用户无感知。见 fe-form-validation 的即时反馈。

## 判定标准
拔掉鼠标,只用键盘能否完成全部流程?读屏(VoiceOver/NVDA)能否念出每个控件的名称与状态?任一否即不合格。Vue 等价:同样原则,`v-on:click` 挂在 `<div>` 上同样违规。
