---
name: mobile-list-perf
pack: frontend:mobile
description: 移动端长列表性能——必须虚拟化(FlatList/RecyclerView 而非 map+ScrollView)、item 用 memo、禁 inline 函数/对象当 props、稳定 keyExtractor、图片懒加载与缓存,目标不掉帧。
when_to_use: 渲染可滚动长列表/表格/信息流,或排查列表卡顿掉帧时。
when_NOT_to_use: 固定少量元素(<20 且不增长)的静态布局。
---

# Skill: 移动端长列表性能

## 强制规则

1. **必须虚拟化** — 长列表用 `FlatList`/`FlashList`,禁止 `ScrollView` + `map` 一次渲染全部。
2. **item 组件 memo 化** — 行组件用 `React.memo`;渲染 props 必须稳定,否则 memo 失效。
3. **禁 inline 函数/对象当 props** — `renderItem`、事件回调用 `useCallback`,样式对象提到组件外或 `useMemo`。
4. **稳定 key** — `keyExtractor` 返回稳定唯一 id,禁用数组 index(增删会错位重渲)。
5. **图片懒加载+缓存** — 列表图用支持缓存/占位的组件,按需加载缩略图,禁止直接塞原图。

## 反模式 → 正确写法

```tsx
// ❌ 掉帧三连:非虚拟化 + inline renderItem + inline 样式对象 + index key
<ScrollView>
  {items.map((it, i) => (
    <Row key={i} style={{ padding: 12 }} onPress={() => open(it.id)} data={it} />
  ))}
</ScrollView>

// ✅ 虚拟化 + 稳定引用
const Row = React.memo(({ item, onPress }) => (
  <Pressable onPress={() => onPress(item.id)} style={styles.row}>
    <FastImage source={{ uri: item.thumb }} style={styles.thumb} />
    <Text>{item.title}</Text>
  </Pressable>
));

function List({ items }) {
  const onPress = useCallback((id) => open(id), []);       // 稳定回调
  const renderItem = useCallback(({ item }) => (
    <Row item={item} onPress={onPress} />
  ), [onPress]);
  return (
    <FlatList
      data={items}
      renderItem={renderItem}
      keyExtractor={(it) => it.id}                          // 稳定 key
      getItemLayout={(_, i) => ({ length: ROW_H, offset: ROW_H * i, index: i })} // 定高时跳过测量
      windowSize={7}
      removeClippedSubviews
    />
  );
}
const styles = StyleSheet.create({ row: { padding: 12 }, thumb: { width: 48, height: 48 } });
```

## 判定标准
- 千级列表滚动稳定 60fps(120Hz 屏则 120fps),无长白屏。
- item 组件在滚动中不因父级重渲染而重复渲染(可用 why-did-you-render 验证)。
- 定高列表提供 `getItemLayout`;不定高优先考虑 `FlashList`。

**Flutter 等价要点:** 用 `ListView.builder`/`SliverList`(懒构建)而非 `ListView(children:[...])`;行 widget 尽量 `const` 构造以跳过重建;图片用 `cached_network_image` 懒加载 + 占位;长列表设 `itemExtent` 加速布局。RecyclerView(原生 Android)同理靠 ViewHolder 复用。

## 反模式速查
- ❌ `ScrollView`+`map` 渲染长列表
- ❌ `renderItem={({item}) => <Row .../>}` 每帧新建函数
- ❌ `style={{...}}` inline 对象破坏 memo
- ❌ `keyExtractor` 用 index
- ❌ 列表直接加载原图不缓存不占位
