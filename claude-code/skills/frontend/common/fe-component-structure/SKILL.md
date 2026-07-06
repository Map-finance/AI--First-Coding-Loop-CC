---
name: fe-component-structure
pack: frontend:common
description: 编写或重构 React/TS 组件时的结构规范——组件职责单一、受控/非受控边界清晰、props 下钻超过两层改用 composition、容器/展示分离适度而非教条。
when_to_use: 新增组件、拆分大组件、传参层级变深、或 review 组件划分是否合理时。
when_NOT_to_use: 纯样式微调、单一叶子组件的内部逻辑改动、与结构无关的 bug 修复。
---

# Skill: 前端组件结构

## 强制规则
1. **单一职责** — 一个组件要么管数据/状态,要么管渲染;既 fetch 又布局又校验的组件必须拆。
2. **受控/非受控二选一,不混用** — 传了 `value` 就必须传 `onChange`;想要非受控用 `defaultValue`。同一 prop 在受控与非受控间切换会触发 React warning。
3. **props 下钻 ≤ 2 层** — 同一份数据穿透 3 层以上组件,改用 `children`/composition 或 context,别继续下钻。
4. **容器/展示分离要有理由** — 仅当展示组件需被复用或独立测试时才拆;为拆而拆制造无意义的间接层。
5. **props 显式解构 + 类型** — 用 `interface Props` 声明,禁 `props: any`。见 naming-convention。

## 反模式
- ❌ 受控/非受控混用:
  ```tsx
  // value 受控但无 onChange → 输入框只读且报 warning
  <input value={name} />
  ```
- ❌ props 深下钻:
  ```tsx
  <Page user={user}><Header user={user}><Nav user={user}><Avatar user={user}/>
  // 改用 composition:<Header><Avatar user={user}/></Header>
  ```
- ❌ 万能组件:一个 `<UserPanel>` 内部同时 `useQuery`、算分页、渲染表格、弹窗表单 —— 拆成容器 + 展示 + 表单。
- ❌ 过度分离:每个 `<Button>` 都配一个 `<ButtonContainer>` 却无任何逻辑 —— 纯间接层。

正确的 composition 示例:

```tsx
function Card({ header, children }: { header: ReactNode; children: ReactNode }) {
  return <section className="card"><div className="card__hd">{header}</div>{children}</section>;
}
// 用法:结构灵活,无 props 下钻
<Card header={<Title/>}><Body/></Card>
```

## 判定标准
组件超过 ~150 行、或 props 超过 ~7 个、或同时出现 `useEffect` 拉数据与复杂 JSX,即为职责过载,应拆分。Vue 等价:`<script setup>` 中 fetch + 大 template 同理拆为容器组件 + 展示组件。
