---
name: fe-form-validation
pack: frontend:common
description: 编写表单校验时的规范——客户端校验只为体验不可信、校验规则与后端同源(共享 schema)、即时反馈、必须覆盖错误路径而非只写 happy path。
when_to_use: 新增/修改表单、输入校验、提交逻辑,或 review 校验是否与后端一致时。
when_NOT_to_use: 无用户输入的只读页面、纯展示组件。
---

# Skill: 前端表单校验

## 强制规则
1. **客户端校验 ≠ 可信** — 前端校验只为即时体验;后端必须独立再校一遍,前端绕过不代表安全。见 secure-coding。
2. **规则与后端同源** — 用共享 schema(zod/yup)前后端复用,禁前端手写一套、后端另写一套导致漂移。
3. **即时且非侵入反馈** — 失焦(blur)后校验单字段,提交时校验全部;别每次 keystroke 就报红。
4. **覆盖错误路径** — 处理空值、超长、非法字符、网络失败、后端返回的字段级错误;禁只测填对的情况。
5. **提交态防重** — 提交中禁用按钮 + loading,防双击重复提交。

## schema 同源示例

```ts
// shared/schema.ts —— 前后端同一份
import { z } from 'zod';
export const signupSchema = z.object({
  email: z.string().email(),
  age: z.number().int().min(18),
});
export type Signup = z.infer<typeof signupSchema>;

// 前端:即时校验
const result = signupSchema.safeParse(form);
if (!result.success) setErrors(result.error.flatten().fieldErrors);
// 后端:同一 schema 再校一次,不信任前端
```

## 反模式
- ❌ 只信前端:后端直接落库前端传来的数据,无独立校验 —— 攻击者绕过前端即注入脏数据。
- ❌ 规则漂移:前端 `age >= 18`、后端忘了校 —— 或反之,行为不一致。
- ❌ 只写 happy path:
  ```tsx
  const onSubmit = async () => { await api.save(form); nav('/done'); };
  // 无 try/catch、无字段级后端错误回填、无 loading —— 失败时用户一脸懵
  ```
- ❌ keystroke 即报红:输入第一个字符就 "邮箱格式错误",体验糟糕;改为 blur 后校验。

## 判定标准
故意留空、填超长、断网、让后端返回 422,表单是否都给出清晰的字段级提示且不崩?否则不合格。异步失败的兜底见 fe-error-boundary。Vue 等价:VeeValidate + zod,同源原则不变。
