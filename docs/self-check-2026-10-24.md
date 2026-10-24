# 自检记录：2026-10-24

> 用本仓库自己的判据查本仓库。**第一次跑，负控 1 是绿的。**
> 这份文件记的是那次失败，以及修完之后五次负控的实测读数。

## 基线

```bash
$ python -m unittest discover -s tests
Ran 17 tests in 0.025s
OK
```

17 条，六组：案例结构 / 索引 / 链接 / 脱敏 / frontmatter / 资源清单。

## 负控 1：破坏案例的节标题

```bash
$ F=cases/03-two-writers-one-tree.md
$ BEFORE=$(sha256sum "$F" | cut -d' ' -f1)
$ echo $BEFORE
8a0f1f136cfc977d736b5fb44128ecea16301d937fb6e00f3e8b4d46d6ac1c09

$ sed -i 's/^## 取证$/## 取证材料（改坏了）/' "$F"
$ python -m unittest discover -s tests
Ran 17 tests in 0.020s
OK                    ← 负控没红。守卫失效。
```

**注入成功（`grep -c "^## 取证$"` 返回 0），但测试仍然全绿。**

### 根因

断言写的是：

```python
self.assertRegex(body, rf"(?m)^##\s+{sec}", ...)
```

`re.search` 是**前缀匹配**。`## 取证材料（改坏了）` 以 `## 取证` 开头，
所以这条断言通过了——它验证的是「有个以『## 取证』开头的行」，
而想要的语义是「有一个恰好叫『取证』的二级标题」。

这正是本仓库在讲的那一类病：**门在场 ≠ 门被走到。**
护栏写得像护栏，跑起来也绿，但它守的不是那个东西。

### 修法

锚到行尾：

```python
# 必须锚到行尾。只写 `^##\s+取证` 会被 `## 取证材料（改坏了）`
# 这种前缀命中 —— 这一条是负控抓出来的，不是想出来的。
self.assertRegex(body, rf"(?m)^##\s+{sec}\s*$", ...)
```

重跑负控：

```bash
$ python -m unittest discover -s tests
AssertionError: Regex didn't match: '(?m)^##\s+取证\s*$'
Ran 17 tests in 0.042s
FAILED (failures=1)          ← 红了

$ cp /tmp/c03.bak "$F"
$ echo "$(sha256sum "$F" | cut -d' ' -f1)"
8a0f1f136cfc977d736b5fb44128ecea16301d937fb6e00f3e8b4d46d6ac1c09   ← 与基线一致
RESTORE-OK
```

## 负控 2–5

脚本化执行，每发都核还原哈希：

| # | 目标 | 注入 | 实测结果 | 还原 |
|---|---|---|---|---|
| 2 | 脱敏 | 案例里插入一个黑名单里的品牌名 | `FAILED (failures=1)` | `RESTORE-OK` |
| 3 | 链接 | 索引里 `02-missing-script.md` → `02-missing-scripts.md` | `FAILED (failures=2)` | `RESTORE-OK` |
| 4 | 资源清单 | 从 `SKILL.md` 删掉 `prior-art.md` 那一行 | `FAILED (failures=1)` | `RESTORE-OK` |
| 5 | frontmatter | 删掉 `license: NC-1.0` | `FAILED (failures=1, errors=1)` | `RESTORE-OK` |

负控 3 红了 2 条不是 1 条，因为改一个字符同时踩了两个守卫：
索引里指向的文件名对不上（索引测试），以及链接解析失败（链接测试）。
这是好事——**两个独立的守卫抓到了同一处破坏**，说明它们不是同一条断言的两次复制。

负控 5 多出 1 条 `error`，因为 `setUp` 里 `self.meta["license"]` 抛了 `KeyError`。
严格说这是守卫的一种粗糙形态：**崩了也是红**，不会被读成绿。
但更好的写法是先断言 key 存在、再断言值，让失败信息说人话。已保留现状，记在这里。

## 还原后的基线

```bash
$ python -m unittest discover -s tests
Ran 17 tests in 0.042s
OK
```

## 这次自检抓到的东西

两条。

### 一（关键）：前缀匹配的断言，会为一个「只是开头像」的东西放行

它和[案例 01](../cases/01-background-agent-killed.md)是同一个家族的：
护栏真实存在、测试真实通过、绿也是真的，但**防护为零**。

区别只在于，案例 01 是「HTTP 路径永远走不到那道护栏」，
这里是「断言永远匹配得上那个错标题」。两者的共同判据是同一句：

> **判断一个绿有没有意义，唯一办法是故意把它弄红一次。**

### 二（记录自己踩的）：这份记录第一版，被自己的脱敏守卫抓了

写完负控 2 那行，我按原样把注入的禁用词写进了表格，作为「注入了什么」的证据。
再跑一次，脱敏守卫红了——**它扫到了这份记录本身**。

三个选项：

| 选项 | 后果 |
|---|---|
| 把那个词从黑名单里删掉 | 最坏。守卫为了迁就记录而自废 |
| 把 `docs/` 加进扫描排除 | 次坏。等于宣布「文档区不脱敏」 |
| **改写记录，不写那个词的字面** | 正确。证据是「注入了一个黑名单里的品牌名」，不是那个名字本身 |

选了第三条。**规则不该为记录让路，记录该为规则改写。**

同一类处理在同作者的另一个仓库里出现过一次：报告引用了一个占位假哈希当证据，
修的是措辞，不是规则。两处都是同一个判断——**削弱守卫永远比改写记录更省事，也永远是错的。**

## 复跑方式

```bash
# 基线
python -m unittest discover -s tests

# 负控 1（手工）
F=cases/03-two-writers-one-tree.md
B=$(sha256sum "$F" | cut -d' ' -f1); cp "$F" /tmp/c03.bak
sed -i 's/^## 取证$/## 取证材料（改坏了）/' "$F"
python -m unittest discover -s tests        # 必须 FAILED
cp /tmp/c03.bak "$F"
[ "$B" = "$(sha256sum "$F" | cut -d' ' -f1)" ] && echo RESTORE-OK
```

CI 里跑的是同一组负控（见 `.github/workflows/ci.yml`），
任一发变绿即构建失败——**守卫自己也要被守卫。**
