---
name: mobile-platform-parity
pack: frontend:mobile
description: iOS/Android 一致性——安全区/刘海/手势区用 SafeArea 而非硬编码、返回键与手势各平台正确处理、字体与阴影/触感差异适配、平台专属代码集中隔离(Platform.select/.ios.tsx)禁散落 if。
when_to_use: 处理跨平台 UI 一致性、安全区、手势返回、字体/阴影差异,或需要平台专属实现时。
when_NOT_to_use: 明确单平台项目,或与平台差异无关的纯逻辑改动。
---

# Skill: 移动端平台一致性

## 强制规则

1. **安全区不硬编码** — 用 `SafeAreaView`/`useSafeAreaInsets` 处理刘海、状态栏、底部手势条;禁止写死 `paddingTop: 44`。
2. **返回语义按平台** — Android 处理硬件返回键;iOS 支持边缘滑动返回(edge-swipe),别禁用默认手势。
3. **平台专属代码隔离** — 差异实现用 `Platform.select` 或 `.ios.tsx`/`.android.tsx` 文件拆分;禁止 `if (Platform.OS==='ios')` 散落满代码。
4. **字体/阴影分平台适配** — 阴影 iOS 用 `shadow*`、Android 用 `elevation`;系统字体、字号度量不同需验证不截断。
5. **触感/交互反馈** — 用平台惯用反馈(iOS Haptics、Android Ripple),而非统一硬套一种。

## 安全区(禁硬编码)

```tsx
// ❌ 硬编码,换机型/横竖屏即错位
<View style={{ paddingTop: 44, paddingBottom: 34 }} />

// ✅ 读真实 insets
const insets = useSafeAreaInsets();
<View style={{ paddingTop: insets.top, paddingBottom: insets.bottom }} />
```

## 平台差异集中隔离

```tsx
// 内联小差异:Platform.select
const styles = StyleSheet.create({
  card: {
    ...Platform.select({
      ios:     { shadowColor: '#000', shadowOpacity: 0.1, shadowRadius: 4 },
      android: { elevation: 3 },
    }),
  },
});

// 大差异:按扩展名拆文件,调用方无感知
// Feedback.ios.tsx / Feedback.android.tsx  →  import Feedback from './Feedback';
```

## 判定标准
- 刘海机型、全面屏手势条、横屏下无内容被裁切或压到系统区。
- Android 返回键与 iOS 边缘滑动返回均行为正确。
- 阴影在两端都可见(非只 iOS 有、Android 全平);字体不截断。
- 平台差异不以裸 `if (Platform.OS)` 形式散落业务组件内。

**Flutter 等价要点:** 安全区用 `SafeArea`/`MediaQuery.padding`;平台判断用 `Theme.of(context).platform` 或 `defaultTargetPlatform`,可直接用 `Cupertino*` 与 `Material*` 组件族区分;返回拦截用 `PopScope`;阴影/触感由各自 widget 族内建,无需手动分平台。

## 反模式
- ❌ 硬编码状态栏/底部安全区高度
- ❌ `if (Platform.OS==='ios')` 分支散落在多个组件里
- ❌ 只写 iOS `shadow*` 导致 Android 无阴影(或反之只写 elevation)
- ❌ 禁用 iOS 边缘滑返 / 不处理 Android 硬件返回键
- ❌ 全平台统一硬套一种交互反馈,违背各自平台习惯
