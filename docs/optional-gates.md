# Optional Gates(v2.3)

> 三个**可选**门禁:**性能回归 / 镜像漏洞 / 机密扫描**。
> 不在默认必走的 ci-gate / ai-review-gate 里——按需启用,避免把通用模板压成"庞然大物"。
>
> 决策原则(贴墙上):**加一个新检查前先问 3 件事——它能挡的失败近 3 个月真发生过吗?它要的等待时长 vs 它阻止一次失败的回报划算吗?它能不能改成 warn 不 block?**

## 总览

| Gate | 抓什么 | 触发 | 默认阈值 | 关键工具 | 是否要 secret |
|---|---|---|---|---|---|
| **perf-gate** | p95 恶化、错误率上升 | PR + main push | p95 +20% / err 1% | k6 + perf_check.py | 否 |
| **image-scan-gate** | 镜像与依赖 CVE | PR + main + daily 03:00Z | CRITICAL,HIGH | Trivy | 否 |
| **secret-scan-gate** | 提交进来的 token/key | PR + main + weekly 周一深扫 | 任意命中 | gitleaks | 否 |

三个都用 **GitHub Security 标签**沉淀历史(SARIF 上传),长期可跟踪、可分配 owner、可追溯。

---

## 1. perf-gate — 性能回归

### 启用步骤

1. 把 `core/workflows/perf-gate.yml` 拷到目标仓 `.github/workflows/`
2. 把 `core/scripts/perf_check.py` 拷到 `scripts/`
3. 把 `core/scripts/perf-scenarios/` 整个拷到 `scripts/perf-scenarios/`
4. 复制 `example.js` → `<your-scenario>.js`,改 BASE_URL / 路径 / 断言
5. 设 Repo Var `PERF_TARGET_URL`(被压的服务地址,通常是 dev 环境)
6. 在 main 上手动触发一次,生成初始 `state/perf-baseline.json` 并 commit 回仓
7. (可选)分支保护 → required check 加 `perf-gate`

### 关键设计

- **首次跑无基线 → PASS + 写入基线**(不能挡还没存在的事)
- **PR 不更新基线**(防 PR 自己拉低基线给自己开后门)
- **main 用指数平滑(α=0.3)滚动基线**(允许产品自然演进、防一次抖动定永)
- **多 scenario 独立基线**(矩阵跑、互不影响)

### 调阈值

env(在 perf-gate.yml 或 Repo Vars):
- `PERF_P95_REGRESSION_PCT` 默认 20
- `PERF_ERROR_RATE_MAX` 默认 0.01
- `PERF_BASELINE_SMOOTHING` 默认 0.3

### 反模式

- ❌ 把 k6 BASE_URL 指向 prod——会真打你的生产
- ❌ 阈值放太宽(>40%)——失去门禁意义
- ❌ 每个 PR 都"临时放宽"——这是噪音,不是门禁

---

## 2. image-scan-gate — 镜像与依赖 CVE

### 启用步骤

1. 拷 `core/workflows/image-scan.yml` 到 `.github/workflows/`
2. (可选)Repo Var `TRIVY_SEVERITY` 调严重度,默认 `CRITICAL,HIGH`
3. (可选)分支保护加 `image-scan-gate` 为 required
4. (可选)开 GitHub Advanced Security(public 仓免费),让 SARIF 上传到 Security 标签

### 双扫机制

- **fs-scan**:静态扫 repo 里的依赖清单(npm/pip/go/cargo)+ Dockerfile 配置问题。不需要构建镜像,**最快**。
- **image-scan**(matrix):对每个 Dockerfile 真构建,然后扫**镜像 layer 里**的 CVE。慢但准。

### 处理 false positive / 暂无修复的 CVE

- `--ignore-unfixed`(默认开):还没有上游 fix 的 CVE 暂不挡(避免无解烦人)
- `.trivyignore`(repo 根放,每行一个 CVE ID):明确忽略列表,需要写**理由 + 复审日期注释**

### 反模式

- ❌ 把严重度放宽到 `CRITICAL` only——会漏掉很多可被利用的 HIGH
- ❌ 把 `.trivyignore` 当作"先过门禁再说"——永久忽略 = 永久债务,半年内必踩雷

---

## 3. secret-scan-gate — 机密扫描

### 启用步骤

1. 拷 `core/workflows/secret-scan.yml` 到 `.github/workflows/`
2. (强烈推荐)分支保护加 `secret-scan-gate` 为 required check
3. (可选)`.gitleaks.toml` 放 repo 根,自定义规则与 allowlist

### 双扫机制

- **PR**:只扫 `BASE..HEAD` 的新增内容,**快**——专挡"刚提交进来的 token"
- **schedule(周一 04:00 UTC)**:全仓全历史深扫,**慢但全**——补救老 commit 里的泄漏

### 如果真泄漏了

PR 触发 BLOCK 时,**force-push 不够**——攻击者可能已抓到 token。按顺序做:

1. **立即轮换**所有可能泄漏的 token / key(直接去对应平台 revoke + reissue)
2. 用 `git filter-repo` 或 BFG 清理 git 历史
3. 通知所有 fork / clone 该仓的人重新拉
4. 上 audit log 看 token 在被发现前有没有被异常调用

### 反模式

- ❌ 给 force-push 自己合并"反正没人看见"——历史里的 token 在 GitHub raw 缓存里仍能找到几小时
- ❌ 把整个 secret-scan-gate 设成 warn 而非 block——失去意义
- ❌ `.gitleaks.toml` allow 真实的 secret(把 hardcoded API key 加进 allowlist)——这是直接关掉门禁

---

## 一键添加(给现有用户)

```bash
# 在你的仓库根目录
curl -sL https://raw.githubusercontent.com/WILLcis/AI--First-Coding-Loop-CC/main/tools/install.sh \
  | bash -s -- "$PWD"
```

`install.sh` 在 v2.3 起默认拷新 workflow + scripts,**已存在的不覆盖**(同时给出冲突提示)。

## 三选哪个先上?ROI 排序

按"挡到一个真问题的概率 × 配置成本的倒数",**强烈建议顺序**:

1. **secret-scan-gate 先上**——几乎零成本(无 secret、无构建),挡的失败一旦发生代价巨大(token 泄漏)
2. **image-scan-gate 次上**——零成本,新 CVE 周期性出现,自动跑
3. **perf-gate 最后上**——需要先写 scenario + 建基线,但**对线上稳定性影响最大**

三个都启用后,你的 ci-gate / ai-review-gate / perf-gate / image-scan-gate / secret-scan-gate **五条 required check 全部强制 + 不可绕过**——这才是真正意义上的"AI-First 工程门禁"。
