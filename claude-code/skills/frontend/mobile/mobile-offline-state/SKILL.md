---
name: mobile-offline-state
pack: frontend:mobile
description: 移动端离线优先——本地缓存为单一读源、写操作先乐观更新再排队同步、失败可回滚、冲突显式解决(禁静默覆盖),每条待同步记录带幂等键与版本号。
when_to_use: 实现离线可用、本地缓存与服务端同步、乐观更新、冲突合并的功能时。
when_NOT_to_use: 纯在线只读展示,或无本地持久化需求的页面。
---

# Skill: 移动端离线状态

## 强制规则

1. **本地为读源** — UI 读本地缓存(单一数据源),网络结果写回缓存后再驱动 UI;禁止 UI 直接绑定网络响应。
2. **写=乐观更新+可回滚** — 立即更新本地并入队;失败必须回滚到操作前快照,不能留脏态。
3. **同步队列幂等** — 每条待同步操作带客户端生成的幂等键(clientId),防止重试造成重复写。
4. **冲突显式解决** — 服务端版本冲突时用明确策略(LWW/字段级合并/让用户选),禁止静默覆盖用户改动。
5. **版本标记** — 记录带 `updatedAt`/`version`,同步时携带以便服务端检测冲突。

## 乐观更新 + 回滚(React Query)

```tsx
useMutation({
  mutationFn: (patch) => api.updateTodo(patch),
  onMutate: async (patch) => {
    await qc.cancelQueries({ queryKey: ['todo', patch.id] });
    const prev = qc.getQueryData(['todo', patch.id]); // 快照
    qc.setQueryData(['todo', patch.id], (o) => ({ ...o, ...patch })); // 乐观
    return { prev };
  },
  onError: (_e, patch, ctx) => {
    qc.setQueryData(['todo', patch.id], ctx.prev); // 回滚
  },
  onSettled: (_d, _e, patch) => qc.invalidateQueries({ queryKey: ['todo', patch.id] }),
});
```

## 幂等键 + 冲突检测

```ts
const op = {
  clientId: uuid(),        // 幂等键:服务端据此去重
  entityId: todo.id,
  baseVersion: todo.version, // 乐观锁基线
  patch,
};
await queue.enqueue(op);

// 同步时
const res = await api.sync(op);
if (res.status === 409) {
  // 冲突:不静默覆盖,交给合并策略/用户决策
  await resolveConflict(local, res.serverState);
}
```

**Flutter 等价要点:** 本地库用 `drift`/`isar`,联网监测用 `connectivity_plus`;乐观更新在 `StateNotifier`/`Riverpod` 中改本地 state 并保存 rollback 快照;同步队列持久化到本地表,带 `clientId` 与 `version` 字段。

## 反模式
- ❌ UI 直接渲染网络响应,离线即白屏
- ❌ 乐观更新失败后不回滚,留下永久脏数据
- ❌ 同步无幂等键,弱网重试导致重复下单/重复扣款
- ❌ 冲突时后写覆盖先写(静默 LWW),悄悄吞掉用户编辑
- ❌ 用内存变量当离线队列,应用被杀即丢失待同步操作
