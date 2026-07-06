---
name: fe-i18n
pack: frontend:common
description: 涉及用户可见文案与本地化时的规范——禁硬编码文案、复数/性别用 ICU、日期货币数字按 locale 格式化、支持 RTL、翻译 key 按命名空间组织。
when_to_use: 新增任何用户可见文本、日期/货币/数字展示、或项目需支持多语言/多地区时。
when_NOT_to_use: 纯内部日志/调试文案、面向开发者的错误码、单语言且明确不国际化的一次性工具。
---

# Skill: 前端国际化 (i18n)

## 强制规则
1. **禁硬编码用户可见文案** — 一切经 `t('key')`;JSX 里出现中文/英文字面量即违规。
2. **复数与性别用 ICU** — 别 `count + ' 项'` 手拼;用 ICU MessageFormat 让翻译方决定形态。
3. **日期/货币/数字按 locale 格式化** — 用 `Intl.DateTimeFormat`/`Intl.NumberFormat`,禁手写 `YYYY-MM-DD` 或 `'$' + n`。
4. **支持 RTL** — 布局用逻辑属性(`margin-inline-start` 而非 `margin-left`),方向随 `dir` 翻转。
5. **key 按命名空间组织** — `checkout.button.pay` 而非扁平 `pay_btn`;禁用译文本身当 key。

## 反模式
- ❌ 硬编码:`<button>结账</button>` —— 无法翻译,改 `<button>{t('checkout.pay')}</button>`。
- ❌ 手拼复数:
  ```tsx
  <span>{count} 条消息</span>  // 英文 1 message / 2 messages 无法处理
  // ICU:t('inbox.count', { count })  →  "{count, plural, one {# message} other {# messages}}"
  ```
- ❌ 手写本地化:
  ```tsx
  `$${price.toFixed(2)}`  // 忽略货币符号位置、千分位、地区
  new Intl.NumberFormat(locale, { style: 'currency', currency: 'USD' }).format(price)  // 正确
  ```
- ❌ 用中文当 key:`t('提交订单')` —— 文案一改 key 全断。

## 判定标准
切到德语(长词)、阿拉伯语(RTL)、英语(复数)三种 locale,布局不溢出、方向正确、复数/日期/货币正确即合格。金额展示同时见 financial-numerics(精度)。Vue 等价:`vue-i18n` 的 `$t()` 与 `<i18n-t>`,规则一致。
