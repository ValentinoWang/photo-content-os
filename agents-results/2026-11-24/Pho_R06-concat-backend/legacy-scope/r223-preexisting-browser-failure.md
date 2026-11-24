# R223 浏览器检查在改动前已失败

状态：待处理。此次交付已确认该断言在 Concat 改动之前即存在。

photo-dev 使用 Chrome for Testing 149、Node.js v24.13.0、隔离 Studio 和同一份合成音频。两端均执行 `/bin/bash docs/tasks/concat-backend/verify_legacy.sh browser`，节拍图模块均通过，交互检查退出码均为 `1`。

- [改动前 `4d78b2a` 原始输出](../acceptance/machine/unit/runs/20261124T064619Z-photo-dev-legacy-scope-94ac2e/evidence/r223-browser-4d78b2a.log)
- [改动后 `4225b88` 原始输出](../acceptance/machine/unit/runs/20261124T064619Z-photo-dev-legacy-scope-94ac2e/evidence/r223-browser-4225b88.log)

同一断言位于 `scripts/verify_r223_interactions.mjs:22:170`。

```text
AssertionError [ERR_ASSERTION]: Expected values to be strictly equal:
+ actual - expected

+ 'rgb(21, 32, 33)'
- 'rgb(228, 235, 235)'
```

本批 diff 不含 R223 的前端文件，改动前后浏览器检查同样失败。颜色预期与当前主题之间的关系留给单独的问题排查。
