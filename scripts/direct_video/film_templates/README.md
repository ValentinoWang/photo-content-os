# 整片模板清单

清单来自 [motiontemplates/all](https://github.com/motiontemplates/all)，固定提交 `b74e9c9e800cc3158bc16f6e9468f0f560248243`。206 条是索引，不等于可下载源码；仅 385712 的公开包标记 MIT，其余许可未知，需要自行核实并在官网账户中获取。样片和海报只保存链接，不下载。

重建和检查：

```sh
python scripts/direct_video/film_templates.py --build --upstream https://raw.githubusercontent.com/motiontemplates/all/b74e9c9e800cc3158bc16f6e9468f0f560248243/catalog.json
python scripts/direct_video/film_templates.py --check
python scripts/direct_video/film_templates.py --summary
```

公开模板上游没有 materials 字段，记录为 null；其媒体地址取上游顶层地址。许可从固定版本的公开模板元数据读取。
