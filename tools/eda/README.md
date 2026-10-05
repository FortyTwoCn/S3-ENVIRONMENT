# 嘉立创 EDA 连接辅助工具

这里保存此前接入本机嘉立创 EDA 专业版的两条通道。PCB 的权威可编辑工程是仓库的 `hardware/` KiCad 工程；这些工具没有将其自动转换为嘉立创工程。

## CLI / stdio MCP

`lceda_mcp.py` 使用 Python 标准库，将嘉立创官方 CLI 包装为 stdio MCP。此前客户端 4.1.60 的原生 `--mcp stdio` 返回 `MCP_NOT_SUPPORTED`，该适配器完成初始化及七项工具发现；没有修改 EDA 安装文件。

按 `codex-mcp-config.example.toml` 填写你自己的脚本和 EDA 安装路径，加入本机 MCP 配置。不要直接复制原电脑配置。工程路径通过工具参数明确传入。

## Run API Gateway

`gateway/` 保存官方桥接脚本、Python HTTP 客户端、启动器与固定依赖文件。此前在 Run API Gateway 1.0.6 / 嘉立创 EDA 4.1.60 下完成只读查询，官方 Bridge 为 1.1.43。

```powershell
cd tools/eda/gateway
npm ci --omit=dev --ignore-scripts
powershell -ExecutionPolicy Bypass -File .\Start-Bridge.ps1
python eda_gateway.py status
python eda_gateway.py read-state
```

启动器使用 PATH 中的 Node；也可传入 `-NodeExe 'C:/path/to/node.exe'`。在 EDA 插件管理器允许 Run API Gateway 外部交互，并在其菜单执行重新连接。

Bridge 仅监听 `127.0.0.1` 的 49620…49629 端口。多窗口执行时明确选择窗口；先核对当前工程、文档和 API，再修改设计。生成的 `logs/`、进程 ID、依赖安装目录和本机 MCP 配置均不提交。

官方脚本来源、提交 ID、SHA256 和依赖完整性见 `gateway/upstream.json`。`bridge-server.mjs` 保持上游原文件；启动器的 Node 路径已经改为可配置。来源：[easyeda-api-skill](https://github.com/easyeda/easyeda-api-skill)、[Run API Gateway](https://github.com/easyeda/eext-run-api-gateway)、[嘉立创 CLI](https://prodocs.lceda.cn/cn/api/guide/cli.html)。
