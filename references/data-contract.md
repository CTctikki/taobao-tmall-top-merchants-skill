# 数据契约

## 两种输入契约

类目发现模式使用下述 `job.json` 与采集审计文件。用户指定名单模式不要求固定文件格式，也不要求创建专用导入脚本；输入可以是店铺名、多个链接、文本、聊天表格、电子表格或混合信息。

名单模式中，Codex在当前任务内归一化以下字段，缺失值留空：

- `category`：用户提供的类目或分组
- `shop_name`：店铺名；未知时保留链接并标记待补
- `platform`：依据明确域名或可靠页面信号识别，否则为“待核验”
- `shop_url`：原始店铺或商品链接，不擅自替换
- `provided_company`、`provided_contact`：用户已给公司与联系方式
- `owner`、`source`：负责人、提供人或来源标记
- `raw_input`：足以回溯原文、原表行或原链接的位置

同一店铺的多条输入合并时保留所有来源URL和冲突值。用户指定名单中的每个唯一店铺都视为正式建联对象，不使用 `passes_minimum`、SPU或占比决定去留。

## job.json

必填：`category`、`queries`、`include_patterns`、`exclude_patterns`。默认参数：`min_spu=10`、`min_share=0.3`、`high_match_share=0.5`、`pages=2`、`interval_seconds=20`、`minimum_payment_lower_bound=10000`、`minimum_quality_query_coverage=3`、`max_candidate_shops=30`。`excluded_shop_patterns` 用于排除综合渠道店；原始候选不等于审计队列。 `sales_top_n_mode` 默认为 `false`；用户要求每类销量Top N时设为 `true`，并设置 `max_candidate_shops=N`、`minimum_payment_lower_bound=0`、`minimum_quality_query_coverage=1`，候选按目标商品付款人数展示下限排序后只审计前N家。

## discovery_raw.json

按查询词保存公开搜索商品：`item_id`、`title`、`shop`、`shop_url`、`user_id`、`sales`、`iconList`、`auctionURL`。

## candidates.json

按类目+店铺聚合：平台、发现目标SPU、查询词、商品样本、店铺链接和用户ID。

## assortment_audit.json

每个店铺记录：`exact_shop_spu_seen`、`target_spu`、`electric_spu`、`accessory_spu`、`unrelated_spu`、`target_share`、`passes_minimum`、`match_grade`、目标商品明细。

## storefronts.json

店铺正式URL、`shop_id`、`seller_id`、`shop_type`、页面信号、采集时间。

## company_candidates.json

企业MCP或风鸟实体识别原始候选。多候选保持原样，禁止覆盖成单一主体。

## subjects.json

由Agent基于证据确认的完整公司名映射：店铺名、公司名、主体角色、置信度、证据URL和备注。只有证据闭环的候选可设为 `selected: true`；仅有联系方式或仍存在多个主体时保持 `selected: false`。

## trademark_queries.json / company_trademarks.json

前者按店铺指定 `brand_terms`、`relevant_classes` 和候选 `companies`；后者保存企业MCP有效商标返回及品牌词+类别匹配结果，用于多候选交叉确认。

## company_enrichment.json

确认主体的工商登记与联系方式原始返回。每个候选保留 `selected`、`evidence`、`registration` 和 `contact`；数据来源写入 `evidence` 或单独的 `source` 字段。缺失值保持空白；电话和邮箱全部去重保留，不做条数截断。

## 工作簿

正式表字段至少包括：类目、平台/店铺类型、店铺名、目标SPU、精确店铺SPU、相关占比、匹配等级、付款展示下限、店铺链接、shopId/sellerId、候选公司/电话/邮箱/地址（待核验）、建联提示、已确认公司名称、法人、电话、邮箱、注册地址、成立日期、信用代码、主体角色/置信度、来源和待确认项。候选建联字段不得被解释为已确认店铺主体。

用户指定名单模式的正式表不要求目标SPU、精确店铺SPU、相关占比、匹配等级和付款展示字段；若保留这些列，必须留空并说明未执行商品结构审计。名单模式至少保留：类目/分组、平台、店铺名、店铺链接、负责人、来源、候选公司/法人/电话/邮箱/地址/成立日期/信用代码/登记状态（均标记待核验）、已确认主体字段、证据、建联提示和待确认项。

名单模式工作簿包含六类信息：

1. 概览：输入店铺数、类目和平台分布、企业候选及联系方式覆盖。
2. 正式招商商家：用户指定的全部唯一店铺。
3. 主体核验：全部企业候选及 `selected`、证据和待确认项。
4. 未确认字段：无候选、额度不足、缺少链接、缺少联系方式和主体未闭环原因。
5. 原始输入：原文、原表行或原链接及归一化结果。
6. 口径说明：明确“用户指定名单，不代表Top30或主营准入达标”，并说明未运行淘宝采集。
