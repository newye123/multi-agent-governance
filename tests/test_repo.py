#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""仓库自检：案例、链接、脱敏、frontmatter、资源清单。

为什么需要这些测试：这套规则的核心是「未复验不记账」，
那么仓库自己说「有三个真实案例」就必须真的有三个、真的可点开、真的不含客户信息。
不然它就是它自己批判的那个东西。

六组断言：

1. 结构   —— 每个案例有固定的六节骨架，且长度够（不是占位）
2. 索引   —— cases/README.md 覆盖全部案例，且每份案例都被 SKILL.md 引用
3. 链接   —— 所有相对链接可解析（不是死链）
4. 脱敏   —— 公开仓库里没有公司名/品牌名/SKU/客户文案
5. 元数据 —— SKILL.md frontmatter 齐全，version 合法
6. 资源   —— SKILL.md 的 Resources 清单与 references/ 目录双向一致
"""

from __future__ import annotations

import os
import re
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
CASES = os.path.join(ROOT, "cases")
REFS = os.path.join(ROOT, "references")
DOCS = os.path.join(ROOT, "docs")
SKILL = os.path.join(ROOT, "SKILL.md")
CASES_README = os.path.join(CASES, "README.md")

# 必须不出现的串。宁短勿长：太宽的词会产生假警报，假警报会被人删掉，比不设还糟。
BANNED = [
    "图译", "工坊", "tuyigf", "SmallRig", "斯莫格",
    "5775", "6746", "yt-visual", "飞书", "镜已",
]

# 每个案例必须有的节。少一节就不是案例，是感想。
REQUIRED_SECTIONS = ["现象", "取证", "结论", "可迁移的判据"]

MIN_CHARS = 800


def case_files() -> list[str]:
    return sorted(
        os.path.join(CASES, f)
        for f in os.listdir(CASES)
        if f.endswith(".md") and f.lower() != "readme.md"
    )


def read(path: str) -> str:
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def md_links(text: str) -> list[str]:
    """抽取 markdown 相对链接（跳过 http/https/锚点）。"""
    out = []
    for m in re.finditer(r"\[[^\]]*\]\(([^)]+)\)", text):
        target = m.group(1).strip()
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        out.append(target.split("#")[0])
    return out


class TestCaseStructure(unittest.TestCase):
    def test_at_least_three_cases(self):
        self.assertGreaterEqual(
            len(case_files()), 3,
            "至少要有三个案例，否则「真实案例」是空话",
        )

    def test_every_case_has_required_sections(self):
        for path in case_files():
            body = read(path)
            for sec in REQUIRED_SECTIONS:
                with self.subTest(case=os.path.basename(path), section=sec):
                    # 必须锚到行尾。只写 `^##\s+取证` 会被 `## 取证材料（改坏了）`
                    # 这种前缀命中 —— 这一条是负控抓出来的，不是想出来的。
                    self.assertRegex(
                        body, rf"(?m)^##\s+{sec}\s*$", f"{path} 缺一节：## {sec}",
                    )

    def test_every_case_is_long_enough(self):
        for path in case_files():
            with self.subTest(case=os.path.basename(path)):
                self.assertGreaterEqual(
                    len(read(path)), MIN_CHARS,
                    f"{path} 太短，像是占位而不是案例",
                )

    def test_every_case_shows_a_real_reading(self):
        """案例里必须有可核的东西：命令块或 file:line 或退出码。"""
        for path in case_files():
            body = read(path)
            with self.subTest(case=os.path.basename(path)):
                has_evidence = (
                    "```" in body
                    or re.search(r"rc\s*=\s*\d", body)
                    or re.search(r"\$\?", body)
                )
                self.assertTrue(has_evidence, f"{path} 没有任何可核的读数")


class TestCaseIndex(unittest.TestCase):
    def test_cases_readme_links_every_case(self):
        index = read(CASES_README)
        for path in case_files():
            name = os.path.basename(path)
            with self.subTest(case=name):
                self.assertIn(name, index, f"cases/README.md 没有索引 {name}")

    def test_skill_links_at_least_three_cases(self):
        body = read(SKILL)
        linked = [t for t in md_links(body) if t.startswith("cases/")]
        self.assertGreaterEqual(
            len(linked), 3, "SKILL.md 应至少引用三个案例",
        )

    def test_skill_case_links_resolve(self):
        body = read(SKILL)
        for target in md_links(body):
            if not target.startswith("cases/"):
                continue
            with self.subTest(link=target):
                self.assertTrue(
                    os.path.exists(os.path.join(ROOT, target)),
                    f"SKILL.md 里的链接是死链：{target}",
                )


class TestLinks(unittest.TestCase):
    def test_all_relative_links_resolve(self):
        """案例、references、docs 与 README 里的每个相对链接都必须可解析。"""
        targets = [(CASES, f) for f in sorted(os.listdir(CASES)) if f.endswith(".md")]
        targets += [(REFS, f) for f in sorted(os.listdir(REFS)) if f.endswith(".md")]
        if os.path.isdir(DOCS):
            targets += [(DOCS, f) for f in sorted(os.listdir(DOCS)) if f.endswith(".md")]
        targets.append((ROOT, "README.md"))

        for directory, fname in targets:
            path = os.path.join(directory, fname)
            for target in md_links(read(path)):
                with self.subTest(file=fname, link=target):
                    resolved = os.path.normpath(os.path.join(directory, target))
                    self.assertTrue(
                        os.path.exists(resolved),
                        f"{fname} 里的链接是死链：{target}",
                    )


class TestDesensitization(unittest.TestCase):
    def test_no_banned_strings(self):
        me = os.path.abspath(__file__)
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                if os.path.abspath(path) == me:
                    continue  # 黑名单本身在这个文件里
                if not fname.lower().endswith((".md", ".py", ".txt", ".yml", ".yaml")):
                    continue
                body = read(path)
                for word in BANNED:
                    with self.subTest(file=os.path.relpath(path, ROOT), word=word):
                        self.assertNotIn(
                            word, body,
                            f"{os.path.relpath(path, ROOT)} 含敏感串：{word}",
                        )

    def test_no_absolute_windows_paths(self):
        """公开仓库不出现本机绝对路径。"""
        me = os.path.abspath(__file__)
        pat = re.compile(r"[A-Za-z]:[\\/](?:Users|工具开发|01_AI)")
        for dirpath, dirnames, filenames in os.walk(ROOT):
            dirnames[:] = [d for d in dirnames if d not in (".git", "__pycache__")]
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                if os.path.abspath(path) == me:
                    continue
                if not fname.lower().endswith(".md"):
                    continue
                with self.subTest(file=os.path.relpath(path, ROOT)):
                    self.assertIsNone(
                        pat.search(read(path)),
                        f"{os.path.relpath(path, ROOT)} 含本机绝对路径",
                    )


class TestFrontmatter(unittest.TestCase):
    def setUp(self):
        self.body = read(SKILL)
        m = re.match(r"^---\n(.*?)\n---\n", self.body, re.S)
        self.assertIsNotNone(m, "SKILL.md 缺 frontmatter")
        self.meta = {}
        for line in m.group(1).splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                self.meta[k.strip()] = v.strip()

    def test_required_keys(self):
        for key in ("name", "description", "version", "license"):
            with self.subTest(key=key):
                self.assertIn(key, self.meta)
                self.assertTrue(self.meta[key], f"{key} 不能为空")

    def test_name_matches_dir(self):
        self.assertEqual(self.meta["name"], "multi-agent-governance")

    def test_version_is_semver(self):
        self.assertRegex(self.meta["version"], r'^"?\d+\.\d+\.\d+"?$')

    def test_description_has_triggers(self):
        """description 里要有触发词，否则不会被路由到。"""
        self.assertIn("触发词", self.meta["description"])

    def test_license_is_nc(self):
        self.assertIn("NC-1.0", self.meta["license"])


class TestResources(unittest.TestCase):
    def test_every_reference_exists(self):
        body = read(SKILL)
        listed = re.findall(r"`references/([^`]+)`", body)
        self.assertGreaterEqual(len(listed), 3, "Resources 至少列三个文件")
        for name in listed:
            with self.subTest(ref=name):
                self.assertTrue(
                    os.path.exists(os.path.join(REFS, name)),
                    f"SKILL.md 引用了不存在的 references/{name}",
                )

    def test_every_reference_is_listed(self):
        body = read(SKILL)
        listed = set(re.findall(r"`references/([^`]+)`", body))
        on_disk = {
            f for f in os.listdir(REFS) if f.endswith(".md")
        }
        for name in sorted(on_disk - listed):
            with self.subTest(ref=name):
                self.fail(f"references/{name} 存在但没在 SKILL.md 里登记")


if __name__ == "__main__":
    unittest.main(verbosity=2)
