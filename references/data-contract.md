# 数据契约

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
