# 08.04 素材已进正式项目：分析、匹配、分镜与 EDL

> 情形编号：`08.04`。  
> 适用情形：素材已经进入 `01_Project_Workspace/主题集合/项目目录/`，现在要把项目素材变成 AI 可读证据，并对照 brief / script 生成素材匹配、Storyboard 和 EDL。

## 前置条件

```text
01_Project_Workspace/主题集合/项目目录/
```

项目内应该已有素材，或已经把 `待增加/` 合并完成。

云端项目包最好已有：

```text
02_project_brief.md
04_script.md
```

## 第一步：补齐项目结构

```bash
python3 99_System_OpenClaw/scripts/13_ensure_project_structure.py "01_Project_Workspace/主题集合/项目目录"
```

## 第二步：分析项目素材

```bash
./99_System_OpenClaw/scripts/run_analyze_project.sh "01_Project_Workspace/主题集合/项目目录"
```

产物：

```text
_ai_analysis/media_manifest.json
_ai_analysis/keyframes/
_ai_analysis/prompts/
_ai_analysis/summaries/
_ai_analysis/project_overview.md
```

## 第三步：对照 brief 匹配素材

Mac Runner / Codex 使用能力：

```text
match_materials_to_brief
```

本地脚本：

```text
17_match_materials_to_brief.py
```

产物：

```text
03_material_match_report.md
08_local_assets.md
```

## 第四步：生成 Storyboard 和 EDL

Mac Runner / Codex 使用能力：

```text
generate_storyboard_edl
```

本地脚本：

```text
18_generate_storyboard_edl.py
```

产物：

```text
05_storyboard.md
06_edit_decision_list.json
```

## 不要做

```text
不要让脚本替代最终审美判断。
不要让 AI 做最终删除决定。
不要把 _ai_analysis 当作 iCloud 照片精选库。
不要跳过 brief / script 就直接生成 EDL。
```

## 下一步

```text
需要进入剪映
-> 看 08.05

只需要回云端改脚本
-> 腾讯云读取 03_material_match_report.md / 05_storyboard.md / 06_edit_decision_list.json 后修订 04_script.md
```
