# -*- coding: utf-8 -*-
"""
P5: End-to-end integration tests for soft-threshold behavior.

Tests are organized in three categories (via build_cleaner_pipeline + pipeline.process):
  1. Clean long Chinese text passes (clean_rec non-None).
  2. Soft-threshold acceptance: texts that old absolute thresholds would have
     killed but the new density rules let through.
  3. High-density garbage is rejected (density: or bad_keyword_score in
     reject_detail) and low-quality structural text is also rejected.

Record structure mirrors tests/test_pipeline.py: {"text": ..., "category_label": ...}
"""

from warc_zh_clean.pipelines import build_cleaner_pipeline

# ---------------------------------------------------------------------------
# Pipeline singleton (avoid rebuilding for every test)
# ---------------------------------------------------------------------------

_PIPELINE = None


def _pipeline():
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = build_cleaner_pipeline()
    return _PIPELINE


def _process(text: str, category: str = "ke_ji"):
    record = {"text": text, "category_label": category}
    return _pipeline().process(record)


# ---------------------------------------------------------------------------
# Diverse clean Chinese paragraphs to avoid zlib repetition detection
# Each paragraph covers a distinct topic (~70-100 chars).
# ---------------------------------------------------------------------------

_PARA_AI = (
    "人工智能大模型在医疗影像诊断领域的应用日益成熟，辅助医生发现早期病变，"
    "相关研究成果已在多家三甲医院落地试点并取得积极效果。"
    "这一趋势正在改变传统医疗流程，显著提升了诊断效率和准确率。"
)

_PARA_ENERGY = (
    "在碳中和目标引领下，光伏和风电装机容量持续扩大，储能技术的降本路径日趋清晰，"
    "绿色电力消费占比逐年上升，有力推动了经济社会向低碳转型的进程。"
    "多省市已完成风光储一体化示范项目，为全国推广提供了宝贵经验。"
)

_PARA_SPACE = (
    "中国空间站已完成在轨建造，神舟系列飞船实现常态化天地往返运输，"
    "航天员在轨驻留时长不断延伸，多项空间科学实验取得重要进展。"
    "这标志着中国在近地空间的长期有人驻留能力进入成熟阶段。"
)

_PARA_EV = (
    "新能源汽车产业实现跨越式发展，比亚迪、宁德时代等企业跻身全球领先行列，"
    "动力电池技术和充电基础设施的持续完善推动了市场渗透率稳步提升。"
    "相关供应链本土化程度大幅提高，降低了对外部进口零部件的依赖。"
)

_PARA_DIGITAL = (
    "数字经济新业态蓬勃兴起，直播电商、跨境电商和即时零售等模式深刻改变了流通格局，"
    "大量农村劳动力通过直播平台实现了就业增收，推动了农村产业振兴。"
    "平台经济监管政策持续完善，促进了行业健康有序发展。"
)

_PARA_HIGHTRAIN = (
    "高铁网络进一步向西部延伸，拉动了沿线地区的旅游和商贸往来，"
    "城际交通时间成本大幅降低，有力推进了区域一体化进程。"
    "多条高铁线路的开通使偏远地区融入了全国一日生活圈。"
)

_PARA_BIO = (
    "生物医药产业在政策支持和市场需求双轮驱动下进入快速发展阶段，"
    "创新药申报数量和审批效率均创历史新高，国产替代空间持续扩大。"
    "多款具有自主知识产权的靶向药物和生物制剂相继上市，打破了进口垄断。"
)

_PARA_EDU = (
    "教育信息化建设取得阶段性成果，线上优质课程资源向农村地区开放共享，"
    "城乡教育差距逐步缩小，学生综合素质评价体系不断完善。"
    "人工智能辅助教学系统在试点学校帮助教师实现了个性化因材施教。"
)

_PARA_CITY = (
    "智慧城市建设以数据治理为核心，整合交通、环保、应急等多类信息，"
    "实现跨部门协同响应，居民服务满意度稳步提升。"
    "多个城市的智能交通系统大幅缓解了早晚高峰拥堵问题。"
)

_PARA_OCEAN = (
    "海洋经济成为沿海省市新的增长极，深远海养殖、海上风电和海洋生物医药"
    "等新兴产业集群初具规模，相关政策支持力度持续加大。"
    "多项深海勘探技术取得突破，为未来开发海洋资源奠定了基础。"
)

