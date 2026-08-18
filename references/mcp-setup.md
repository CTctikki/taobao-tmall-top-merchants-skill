# 企业查询MCP安装

## 检测

读取 `~/.codex/config.toml` 的 `mcp_servers`，名称或URL包含 `qcc`、`企查查`、`aiqicha`、`爱企查`、`tianyancha`、`天眼查` 均视为候选企业查询MCP。另检查 `~/.openclaw/skills/company-search-fengniao/scripts/tool.mjs`；当前进程存在 `FN_API_KEY` 时优先使用私有额度，否则使用官方包的公共额度。运行时以实际工具列表为准。

## 企查查示例

不要把Token写进命令历史、脚本或Git。将密钥放入环境变量：

```powershell
$env:QCC_AUTH = "Bearer <YOUR_TOKEN>"
```

配置公司信息服务：

```powershell
codex mcp add qcc-company --url https://agent.qcc.com/mcp/company/stream --bearer-token-env-var QCC_AUTH
```

开通/充值入口：<https://agent.qcc.com/>。配置后重启Codex，再运行预检。

## 其他提供商

若本机已有爱企查、天眼查等MCP，优先使用其实体识别、工商登记和联系方式工具。若没有公开、可验证的安装命令，不要猜测包名或URL；打开提供商官方说明，让用户完成API开通后再配置。

## 风鸟 Skill

官方包：<https://clawhub.ai/xinshu001/company-search-fengniao>。全局安装：

```powershell
npx -y openclaw@2026.7.1-2 skills install '@xinshu001/company-search-fengniao' --global --acknowledge-clawhub-risk
```

官方包可使用有限公共额度；有私有 Key 时只放在当前进程的 `FN_API_KEY`，不要写入配置文件、命令参数或结果文件。进入风鸟 Skill 目录后按以下顺序调用：

```powershell
node scripts/tool.mjs discover "企业基本信息"
node scripts/tool.mjs call biz_fuzzy_search --params '{"key":"企业或品牌中文名"}'
node scripts/tool.mjs call biz_basic_info --params '{"entid":"上一步内部ID"}'
```

先用 `biz_fuzzy_search` 消歧，再用同一个内部 `entid` 查询基本信息。企业简称或品牌出现多个候选时不得直接取第一条。`entid` 不写入工作簿。

## 数据纪律

- 运行 `scripts/company_source_routing.py`：模糊身份先风鸟、精确身份先企查查，随后用另一数据源核验或补缺
- 简称或品牌先实体识别
- 多候选由用户/店铺资质证据确认
- 完整公司名或信用代码才能查工商详情
- 联系方式不能单独确认店铺主体；仅有电话/邮箱的候选保持 `selected: false`
- 平台资质页确认的当前持证主体优先于商标权利人；只有商标证据时必须写明主体角色和剩余风险
- 多源冲突证据优先级：平台资质页 > 信用代码一致 > 商标/品牌官网 > 企业名称相似 > 电话邮箱
- MCP未返回的字段留空
