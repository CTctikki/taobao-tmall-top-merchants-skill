# 淘宝/天猫top商家清单

一个可复用的 Codex Skill：用户只需给出商品类目，Agent 会检查淘宝登录和企业查询 MCP，低频采集淘宝/天猫店铺，按店铺商品结构筛选 TOP 商家，并补齐工商与联系方式，最后生成可招商的 Excel 工作簿。

## 默认口径

- 淘宝店/C店和天猫店全部纳入
- 目标商品 SPU ≥ 10
- 店内目标商品占比 ≥ 30%
- 占比 ≥ 50% 标记为高匹配
- 多企业候选不自动选第一名
- 未披露数据留空，不编造

## 安装

```bash
git clone https://github.com/CTctikki/taobao-tmall-top-merchants-skill.git
```

将仓库目录复制或链接到 `$CODEX_HOME/skills/taobao-tmall-top-merchants`（默认 `~/.codex/skills/`），重启 Codex 后使用：

```text
$taobao-tmall-top-merchants 按摩梳
```

## 依赖

- Python 3.11+
- `openpyxl`、`requests`
- `o2` 与 `webcli` Browser Bridge
- 至少一个企业查询 MCP（企查查/爱企查/天眼查等）
- 已登录淘宝的 Chrome 会话

密钥只通过环境变量或本机 Codex 配置提供，禁止提交到 Git。

## 目录

- `SKILL.md`：Agent 执行协议
- `scripts/`：预检、采集、审计、企业补全、工作簿生成
- `references/`：流程、数据契约、MCP安装、类目规则
- `tests/`：离线单元测试

## 合规

仅采集用户浏览器中可访问的公开页面和公开企业信息；遵守平台条款、访问频率限制和验证码流程，不绕过风控。

