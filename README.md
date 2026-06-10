# warc_zh_clean

Common Crawl 中文网页清洗 pipeline。从原始 WARC 中提取文本，通过多阶段规则过滤低质量、色情、赌博、垃圾内容，输出适合大模型预训练的干净中文语料。

---

## 项目结构

```
warc_zh_clean/          ← 包根目录（含 __init__.py）
├── config.py           ← 所有阈值常量、DensityRule / QualityThresholds 数据类
├── models.py           ← CleanContext、CleanResult 数据模型
├── pipelines/          ← 流水线框架及 YAML 配置
│   ├── __init__.py     ← build_cleaner_pipeline() 入口
│   ├── executor.py     ← CleanerPipeline、PipelineStep 执行引擎
│   └── configs/
│       └── zh_pipeline.yaml
├── rules/              ← 各步骤规则实现
│   ├── pre_clean.py
│   ├── chapter_filter.py
│   ├── line_clean.py
│   ├── quality_signals.py
│   ├── post_length_filter.py
│   └── ratio_filter.py
└── tests/
    ├── test_pipeline.py
    ├── test_integration_soft_thresholds.py
    └── ...
```

---

## 7 步流水线

```
输入 record {"text": ..., "category_label": ...}
        │
        ▼
[步骤 1] pre_clean          ← URL 替换为 <URL>、非打印字符清除、HTML 实体解码
        │
        ▼
[步骤 2] chapter_filter     ← zlib 压缩比检测、密度规则（DensityRule×24）、
        │                      坏关键词评分（BAD_KEYWORD_WEIGHTS）
        ▼
[步骤 3] set_text_len       ← 计算并写入 ctx.text_len（供后续步骤使用）
        │
        ▼
[步骤 4] line_clean         ← 逐行删除低质量行（LineComboRule 关键词组合规则）
        │
        ▼
[步骤 5] quality_signals    ← 11 项 CCNet/Gopher/RefinedWeb 质量信号检测
        │
        ▼
[步骤 6] post_length_filter ← 清洗后文本长度再次检测（>= MIN_TEXT_LEN=256）
        │
        ▼
[步骤 7] ratio_filter       ← 清洗前后文本长度比率检测（>= 0.5）
        │
        ▼
输出 CleanResult
  clean_rec  非 None → 通过，返回清洗后记录
  dirty_rec  非 None → 拒绝，dirty_rec["new_filter_detail"] 含拒绝原因
```

---

## 快速上手（uv）

```bash
# 安装依赖
uv sync

# 运行测试（222 个，全部应为绿色）
uv run pytest -q

# 本地模式处理（需自行准备输入文件）
uv run python main.py --mode local --input data/raw/ --output data/clean/

# 验证流水线步骤数
python -c "
import sys; sys.path.insert(0, '..')
from warc_zh_clean.pipelines import build_cleaner_pipeline
p = build_cleaner_pipeline()
print(len(p.steps))   # 输出：7
"
```

可选依赖（安装后自动启用额外检测）：

```bash
# 繁简体转换距离检测
uv sync --extra quality

# Spark 分布式处理
uv sync --extra spark
```

---

## 软阈值机制（Soft Thresholds）

### 问题背景

旧版本使用硬性绝对计数阈值，例如：

- `PRE_URL_COUNT_LIMIT = 5`：文本中 `<URL>` 占位符 > 5 则直接拒绝
- `PRE_WECHAT_COUNT_LIMIT = 6`：文本中"微信"出现次数 > 6 则直接拒绝

这种做法对长文章不公平：一篇 5000 字的新闻报道中出现 7 个链接是正常的，但旧规则会误杀。

### DensityRule（密度规则）

`config.py` 中定义了 `DensityRule` 数据类，将绝对计数改为**每千字密度**：

```python
@dataclass(frozen=True)
class DensityRule:
    name: str           # 规则标识符（出现在 reject_detail 中）
    counter: str        # 计数方式：
                        #   "substr:<s>"   → text.count(<s>)
                        #   "regex:<pat>"  → len(re.findall(<pat>, text))
    max_per_kilo: float # 每 1000 字允许的最大命中数（软阈值）
    min_count: int      # 触发规则所需的最少命中数（保护短文）
    category_exempt: tuple  # 豁免的类别标签
```

触发条件：`count >= min_count AND count / len(text) * 1000 > max_per_kilo`

`MISC_DENSITY_RULES` 包含 24 条规则，典型示例：

| 规则名 | counter | max_per_kilo | min_count | 说明 |
|--------|---------|:---:|:---:|------|
| `url_placeholder` | `substr:<URL>` | 2.5 | 3 | URL 占位符密度 |
| `wechat` | `substr:微信` | 3.0 | 3 | 微信相关词密度 |
| `lottery` | `substr:彩票` | 5.0 | 3 | 彩票关键词密度 |
| `reply_day` | `substr:天前回复` | 2.5 | 3 | 论坛时间戳噪声 |
| `datetime_stamp` | `regex:\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}` | 2.0 | 3 | 时间戳堆叠 |

**软阈值效果示例**：

- 旧逻辑：文本含 6 个 `<URL>` → 6 > 5 → **拒绝**（无论文章多长）
- 新逻辑：6 个 `<URL>` 在 2700 字文章中 → 密度 = 6/2700×1000 = **2.22 < 2.5** → **通过**

### 坏关键词评分（BAD_KEYWORD_WEIGHTS）

对色情、赌博等高危词采用加权评分机制：

- 核心词（weight=2.0）：色情、赌博核心词汇
- 边缘词（weight=0.5）：模糊语境下的敏感词

评分计算：`score = Σ min(text.count(kw), 5) × weight`

拒绝条件：`score >= BAD_KEYWORD_SCORE_MIN(3.0) AND score / len(text) * 1000 > BAD_KEYWORD_SCORE_PER_KILO(1.0)`

### QualityThresholds（11 项质量信号）

`QualitySignalsRule` 在流水线步骤 5 中检测以下信号：

| 字段 | 含义 | 拒绝方向 |
|------|------|---------|
| `cjk_ratio` | CJK 字符占比 | 过低（非中文内容）|
| `stopword_hits` | 停用词命中数 | 过低（缺乏自然语言特征）|
| `symbol_ratio` | 特殊符号占比 | 过高（符号堆砌）|
| `digit_ratio` | 数字字符占比 | 过高（数字垃圾）|
| `mean_line_len` | 平均行长度 | 过短（导航/列表页）|
| `ellipsis_line_ratio` | 省略号行占比 | 过高（省略号堆叠）|
| `bullet_line_ratio` | 项目符号行占比 | 过高（纯列表）|
| `terminal_punct_line_ratio` | 终止标点行占比 | 过低（语句不完整）|
| `top_ngram_{2,3,4}_max` | 最高频 n-gram 覆盖率 | 过高（重复内容）|
| `dup_ngram_char_frac_max` | 重复 n-gram 字符占比 | 过高（重复段落）|
| `unique_char_ratio_min` | 最小唯一字符比例 | 过低（内容单一）|

---

## 拒绝记录格式

被拒绝的记录在 `dirty_rec["new_filter_detail"]` 中包含拒绝原因，例如：

```
density:url_placeholder=6/2100     ← 密度规则触发（规则名=命中数/文本长度）
bad_keyword_score=4.5/850          ← 坏关键词评分过高
zlib_full_high                     ← zlib 压缩比 >= 4.0（高度重复内容）
quality_signals:mean_line_len=2.3  ← 质量信号不达标（信号名=实测值）
```
