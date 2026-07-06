---
name: mobile-navigation
pack: frontend:mobile
description: 移动端导航——栈/Tab/深链结构清晰、返回行为可预期、参数最小化传递、导航态与业务态解耦，禁止在导航参数里塞大对象或用导航栈存业务数据。
when_to_use: 设计或修改 RN/Flutter 的路由结构、Tab、深链、返回逻辑、页面间传参时。
when_NOT_to_use: 单页面内部 UI 逻辑，或与页面跳转/路由无关的改动。
---

# Skill: 移动端导航

## 强制规则

1. **导航态 ≠ 业务态** — 路由参数只传标识符(id/type),业务数据从 store/query 拉;禁止把大对象或可变实体塞进导航参数。
2. **返回行为可预期** — 遵循平台栈语义:Android 硬件返回键必须处理;深链进入的页面返回时应回到合理父级,而非直接杀应用。
3. **深链集中声明** — 所有 URL 映射在一处 linking 配置声明,禁止散落在各页面手写解析。
4. **传参最小化且可序列化** — 参数必须可 JSON 序列化(为深链/状态恢复);禁止传函数、类实例、图片二进制。
5. **类型化路由** — 路由名与参数用类型系统约束,禁止字符串魔法值满天飞。

## 传参:传 id 而非对象

```tsx
// ❌ 把整个业务对象塞进导航参数——无法深链、无法恢复、易过期
navigation.navigate('OrderDetail', { order: bigOrderObject });

// ✅ 只传标识,详情页自己拉最新数据
navigation.navigate('OrderDetail', { orderId: order.id });

function OrderDetail({ route }) {
  const { orderId } = route.params;
  const { data: order } = useOrderQuery(orderId); // 单一数据源
}
```

## 深链集中声明(React Navigation)

```tsx
const linking = {
  prefixes: ['myapp://', 'https://app.example.com'],
  config: {
    screens: {
      Home: 'home',
      OrderDetail: 'orders/:orderId', // 参数从 URL 解析,与手动 navigate 同构
    },
  },
};
<NavigationContainer linking={linking} />
```

## Android 返回键

```tsx
useEffect(() => {
  const sub = BackHandler.addEventListener('hardwareBackPress', () => {
    if (canGoBack) { goBack(); return true; }
    return false; // 交还系统默认行为
  });
  return () => sub.remove();
}, [canGoBack]);
```

**Flutter 等价要点:** 用 `go_router` 声明式路由 + `GoRoute(path)` 集中管理深链;返回用 `PopScope`(替代已废弃的 `WillPopScope`)拦截;传参走 `pathParameters`/`queryParameters` 而非直接传对象。

## 反模式
- ❌ 导航参数传大对象/实体 → 无法深链、状态恢复丢失、数据过期
- ❌ 用导航栈当业务状态容器(靠"栈里有没有某页"判断业务逻辑)
- ❌ 深链解析散落各页面手写 `parseUrl`
- ❌ 忽略 Android 硬件返回键,导致深链进入后直接退出应用
- ❌ 路由名/参数用裸字符串,无类型约束
