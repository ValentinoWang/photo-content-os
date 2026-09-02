from __future__ import annotations

import unittest
from pathlib import Path

STATIC = Path(__file__).resolve().parents[1] / "desktop" / "static"


class FrontendContractTests(unittest.TestCase):
    def test_ordinary_user_information_architecture(self):
        text = "\n".join(path.read_text(encoding="utf-8") for path in STATIC.iterdir() if path.is_file())
        for label in ["工作台", "整理台", "素材库", "项目", "设置与诊断", "研究与参考", "Brief", "脚本", "剪辑方案", "交付", "发布与复盘"]:
            self.assertIn(label, text)
        for capability in ["AI 只可修改你选中的未锁定内容", "锁定", "版本", "素材留在本机", "系统回收站"]:
            self.assertIn(capability, text)
        for forbidden in ["/Users/", "/home/ubuntu", "Traceback", "OPENAI_API_KEY="]:
            self.assertNotIn(forbidden, text)

    def test_no_build_dependency(self):
        self.assertTrue((STATIC / "index.html").is_file())
        self.assertTrue((STATIC / "app.js").is_file())
        self.assertTrue((STATIC / "styles.css").is_file())
        self.assertFalse((STATIC.parent / "package.json").exists())


if __name__ == "__main__":
    unittest.main()