_PARA_QUANTUM = (
    "量子计算研究持续推进，超导量子比特和离子阱两大技术路线均取得阶段性突破，"
    "量子纠错码的实验验证为大规模容错量子计算机的研制指明了路径。"
    "多家科研机构正在推进量子通信和量子传感在实际场景中的工程化部署。"
)

_PARA_SEMICONDUCTOR = (
    "半导体产业链自主化进程加快，14纳米以下先进制程取得重要进展，"
    "国产光刻机和刻蚀设备的研发持续推进，国内芯片设计企业的市场份额不断提升。"
    "多地政府加大投入建设集成电路产业园区，集聚了大批高端人才。"
)

_PARA_FINANCE = (
    "绿色金融体系不断完善，碳排放权交易市场纳入更多行业，"
    "绿色债券和绿色信贷规模持续扩大，金融资源引导实体经济绿色低碳转型的作用日益凸显。"
    "多家银行推出了针对可再生能源企业的专项融资产品。"
)

_PARA_RURAL = (
    "乡村振兴战略深入推进，农业现代化水平持续提升，"
    "特色农产品品牌建设和农村电商物流体系不断完善，"
    "农民收入稳步增长，脱贫攻坚成果得到有效巩固。"
)

_PARA_MANUFACTURING = (
    "先进制造业加速向智能化、数字化转型，工业互联网平台加快推广，"
    "企业生产效率和产品质量显著提升，多个行业涌现出一批数字化标杆工厂。"
    "工业机器人装机量居全球前列，有力支撑了制造业高质量发展。"
)

_PARA_HEALTHCARE = (
    "医疗体系改革持续深化，分级诊疗制度和家庭医生签约服务覆盖面不断扩大，"
    "医疗资源配置更加均衡，基层卫生机构服务能力明显提升。"
    "中医药传承创新发展步伐加快，多项中医特色疗法走向海外市场。"
)

# All distinct paragraphs in order
_ALL_PARAS = [
    _PARA_AI, _PARA_ENERGY, _PARA_SPACE, _PARA_EV, _PARA_DIGITAL,
    _PARA_HIGHTRAIN, _PARA_BIO, _PARA_EDU, _PARA_CITY, _PARA_OCEAN,
    _PARA_QUANTUM, _PARA_SEMICONDUCTOR, _PARA_FINANCE, _PARA_RURAL,
    _PARA_MANUFACTURING, _PARA_HEALTHCARE,
]


def _make_diverse_text(min_chars: int = 500) -> str:
    """Build a long, diverse Chinese text without repeating paragraphs.

    Cycles through _ALL_PARAS until min_chars is reached.
    This avoids zlib_full_high which triggers on highly repetitive content.
    """
    parts = []
    total = 0
    cycle_idx = 0
    while total < min_chars:
        para = _ALL_PARAS[cycle_idx % len(_ALL_PARAS)]
        parts.append(para)
        total += len(para)
        cycle_idx += 1
    return "\n".join(parts)


# ===========================================================================
# Category 1: Clean long Chinese text passes
# ===========================================================================


def test_clean_long_news_passes():
    """A 500+ char clean news/encyclopedia article passes the full pipeline."""
    text = _make_diverse_text(min_chars=600)
    assert len(text) >= 500, f"text too short: {len(text)}"
    result = _process(text, category="ke_ji")
    detail = result.dirty_rec.get("new_filter_detail") if result.dirty_rec else "N/A"
    assert result.clean_rec is not None, (
        f"Clean long text was rejected. reject_detail: {detail}"
    )
    assert result.dirty_rec is None


