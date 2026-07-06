---
name: mobile-native-permissions
pack: frontend:mobile
description: 移动端原生权限——用时才申请(禁启动即弹)、先讲清用途再触发系统弹窗、拒绝后功能降级不阻断、处理"永久拒绝"引导去设置、iOS/Android 差异与隐私合规文案齐全。
when_to_use: 申请相机/相册/定位/通知/麦克风/通讯录等系统权限,或处理权限被拒的降级逻辑时。
when_NOT_to_use: 不涉及任何系统级权限的纯业务 UI。
---

# Skill: 移动端原生权限

## 强制规则

1. **用时才申请** — 在用户主动触发需要该权限的操作那一刻申请,禁止 App 启动或登录后批量弹权限。
2. **先解释后申请** — 首次申请前用自定义 pre-permission 说明"为什么需要",再触发系统弹窗(系统弹窗只能弹有限次)。
3. **拒绝=降级不阻断** — 被拒后提供有意义的降级路径(如手动输入地址替代定位),禁止死循环弹窗或卡住流程。
4. **处理永久拒绝** — 区分"可再弹"与"blocked/永久拒绝";后者引导用户去系统设置,而非反复调用申请 API。
5. **合规文案齐全** — iOS 的 `Info.plist` usage 描述、Android 的 manifest 声明与运行时权限必须与真实用途一致,文案清晰。

## 用时申请 + 降级(react-native-permissions)

```tsx
import { check, request, RESULTS, PERMISSIONS, openSettings } from 'react-native-permissions';

async function pickWithCamera() {
  const perm = Platform.select({
    ios: PERMISSIONS.IOS.CAMERA,
    android: PERMISSIONS.ANDROID.CAMERA,
  });

  let status = await check(perm);
  if (status === RESULTS.DENIED) {
    await showRationale();          // 先解释用途(自定义 UI)
    status = await request(perm);   // 再触发系统弹窗
  }

  switch (status) {
    case RESULTS.GRANTED:   return openCamera();
    case RESULTS.BLOCKED:                                  // 永久拒绝
      return promptGoToSettings(openSettings);            // 引导去设置,不再弹
    default:                return fallbackToGallery();    // 降级:改用相册/手动
  }
}
```

## 平台差异要点
- **iOS**:usage 描述缺失会直接崩溃/被拒审;权限首次拒绝后系统弹窗不再出现,只能去设置。
- **Android**:危险权限运行时申请;可通过 `shouldShowRequestPermissionRationale` 判断是否被"不再询问";部分权限(如后台定位)需分步申请。
- **通知**:iOS 与 Android 13+ 均需运行时申请,别默认已授予。

**Flutter 等价要点:** 用 `permission_handler`;`status.isPermanentlyDenied` 对应上面的 BLOCKED,调 `openAppSettings()`;`Permission.camera.request()` 前同样先展示 rationale。iOS 文案写 `Info.plist`,Android 写 `AndroidManifest.xml`。

## 反模式
- ❌ App 启动即连弹一堆权限,用户全部秒拒
- ❌ 不先解释直接调系统弹窗,一次拒绝后再无机会
- ❌ 被拒后 while 循环反复 `request`,或直接卡死主流程
- ❌ 永久拒绝还在调 `request`(无效),不引导去设置
- ❌ `Info.plist`/manifest 文案含糊或与实际用途不符 → 审核被拒/合规风险
