# Stage 11 Web/API 服务契约（批次 1，W1/W4 裁决）

`app.cli serve` 启动的本地 HTTP API 服务（FastAPI）。定位：**本地单用户工具**——
无鉴权，不适合公开暴露；默认仅监听 127.0.0.1，非 loopback 地址须显式
`--unsafe-expose`（CLI 层拦截，rc 2，服务层不重复判断）。

实现：`app/service.py`（应用工厂 `create_app`）+ `app/cli.py serve` 子命令 +
`app/static/index.html`（极简前端，无构建链）。服务层只是外壳：解析/分块/校验
全部复用 CLI 同一实现（`process_single`），不改 parser/chunker/pipeline 语义。

## 1. 端点

| 方法 | 路径 | 说明 |
|---|---|---|
| GET | `/api/v1/health` | `{status: "ok", version, parser_count}` |
| GET | `/api/v1/parsers` | `list_parsers()` 行原样（(priority, name) 稳定序） |
| POST | `/api/v1/parse` | multipart 表单：`file`（必填）、`parser`（默认 `fallback`，可为 `auto`）、`max_chars`（默认 800）→ 统一文档 JSON |
| GET | `/` | 静态前端（挂载在全部 API 路由之后，不遮蔽 `/api/*`、`/docs`、`/openapi.json`） |
| GET | `/docs`、`/openapi.json` | FastAPI 自带文档（不被静态根遮蔽） |

启动参数：`--host`（默认 127.0.0.1）、`--port`（默认 8000）、`--plugin`
（可重复，启动时一次性加载，失败即启动失败）、`--max-upload-mb`
（默认 50）、`--unsafe-expose`（非 loopback 确认开关）。

`/api/v1/parse` 内部执行序与 CLI `parse` 一致：插件已在启动时预载 →
流式落盘临时文件（实际计量，超限 413）→ parser 名校验（`auto` 为保留名）
→ auto 扩展名发现 → `process_single(write_json=False)` → 响应。
`process_single` 在事件循环内同步执行——本地单用户工具的已知边界。

## 2. 错误 envelope（全部错误响应统一形状）

```json
{"error": {"code": "...", "message": "...", "details": {...}}}
```

`details` 可省略（无内容时不出现该键）。成功响应 = 与 CLI `parse -o`
同构的统一文档 JSON（键集完全一致，无 `error` 键），仅两处已知差异：

- `source_path` = 净化后的上传文件名（`sanitize_filename`：取 basename、
  去控制字符、长度封顶 100 保后缀），**永不**是服务器临时路径；
- `metadata.image_output_dir` 不存在（服务不写盘、不导出图片目录）。

## 3. HTTP 错误映射表（W4 首报送审）

### 3.1 服务层错误（进入 pipeline 之前）

| HTTP | code | 触发条件 |
|---|---|---|
| 413 | `upload_too_large` | 流式写入时实际计量超过 `max_upload_bytes`（不信任 Content-Length）；`details.limit_bytes` 给出上限 |
| 400 | `unknown_parser` | `parser` 不是注册名且不是 `auto`；message 含已知名单 |
| 400 | `unsupported_type` | `parser=auto` 但扩展名无任何已注册 parser 声明（发现层 ValueError） |
| 422 | `invalid_request` | 请求参数缺失或类型不符（如缺 `file` 字段、`max_chars` 非整数）；`details.errors` 截断至 20 条 |

### 3.2 pipeline 错误（`process_single` 返回非空 errors）

取**第一条**错误记录映射，其余丢弃；`message`/`details` 中的服务器临时
路径已被递归替换为净化上传名。

| HTTP | code | 规则 |
|---|---|---|
| 500 | `parser_contract_mismatch` / `unexpected_parser_error` / `chunker_failed` | 服务端集成缺陷三码（固定集合 `_SERVER_DEFECT_CODES`） |
| 422 | 其余全部错误码 | 业务失败：`no_extracted_elements`、`schema_validation_failed`、`hash_io_error`、parser 各自的 `ParserError` 子类码（`file_not_found`、`md_read_failed`、各格式解析失败码等） |

注意 `unsupported_type` 有**两个来源**：发现层（表 3.1，400）与个别 parser
对"显式指定的扩展名"自查拒绝（pipeline 层，表 3.2，422）。同码不同状态是
既定行为：来源不同（找不到 parser vs parser 明确拒绝）。

### 3.3 未预期异常

| HTTP | code | 行为 |
|---|---|---|
| 500 | `internal_error` | 响应体**无 traceback**（固定一句"服务器内部错误"）；完整 traceback 只进服务器日志（`logging.getLogger("app.service")` `.exception`） |

### 3.4 traceback 泄露面（W4：redaction 行为）

- 任何 HTTP 响应体（成功或错误）都不含 traceback；
- pipeline 错误的 `message` 可能含异常类型名（如 `ValueError: ...`），
  但不含完整调用栈；`details` 不含 traceback 字段（结构化错误契约本就如此）；
- 唯一含 traceback 的输出是服务器端日志（stderr/uvicorn log），不回传客户端。

## 4. 临时文件与路径泄露（W1 边界）

- 上传先流式写入 `tempfile.mkstemp`（后缀取自净化名，供扩展名发现），
  1 MiB 块读取、**边写边计量**；成功 / 失败 / 超限 / 未预期异常全路径
  `finally` 清理（内层 `finally` 关 fd，外层 `finally` unlink + 关闭上传）；
- 响应中的服务器临时路径通过 `_scrub_paths` 递归替换（成功路径
  `source_path` 直接覆写为净化名；错误路径 message/details 同样替换）。

## 5. 已知边界与待裁事项

1. **`max_chars <= 0` → 500 `chunker_failed`**（与 CLI 同码：CLI
   `--max-chars 0` 同样 `chunker_failed` rc 1）。用户输入可轻易触发
   500 是否合适待 r32 裁决：A. 维持缺陷码映射（CLI 行为一致）；
   B. 服务层显式校验 `max_chars >= 1` → 400（新增前置拒绝）。
   前端表单已用 `min="1"` 挡住，但 API 层未挡。
2. `process_single` 同步执行会阻塞事件循环——本地单用户可接受，
   不做异步任务队列（本批明确不做）。
3. 无评测端点、无鉴权、无持久化、无批量端点、无真实 KVFS 接入
   （W1 裁决范围边界）。

## 6. 测试

`tests/test_service_api.py`（23 项，全合成夹具）：API 与 CLI 成功结构
等价（逐键相等）、max_chars 透传等价、上传名净化、错误码全表行为验证
（400/413/422/500 + 无 traceback + 临时路径净化）、恰好等于上限放行、
临时目录全路径清理断言、插件预载（显式/auto/健康列表/加载失败）、
前端与遮蔽、CLI loopback 与 max-upload 守卫。