def test_clean_encyclopedia_style_passes():
    """A 500+ char encyclopedia-style article (numbers, English terms) passes."""
    text = (
        "量子计算是利用量子力学原理进行信息处理的新型计算范式，"
        "其基本计算单元称为量子比特（qubit）。"
        "不同于经典比特只能表示 0 或 1，量子比特可通过叠加态同时表示 0 和 1，"
        "从而在特定问题上实现指数级加速。\n"
        "量子纠缠是量子计算的核心资源之一，两个纠缠量子比特无论相距多远，"
        "对其中一个的测量结果都会瞬间影响另一个的状态，"
        "爱因斯坦称之为鬼魅般的超距作用。\n"
        "量子门是量子线路的基本操作单元，常见的量子门包括 Hadamard 门、"
        "CNOT 门和 Toffoli 门等，它们通过幺正变换对量子态进行精确操控。\n"
        "在算法层面，Shor 算法可以在多项式时间内分解大整数，"
        "对现有 RSA 加密体系构成潜在威胁；"
        "Grover 算法则将无结构搜索的时间复杂度从 O(N) 降至 O(sqrt(N))。\n"
        "工程实现方面，主要技术路线包括超导量子比特、离子阱、"
        "拓扑量子比特和光量子计算，"
        "各路线在相干时间、可扩展性和操作保真度上各有优劣。\n"
        "全球主要科技企业和国家级研究机构正加速布局量子计算赛道，"
        "预计在近中期内将在特定领域率先实现量子优势的工程化应用。\n"
        "量子通信方面，量子密钥分发（QKD）技术已在银行、政务等"
        "高安全需求场景完成商用部署，"
        "京沪干线量子保密通信网络是迄今最长的量子通信骨干网络，"
        "全长逾 2000 公里。\n"
        "量子传感器利用量子叠加态对外部物理量的极端敏感性，"
        "在导航、医学成像和地球物理勘探等领域展现出超越经典传感器的精度极限。\n"
    )
    assert len(text) >= 500
    result = _process(text, category="ke_ji")
    detail = result.dirty_rec.get("new_filter_detail") if result.dirty_rec else "N/A"
    assert result.clean_rec is not None, (
        f"Encyclopedia-style text was rejected. detail: {detail}"
    )


# ===========================================================================
# Category 2: Soft-threshold acceptance
# Old absolute thresholds would have killed these texts; density rules let them through.
# ===========================================================================


