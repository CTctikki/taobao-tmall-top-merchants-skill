# 数据契约

## job.json

必填：`category`、`queries`、`include_patterns`、`exclude_patterns`。默认参数：`min_spu=10`、`min_share=0.3`、`high_match_share=0.5`、`pages=2`、`interval_seconds=20`。

## discovery_raw.json

按查询词保存公开搜索商品：`item_id`、`title`、`shop`、`shop_url`、`user_id`、`sales`、`iconList`、`auctionURL`。

## candidates.json

按类目+店铺聚合：平台、发现目标SPU、查询词、商品样本、店铺链接和用户ID。

## assortment_audit.json

每个店铺记录：`exact_shop_spu_seen`、`target_spu`、`electric_spu`、`accessory_spu`、`unrelated_spu`、`target_share`、`passes_minimum`、`match_grade`、目标商品明细。

## storefronts.json

店铺正式URL、`shop_id`、`seller_id`、`shop_type`、页面信号、采集时间。

## company_candidates.json

企业MCP实体识别原始候选。多候选保持原样，禁止覆盖成单一主体。

## subjects.json

由Agent基于证据确认的完整公司名映射：店铺名、公司名、主体角色、置信度、证据URL和备注。

## company_enrichment.json

确认主体的工商登记与联系方式原始返回。缺失值保持空白。

## 工作簿

正式表字段至少包括：类目、平台/店铺类型、店铺名、目标SPU、精确店铺SPU、相关占比、匹配等级、付款展示下限、店铺链接、shopId/sellerId、公司名称、法人、电话、邮箱、注册地址、成立日期、信用代码、主体角色/置信度、来源和待确认项。

