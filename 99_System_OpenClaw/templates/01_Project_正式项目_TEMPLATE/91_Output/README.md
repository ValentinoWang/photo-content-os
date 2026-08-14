# Output

成片和导出素材放这里。

建议结构：

```text
V1/
V2/
Final/
HyperFrames/
```

候选成片导出后要跑 `local_output_review`，人工确认后才算 Final。

## 剪映导出规则

| 导出物 | 放哪里 |
| --- | --- |
| 第一版预览 | `V1/` |
| 修改版 | `V2/` |
| 人工确认可发布版 | `Final/` |
| HyperFrames 导出包装素材 | `HyperFrames/` |

封面、发布图、字幕图等临时导出先放项目级缓存：

```text
App_WorkCache/发布图临时导出/
```

确认值得长期回看或复用的封面，再复制到：

```text
80_To_iCloudPhotos_精选入库/02_Cover_Candidates_封面候选/
```

Final 发布版如要进入 iCloud 照片，复制一份到：

```text
80_To_iCloudPhotos_精选入库/06_Final_Output_发布成片与高光/
```