def test_soft_threshold_url_placeholder_long_article_passes():
    """
    Soft threshold: url_placeholder density rule.

    OLD LOGIC (PRE_URL_COUNT_LIMIT=5, absolute count > 5 => reject):
        7 <URL> placeholders in any text => 7 > 5 => KILLED.

    NEW DENSITY RULE (max_per_kilo=2.5, min_count=3):
        In a 3000+ char article, 7 <URL>:
        density = 7 / 3000 * 1000 = 2.33 < 2.5 => PASS.

    Build: a 3000+ char government-news article (inline, non-repetitive)
    with 7 scattered <URL> placeholders (simulating pre_clean URL replacement).
    The text is unique enough to avoid zlib_full_high rejection.
    """
    # A government-policy news article, ~2700 chars, covering 10 different policy areas.
    # We combine the test_pipeline.py base text with additional unique paragraphs
    # to avoid zlib_full_high while being long enough for the density math to work.
    # 6 <URL> placeholders will be scattered: old logic (>5 = kill) would reject this;
    # new density rule (6/2700*1000 = 2.22 < 2.5) lets it through.
    article = (
        "人工智能技术在近年来取得了突破性的进展，深度学习模型在图像识别和自然语言处理领域表现出色。"
        "云计算平台为企业提供了弹性可扩展的计算资源，降低了基础设施的运维成本和技术门槛。"
        "开源软件生态系统的蓬勃发展促进了技术创新，开发者可以基于现有项目快速构建新的应用。"
        "数据安全与隐私保护成为数字化转型过程中的重要议题，各国相继出台相关法律法规。"
        "物联网设备的广泛部署正在改变城市管理和工业生产的模式，实现更高效的资源调度。"
        "区块链技术在金融领域的应用探索不断深入，去中心化账本为交易验证提供了新的范式。"
        "量子计算的研究进展令人瞩目，虽然仍处于早期阶段，但已展现出解决复杂优化问题的潜力。"
        "边缘计算将数据处理能力推向网络边缘，减少延迟并提高实时响应速度。\n"
        "国家发展和改革委员会日前召开新闻发布会，就新型基础设施建设的进展和下一步工作进行了介绍。"
        "发改委主任表示，5G基站、数据中心和人工智能计算中心是当前重点投资方向，各地已启动专项规划。"
        "针对数据安全问题，委员会将同步推进数据安全标准体系建设，确保数字基础设施的安全可靠运行。\n"
        "工业和信息化部发布了5G网络基站建设的行业标准，要求主要城市核心区域覆盖率年底前达90%以上。"
        "同时明确了频谱资源分配和干扰协调规范，还推动建立5G共建共享机制以减少重复建设和降低成本。\n"
        "生态环境部发布碳排放核查技术指南，规范了控排企业的数据报送和第三方核查流程。"
        "明确了钢铁、电力、建材等重点行业的碳排放核算方法学，为全国碳交易市场规范运行奠定了基础。"
        "首批50家碳排放数据质量优秀企业名单同步公布，在业界树立了标杆和示范效应。\n"
        "商务部公布了最新跨境电商进出口统计数据，上半年总额同比增长23.6%，东南亚和中东增幅突出。"
        "国内产品通过独立站和第三方平台实现大规模出海，商务部同时宣布扩大综试区数量至200个。\n"
        "科技部公布新一批重点研发计划项目，支持量子通信、人工智能芯片和先进储能材料三大领域。"
        "总资助超过百亿元，覆盖全国20余省市，成果将优先向中小企业开放，推动产学研深度融合。\n"
        "教育部要求各地推进学校数字化建设，明年底实现农村学校宽带接入全覆盖并推广网络课程平台。"
        "职业院校将率先推广人工智能和大数据专业课程，配套启动教师数字素养培训项目。\n"
        "国家医保局开展新一轮药品集中带量采购，47种常用药品平均降价56%，部分品种降幅超过80%。"
        "医保局表示将建立动态调整机制，每年滚动纳入新药种，持续扩大集采覆盖面以惠及更多患者。\n"
        "住建部对全国老旧小区改造工作进行中期评估，上半年已完成改造面积近8亿平方米，逾500万户受益。"
        "改造过程中强调尊重居民意愿，杜绝一刀切，注重保留社区历史文化风貌，实现宜居改善。\n"
        "农业农村部推广智慧农业方案，通过卫星遥感和物联网传感器实现精准施肥灌溉，化肥用量降12%。"
        "相关技术已在华北和东北主产区大面积推广，还将在西部地区建设100个示范园推动农业现代化。\n"
        "财政部发布专项债扩容使用通知，允许将更多资金用于新基建项目，并适当延长专项债偿还周期。"
        "同时要求各地建立债务风险管控台账，强化债务透明度，防范局部风险向系统性风险演变。\n"
        "人力资源和社会保障部推出新版职业技能等级认定目录，新增人工智能训练师和数字化管理师等职种，"
        "面向制造业和服务业新兴岗位开展专项技能提升培训，累计培训劳动者逾百万人次。\n"
        "国家市场监督管理总局修订了食品安全抽检管理办法，加大对网络餐饮和生鲜电商的监督抽查频次，"
        "全年抽检批次较上年增加20%，不合格食品核查处置率保持100%。\n"
        "国家卫生健康委推进分级诊疗制度落实，基层医疗机构慢性病患者签约率持续提升，"
        "家庭医生服务包内容不断丰富，有效缓解了三级医院门诊压力，居民就医体验明显改善。\n"
        "交通运输部加快推进快递包装减量化和循环化工作，可循环包装使用比例持续提升，"
        "电商平台和快递企业联合试点托盘和周转箱共享模式，推动绿色物流体系建设取得积极成效。\n"
        "文化和旅游部发布旅游市场秋冬季旅游产品指引，重点推介户外运动、研学旅行和乡村旅游路线，"
        "引导出游需求向淡季分流，多地民宿和特色景区预订量同比增长明显，带动了地方消费。\n"
        "国家能源局发布新能源开发年度计划，风电和光伏新增装机目标大幅上调，"
        "西部大基地送出通道建设加快推进，特高压输电线路跨省跨区消纳规模持续扩大，"
        "新型储能装机容量实现翻倍增长，有力保障了新能源电量全额消纳。\n"
        "水利部宣布新一批大型水库枢纽工程开工建设，重点布局西南水资源丰富地区，"
        "通过调水工程和灌区改造，解决北方农业灌溉用水紧张问题，"
        "完善防洪减灾体系，提升应对极端降水事件的工程调蓄能力。\n"
        "国家林业和草原局公布新增自然保护区和国家公园范围，"
        "全国森林覆盖率持续提升，生物多样性保护工作取得阶段性成效，"
        "多个濒危野生动植物种群数量恢复趋势明显，生态红线划定工作全面完成。\n"
        "应急管理部强化极端天气防灾减灾体系建设，推进基层应急响应能力标准化建设，"
        "卫星遥感和气象预警系统覆盖广度持续提升，灾害预警发布效率大幅改善，"
        "受灾群众转移安置工作更加规范，全国自然灾害综合风险普查成果完成入库。\n"
        "中国人民银行推动金融数字化转型，积极推广数字人民币在交通、餐饮、医疗等场景的应用，"
        "数字人民币累计交易额突破万亿元，覆盖主要城市和地区的试点持续扩展，"
        "数字支付普惠金融属性逐步显现，为偏远地区居民提供了更便捷的支付体验。\n"
        "国防科工委积极推进军民融合深度发展战略，推动卫星导航、无人系统和先进材料等技术的"
        "双向转化应用，多项军工核心技术实现产业化落地，国防科技工业整体实力持续增强。\n"
        "民政部完善城乡社区治理体系，推进社区综合服务设施建设，"
        "推广网格化管理和精细化服务模式，提升基层治理效能，"
        "加强老年人、残疾人等群体的社会保障和公共服务供给水平，"
        "推动社会救助制度改革，使社会福利覆盖面持续扩大，保障水平稳步提升。\n"
        "国家体育总局加快推进全民健身战略，完善城乡公共体育设施配置，"
        "举办各级各类群众性体育赛事，推动青少年体育锻炼习惯养成，"
        "竞技体育和群众体育协调发展的新格局初步形成。\n"
    )
    assert len(article) >= 2400, f"Article too short: {len(article)}"

    # Scatter 6 <URL> placeholders at different positions.
    # OLD LOGIC: absolute count > 5 => KILL (6 > 5 => KILL regardless of text length).
    # NEW LOGIC: density = 6/2600*1000 ≈ 2.31 < 2.5 => PASS.
    url_count_target = 6
    article_chars = list(article)
    total = len(article_chars)
    step = total // (url_count_target + 1)
    for i in range(url_count_target):
        pos = step * (i + 1) + i * 6
        pos = min(pos, len(article_chars))
        article_chars.insert(pos, "<URL>，")
    text = "".join(article_chars)

    url_count = text.count("<URL>")
    text_len = len(text)
    density = url_count / text_len * 1000

    assert url_count == url_count_target, (
        f"Expected {url_count_target} <URL> placeholders, got {url_count}"
    )
    assert text_len >= 2000, f"Text should be >= 2000 chars, got {text_len}"
    assert density < 2.5, (
        f"Density {density:.3f} should be < 2.5 "
        f"(old absolute count >5 would kill any text with {url_count_target} URLs)"
    )

    result = _process(text, category="ke_ji")
    detail = result.dirty_rec.get("new_filter_detail") if result.dirty_rec else "N/A"
    assert result.clean_rec is not None, (
        f"[SOFT THRESHOLD] {url_count_target} <URL> in news article was wrongly rejected. "
        f"Old absolute threshold >5 kills any text with {url_count_target} URLs; "
        f"new density {density:.2f}/kilo < 2.5 should pass. "
        f"reject_detail={detail}"
    )


