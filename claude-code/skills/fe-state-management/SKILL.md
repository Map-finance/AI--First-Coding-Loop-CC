---
name: fe-state-management
pack: frontend:common
description: 决定状态放哪里时的分层规范——本地 useState、跨组件全局 store、服务端数据用 react-query 类缓存;禁把服务端数据塞进全局 store,禁滥用全局态存本可局部的状态。
when_to_use: 新增状态、决定状态归属层、引入全局 store、或 review 状态是否放错层时。
when_NOT_to_use: 纯 UI 结构调整、与状态归属无关的样式/文案改动。
---

# Skill: 前端状态分层

## 三层归属
| 层 | 用什么 | 存什么 |
|----|--------|--------|
| 本地 | `useState`/`useReducer` | 只此组件及子树关心的 UI 态(展开、输入草稿) |
| 服务端缓存 | react-query / SWR / RTK Query | 来自后端、有 loading/error/失效语义的数据 |
| 全局客户端 | zustand / redux / context | 跨路由共享的纯客户端态(主题、登录用户、购物车草稿) |

## 强制规则
1. **服务端数据不进全局 store** — 它有新鲜度、加载态、失效、重取语义,交给 react-query;塞进 redux 会手写一套烂缓存。
2. **默认本地,提升有据** — 先 `useState`;确有 ≥2 个不相邻组件需要读写,才提升到 context/store。
3. **全局态最小化** — 全局只放真正全局的东西;表单临时值、hover、分页页码留在本地。
4. **派生态不存储** — 能由已有 state 算出的值用计算而非新 state,避免不同步。见 fe-perf-budget 的重渲染。

## 反模式
- ❌ 服务端数据进 redux:
  ```tsx
  const users = await api.getUsers();
  dispatch(setUsers(users)); // 无失效、无重取、无 loading —— 手写烂缓存
  ```
  改用:
  ```tsx
  const { data, isLoading, error } = useQuery({ queryKey: ['users'], queryFn: api.getUsers });
  ```
- ❌ 全局态存局部值:把某个 modal 的 `isOpen` 放进全局 store —— 泄露到无关组件,难维护。
- ❌ 派生态冗余:
  ```tsx
  const [items, setItems] = useState([]);
  const [count, setCount] = useState(0); // count 应为 items.length,存了就会不同步
  ```

## 判定标准
问三句:这数据来自后端吗?(→缓存层) 有多少组件真的用它?(1 个→本地) 它跨路由存活吗?(是且纯客户端→全局)。任一层放错即需迁移。Vue 等价:服务端数据用 `@tanstack/vue-query`,全局用 Pinia,别把接口结果堆进 Pinia 当缓存。
