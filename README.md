# 淘宝/天猫top商家清单

一个可复用的 Codex Skill，支持两种模式：用户只给商品类目时，Agent 低频发现并审计淘宝/天猫优质商家；用户直接给店铺名、多个链接、文本、表格、电子表格或混合名单时，Agent 不重新采集淘宝，直接整理建联对象、企业候选与联系方式，生成最终招商工作簿。

## 使用模式

- **类目发现模式**：执行候选发现、店铺SPU结构审计和默认Top30优质短名单规则。
- **用户指定名单模式**：用户给出的店铺全部进入正式招商表，不需要固定Excel模板或专用导入脚本；Codex自行提取、去重并保留原始输入。
- **审核筛选模式**：读取已有审核工作簿，访问表内店铺并回填引入画像和优先级；与不打开淘宝的用户指定名单模式相互独立。

名单模式不填写或推断SPU、店内占比、付款人数展示下限和Top30结论。工作簿会明确说明该名单由用户指定，不代表已通过主营准入审计。

## 默认口径

- 淘宝店/C店和天猫店全部纳入
- 目标商品 SPU ≥ 10
- 店内目标商品占比 ≥ 30%
- 占比 ≥ 50% 标记为高匹配
- 优质短名单默认要求目标商品付款人数展示下限合计 ≥ 10000，每类最多审计 30 家；不足不凑数
- 多企业候选不自动选第一名
- 候选企业电话、邮箱和地址直接写入正式表的“待核验”建联列，方便招商联系但不作为主体认定证据
- 平台营业执照公司名和信用代码是正式主体最高优先级；与执照不一致的企业搜索结果只能显示为“建联候选公司（非店铺主体，待核验）”
- 平台资质必须来自独立资质记录且同时具备公司名和信用代码；信用代码闭环必须保存并逐字比较来源侧代码，不能只写证据类型标签
- 未披露数据留空，不编造
- 企业查询动态路由：模糊店铺/品牌先风鸟，精确公司全称/信用代码先企查查，再用另一平台核验或补缺

## 安装

```bash
git clone https://github.com/CTctikki/taobao-tmall-top-merchants-skill.git
```

将仓库目录复制或链接到 `$CODEX_HOME/skills/taobao-tmall-top-merchants`（默认 `~/.codex/skills/`），重启 Codex 后使用：

```text
$taobao-tmall-top-merchants 按摩梳
```

也可以直接粘贴店铺名称或多个店铺链接，或附上任意结构的名单文件并要求整理最终招商表。

首次运行会自动执行环境检查；也可以手动运行：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1
```

整理用户指定名单时跳过淘宝检查：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -SkipTaobaoCheck
```

审核已有工作簿时使用不检查企业 Key 的独立环境入口：

```powershell
powershell -ExecutionPolicy Bypass -File scripts/bootstrap.ps1 -AuditOnly
python scripts/review_workbook.py "审核筛选.xlsx" --output "审核筛选_已完成.xlsx" --owner "负责人" --dry-run
python scripts/review_workbook.py "审核筛选.xlsx" --output "审核筛选_已完成.xlsx" --owner "负责人"
```

审核模式按语义识别列名，重复店铺只访问一次；首页无商品时依次回退店内热销页和公开店铺列表页。详细规则见 `references/review-mode.md`。

## 首次使用

类目发现和用户指定名单任务必须同时拥有企查查 Key 和风鸟 Key；审核筛选模式不执行企业查询，因此不要求这两个 Key：

- 企查查：<https://agent.qcc.com/profile/api-key>
- 风鸟：<https://www.riskbird.com/center/apiKey>

把两个 Key 一起发给 Codex 即可，不要自行配置环境变量。Codex 会通过 `scripts/configure_enterprise_keys.py` 的标准输入安全配置，不把 Key 放进命令参数、仓库、日志或工作簿；后续风鸟调用通过 `scripts/run_fengniao.py` 自动读取用户级配置，无需重启。任一 Key 缺失或验证失败时，任务会停止。

如果提示 Browser Bridge 未连接，按以下步骤操作：

1. 在 Chrome 地址栏打开 `chrome://extensions`。
2. 开启右上角“开发者模式”。
3. 点击“加载已解压的扩展程序”，选择 `~/.webcli/extension`。
4. 将 Browser Bridge 固定到工具栏，并保持 Chrome 开启。
5. 重新运行 `bootstrap.ps1`，直到连接检查通过。

## 依赖

- Windows PowerShell 与 `winget`（仅在需要自动安装 Python 时使用）
- 已登录淘宝的 Chrome 会话（类目发现模式和审核筛选模式需要）
- 已验证的 `qcc-company` MCP 与风鸟企业查询 Skill，两者缺一不可（审核筛选模式除外）

`bootstrap.ps1` 会自动检测并尽量静默安装以下运行环境：

- Python 3.11 或更高版本；
- `openpyxl`、`requests`；
- `o2`；
- `webcli` Browser Bridge；
- `qcc-company` MCP 与风鸟企业查询 Skill。

风鸟公共额度不能替代用户自己的 Key。企业账号开通、淘宝登录和验证码仍需用户本人完成，脚本不会绕过登录或风控。

密钥只由 Codex 通过标准输入交给配置助手，禁止写入命令参数或提交到 Git。可先运行 `python scripts/company_source_routing.py --brand-or-shop <店铺或品牌>` 或 `--company-name <公司全称>` 获取动态查询顺序；仅有联系方式时不得自动确认主体。

## 目录

- `SKILL.md`：Agent 执行协议
- `scripts/`：预检、采集、审计、企业补全、工作簿生成
- `references/`：流程、数据契约、审核模式、MCP安装、类目规则
- `tests/`：离线单元测试

## 合规

仅采集用户浏览器中可访问的公开页面和公开企业信息；遵守平台条款、访问频率限制和验证码流程，不绕过风控。

- 用户明确要求每类销量 Top N 时，设置 `sales_top_n_mode=true` 与 `max_candidate_shops=N`；原始发现候选不会全部进入后续审计。