def test_soft_threshold_wechat_enterprise_article_passes():
    """
    Soft threshold: wechat density rule.

    OLD LOGIC (PRE_WECHAT_COUNT_LIMIT=6, absolute count > 6 => reject):
        8 mentions of 'WeChat' (微信) in any text => 8 > 6 => KILLED.

    NEW DENSITY RULE (max_per_kilo=3.0, min_count=3):
        In a 2700+ char enterprise profile with 8 WeChat mentions:
        density = 8 / 2700 * 1000 ≈ 2.96 < 3.0 => PASS.

    Build: a 2700+ char enterprise digital-transformation article (inline,
    non-repetitive) with 8 WeChat mentions woven in naturally.
    """
    # Inline diverse enterprise article, ~2800 chars, each paragraph unique.
    # 8 occurrences of "微信" are embedded naturally in the narrative.
    # OLD LOGIC (PRE_WECHAT_COUNT_LIMIT=6, absolute > 6 => reject):
    #   8 mentions in any text => 8 > 6 => KILLED.
    # NEW DENSITY RULE (max_per_kilo=3.0, min_count=3):
    #   In a 2700+ char article, density = 8/2800*1000 ≈ 2.86 < 3.0 => PASS.
    text = (
        "某大型连锁零售集团近年来积极推进数字化转型战略，通过整合线上线下渠道资源构建全渠道运营体系。"
        "集团先后引入大数据分析平台和智能选品系统，对消费者购买行为进行实时追踪与深度挖掘分析，"
        "依据分析结果动态调整各门店商品陈列方案和促销资源投放策略，"
        "实现精准运营，坪效和库存周转率均取得了量化的可见提升，在行业内形成了竞争壁垒。"
        "集团还同步推进供应商协同平台建设，实现从订单到发货的全程可视化管控，"
        "供应链响应时效从平均5天缩短至2.5天，库存积压率降低逾18%。\n"
        "在数字支付体系建设方面，集团于三年前率先在旗下所有直营门店接入微信支付作为核心收款渠道，"
        "推出扫码取餐、自助结账等无接触购物模式，消费者扫码支付比例超过70%，"
        "大幅缩短了收银台排队等候时间，极大改善了顾客的整体购物体验和满意度评分。"
        "集团还与多家银行深度合作推出联名信用卡，为忠实会员提供专属积分返还和节假日消费折扣权益，"
        "联名卡激活用户三个月内复购率比普通会员高出约35%。\n"
        "客户服务方面，集团依托微信公众号和企业服务号搭建了全天候智能客服响应体系，"
        "平均客户问题解决时长从原来的4小时大幅压缩至45分钟以内，用户好评率持续提升。"
        "引入智能客服机器人承接常见问题咨询，机器人自动化处理率达到60%，"
        "对于复杂投诉和售后纠纷，则由经过专业培训的金牌客服经理一对一深度跟进，"
        "客户满意度综合评分连续三年在同类企业中保持行业领先地位，多次获得权威机构认可。\n"
        "移动端服务创新是集团数字化转型的重要突破方向，也是用户体验升级的核心载体。"
        "微信小程序作为集团数字触点的重要组成，自上线以来持续迭代优化，日活跃用户数已突破50万人次。"
        "用户可在小程序内完成从商品浏览、价格比较到下单支付和全程配送跟踪的完整消费旅程，"
        "界面简洁直观，加载速度快，操作体验受到用户的高度好评。"
        "小程序还集成了会员积分实时查询、电子优惠券领取和门店导购在线预约等丰富增值功能，"
        "有效推动线上订单在集团整体销售额中的占比持续快速提升，两年内从8%增长至28%。\n"
        "在私域流量运营层面，集团构建了以微信生态为核心的立体私域流量运营矩阵，"
        "通过建立品类社群、举办线上主题活动和发展付费会员专属社区三大抓手，"
        "累计沉淀私域用户超过200万人，触达成本仅为公域投放的十分之一左右。"
        "社群内持续发布限时秒杀抢购信息、新品尝鲜预告和独家买家秀内容，"
        "有效激发用户复购意愿，社群活跃用户的年均复购频次比普通渠道用户高出约40%，"
        "私域运营已成为集团新的利润增长引擎。\n"
        "内部协同效率的系统性提升也是数字化建设的重要组成。"
        "集团在全国所有门店和总部职能部门全面推行企业微信作为统一的日常办公协同平台，"
        "打通了审批流程、任务分配与跟踪、内部公告通知和知识库共享等核心业务场景，"
        "实现了总部与门店的实时信息同步和远程指挥调度，跨部门协作响应速度提升了约60%，"
        "员工对协同办公工具的综合满意度调研得分高达92%，人效比同行业提升约15%。\n"
        "在内容营销和直播电商领域，集团充分借助微信视频号和公众号生态的流量分发优势，"
        "深度融合图文种草、短视频测评和直播带货三种内容形态，"
        "定期与知名品牌联合策划主题专场直播，全年合作场次超过百场，累计观看人次逾5000万。"
        "直播渠道已成为仅次于实体门店的第二大销售渠道，贡献全年销售额约15%，"
        "直播间粉丝转化率和客单价均高于行业平均水平，品牌影响力持续扩大。\n"
        "在供应链端，集团上线全链路供应链数字化管理平台，实现采购、入库、分拣和配送的全程数字化。"
        "AI驱动的补货预测系统将滞销品库存积压率降低18%，鲜食类商品损耗率较改造前下降22%，"
        "每年节省仓储和损耗成本超过亿元，供应商结算周期也从30天缩短至20天，双赢效果显著。\n"
        "在会员体系升级方面，集团联合多家品牌合作伙伴推出联盟积分计划，"
        "会员可在集团旗下全品类门店和合作商户跨场景积分，积分兑换率和有效期均得到优化，"
        "会员规模从300万增长至700万，高价值黄金会员占比提升了12个百分点，"
        "核心会员贡献了集团超过60%的销售额，会员运营成为差异化竞争的重要抓手。\n"
        "在数据智能层面，集团构建了统一的用户数据中台，整合门店POS、电商订单、"
        "微信小程序行为和会员签到等多源数据，建立了涵盖用户画像、消费偏好和价格敏感度的"
        "全景数据模型，为精准营销、智能选品和个性化推荐提供了坚实的数据基础，"
        "营销ROI较传统大水漫灌模式提升了约2.3倍。\n"
        "绿色零售是集团当前重点推进的可持续发展议题之一，"
        "集团在包装减量、节能照明和食物损耗降低等方面设定了明确的量化目标，"
        "与核心供应商签订了绿色采购协议，从产品设计阶段就推进源头减碳降耗，"
        "门店光伏发电覆盖率持续提升，绿色电力使用占比已达35%，"
        "集团碳排放总量连续两年实现同比下降，获得了权威机构颁发的绿色认证称号，"
        "树立了零售行业可持续发展的良好形象。\n"
        "在人才战略方面，集团将数字化人才作为核心战略资源进行重点培育，"
        "与头部高校建立联合培训项目，每年定向引进算法工程师、数据分析师和用户增长专家，"
        "同时对现有员工开展分层次、分岗位的数字化技能提升培训，"
        "建立了完善的数字化岗位晋升通道和激励体系，"
        "近两年数字化相关岗位员工流失率大幅下降，核心技术团队保持稳定。"
        "集团还积极参与行业组织和标准制定，通过分享实践经验推动行业整体数字化能力提升，"
        "在业界积累了良好的品牌声誉和影响力。\n"
        "在线下体验创新方面，集团将实体门店定位为社交消费和体验消费的目的地，"
        "在多个旗舰店引入沉浸式场景布置、直播互动区和顾客个性化定制服务台，"
        "打造差异化的线下消费场景，吸引年轻客群回归实体购物。"
        "与此同时，门店还充当私域流量和线上订单的重要履约节点，"
        "实现门店仓储与即时配送平台的深度整合，30分钟达配送服务覆盖门店周边5公里范围，"
        "线上转线下核销率持续提升，全渠道协同效应日益明显。\n"
        "在国际化布局方面，集团正积极探索东南亚市场的业务扩张机会，"
        "依托中国积累的全渠道零售经验和数字化技术能力，在泰国和越南设立了试点门店，"
        "复制国内的数字化运营模式和私域流量打法，已初步验证了可行性。"
        "集团计划在三年内将海外门店数量扩大至50家，并适配当地市场的支付和物流生态，"
        "构建面向东南亚消费者的完整零售服务体系，提升集团的国际化品牌形象与竞争力。\n"
        "展望未来三年，集团将持续加大数字化研发和基础设施投入，"
        "重点推进无人收银和自助购物场景的全面落地，全面升级仓储物流自动化和智能调度系统，"
        "探索在微信生态内新增AR试妆和个性化推荐功能，并借助大模型技术提升营销精准度，"
        "力争将数字化渠道销售占比从当前的28%提升至50%以上，"
        "同时推动绿色零售和社会责任目标协同达成，将集团打造为零售行业数字化转型与可持续发展的双重标杆企业。\n"
    )

    wechat_count = text.count("微信")
    text_len = len(text)
    density = wechat_count / text_len * 1000

    assert wechat_count >= 8, (
        f"Expected >= 8 WeChat mentions, got {wechat_count}"
    )
    assert text_len >= 1500, f"Text should be >= 1500 chars, got {text_len}"
    assert density < 3.0, (
        f"Density {density:.3f} should be < 3.0 "
        f"(old absolute threshold >6 would kill any text with 8 WeChat mentions)"
    )

    result = _process(text, category="ke_ji")
    detail = result.dirty_rec.get("new_filter_detail") if result.dirty_rec else "N/A"
    assert result.clean_rec is not None, (
        f"[SOFT THRESHOLD] 8 WeChat mentions in enterprise article wrongly rejected. "
        f"Old absolute threshold >6 would kill any text with 8 mentions; "
        f"new density {density:.2f}/kilo < 3.0 should pass. "
        f"reject_detail={detail}"
    )


