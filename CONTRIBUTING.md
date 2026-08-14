# 协作开发说明

## 开始开发

```bash
git switch main
git pull --ff-only
git switch -c feature/简短功能名
```

一个分支只处理一个明确问题。提交信息使用简短动词说明结果，例如 `feat: add portable demo workflow`。

## 提交前检查

```bash
python -m unittest discover -s 99_System_OpenClaw/tests
python 99_System_OpenClaw/scripts/06_check_outline_contract.py . --skip-obsidian-sync
python 99_System_OpenClaw/scripts/36_validate_review_capability_registry.py
python 99_System_OpenClaw/scripts/40_check_repository_safety.py
```

修改作品审核能力时，还要完成 `.github/PULL_REQUEST_TEMPLATE/review-capability-change.md` 中的单一事实源检查。

## 数据安全

- 不提交真实照片、视频、音频、剪辑工程、AI 分析产物或云端任务结果。
- 不提交 `.env`、访问令牌、Cookie、私钥或本机账号配置。
- 测试素材必须在测试运行时合成，不能从个人项目复制。
- 如果 `git status` 出现媒体文件或个人项目路径，先停止提交并检查忽略规则。

## Pull Request

PR 说明至少写清：问题、实现、验证命令和仍未覆盖的本机集成。代码评审通过且 GitHub Actions 通过后再合并。
