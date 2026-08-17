# 企业查询MCP安装

## 检测

读取 `~/.codex/config.toml` 的 `mcp_servers`，名称或URL包含 `qcc`、`企查查`、`aiqicha`、`爱企查`、`tianyancha`、`天眼查` 均视为候选企业查询MCP。运行时以实际工具列表为准。

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

## 数据纪律

- 简称或品牌先实体识别
- 多候选由用户/店铺资质证据确认
- 完整公司名或信用代码才能查工商详情
- MCP未返回的字段留空