# ===========================================================================
# Category 3: High-density garbage is rejected;
#             Low-quality structural text is also rejected.
# ===========================================================================


def test_dense_lottery_gambling_rejected():
    """
    Short dense 'lottery/bet/macau' spam text is rejected.
    The rejection reason can be density:, bad_keyword_score, or zlib_full_high
    (highly repetitive spam triggers zlib before density checks, all are valid rejections).
    """
    spam_core = (
        "彩票开奖推荐买球澳门彩票官方购彩，投注开奖直播澳门彩票，"
        "买球赢大奖彩票预测在线博彩网赌平台，押注彩票赔率，"
    ) * 8  # ~400 chars
    filler = "今日最新彩票开奖号码推荐，快来购彩。彩票中奖秘诀大公开。"
    text = spam_core + filler
    assert len(text) > 256

    result = _process(text, category="ke_ji")
    assert result.clean_rec is None, (
        "High-density lottery/gambling spam should be rejected"
    )
    assert result.dirty_rec is not None

    detail = result.dirty_rec.get("new_filter_detail", "")
    # Any of these three is a valid rejection reason for pure spam
    assert (
        "density:" in detail
        or "bad_keyword_score" in detail
        or "zlib_full_high" in detail
        or "filter_rules_2" in detail
    ), f"Unexpected reject_detail: {detail}"


def test_dense_porn_gambling_keywords_rejected():
    """
    Multiple core-weight bad keywords (weight=2.0) at high density are rejected.
    score >= BAD_KEYWORD_SCORE_MIN=3.0 and score/len*1000 > 1.0.
    Zlib may also trigger first on highly repetitive spam.
    """
    # Core gambling/betting keywords in a short, dense text
    base = (
        "在线博彩平台推荐，网赌最新地址，押注赔率高，投注活动多，"
        "皇冠博彩官网开户，澳门威尼斯人平台，澳门新葡京注册，"
        "线上买球赔率，彩票官方购彩网站，时时彩开奖，竞彩预测。"
    )
    text = base * 5  # ~300 chars, core keyword density very high
    assert len(text) > 256

    result = _process(text, category="ke_ji")
    assert result.clean_rec is None, (
        "High-density core bad-keyword text should be rejected"
    )
    detail = result.dirty_rec.get("new_filter_detail", "") if result.dirty_rec else ""
    assert (
        "density:" in detail
        or "bad_keyword_score" in detail
        or "zlib_full_high" in detail
        or "filter_rules_2" in detail
    ), f"Should be rejected by density/bad_keyword/zlib. Got: {detail}"


def test_low_quality_listing_page_rejected():
    """
    Navigation/listing page style text (many short lines, no full sentences)
    is rejected by quality_signals (mean_line_len) or chapter_filter.
    This tests P4's QualitySignalsRule in the pipeline.
    """
    # Typical website navigation page: lots of short link-like lines
    lines = [
        "- 首页",
        "- 新闻资讯",
        "- 产品中心",
        "- 关于我们",
        "- 联系方式",
        "- 招聘信息",
        "- 合作伙伴",
        "- 下载中心",
        "- 常见问题",
        "- 技术支持",
        "- 售后服务",
        "- 网站地图",
        "- 隐私政策",
        "- 版权声明",
        "- 友情链接",
        "- 在线留言",
        "- 产品一览",
        "- 解决方案",
        "- 客户案例",
        "- 行业资讯",
        "- 媒体报道",
        "- 活动公告",
        "- 视频中心",
        "- 图片库",
        "- 数据下载",
        "- 白皮书",
        "- 演示申请",
        "- 价格咨询",
        "- 免费试用",
        "- 登录注册",
    ]
    # Repeat to exceed MIN_TEXT_LEN=256 while keeping the listing structure
    text = "\n".join(lines * 3)
    assert len(text) > 256

    result = _process(text, category="ke_ji")
    assert result.clean_rec is None, (
        "Navigation/listing page should be rejected"
    )
    detail = result.dirty_rec.get("new_filter_detail", "") if result.dirty_rec else ""
    assert detail, "Should have a non-empty reject_detail"


def test_low_quality_repetitive_nav_rejected():
    """
    Forum-style UI noise text with many 'reply_day' patterns
    ('X天前回复') is rejected by density rule.
    """
    noise_line = "张三 3天前回复：顶！李四 5天前回复：好的。王五 2天前回复：赞一个！"
    text = (noise_line + "\n") * 35  # ~1200 chars, very high reply_day density
    assert len(text) > 256

    result = _process(text, category="ke_ji")
    assert result.clean_rec is None, (
        "High-density forum timestamp noise should be rejected"
    )
    detail = result.dirty_rec.get("new_filter_detail", "") if result.dirty_rec else ""
    assert detail, "Should have a non-empty reject_detail"
