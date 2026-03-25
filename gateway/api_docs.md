# Gateway API 文档

> 版本：v1.0.0
> Base URL：`http://localhost:8000/api/v1`
> 完整交互式文档：[http://localhost:8000/docs](http://localhost:8000/docs)（FastAPI Swagger UI）

---

## 通用约定

### 请求头

| 头字段 | 说明 |
|--------|------|
| `Content-Type: application/json` | POST 请求必须携带 |
| `Authorization: Bearer <token>` | 预留，当前版本不强制校验 |

### 错误响应格式

```json
{
  "detail": "错误描述信息"
}
```

| HTTP 状态码 | 含义 |
|------------|------|
| `200` | 成功 |
| `404` | 资源不存在 |
| `422` | 请求参数校验失败 |
| `500` | 服务器内部错误 |

---

## 接口列表

### 1. 提交推理请求

```
POST /inference
```

**请求体**

```json
{
  "prompt": "string",        // 必填，不能为空
  "max_tokens": 512,         // 可选，范围 1–4096，默认 512
  "temperature": 0.7         // 可选，范围 0.0–2.0，默认 0.7
}
```

**响应体 `200`**

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "result": "模型生成的文本内容",
  "status": "success",
  "created_at": "2026-03-25T10:00:00Z"
}
```

**错误**

| 状态码 | 触发条件 |
|--------|---------|
| `422` | `prompt` 为空字符串，或参数超出范围 |

---

### 2. 获取历史记录列表

```
GET /history
```

**查询参数**

| 参数 | 类型 | 默认值 | 说明 |
|------|------|--------|------|
| `limit` | int | 20 | 每页条数，范围 1–100 |
| `offset` | int | 0 | 跳过条数（用于分页） |
| `status` | string | *(无)* | 状态筛选：`success` 或 `failed` |

**响应体 `200`**

```json
{
  "items": [
    {
      "request_id": "550e8400-e29b-41d4-a716-446655440000",
      "prompt_preview": "前 80 个字符的摘要…",
      "status": "success",
      "created_at": "2026-03-25T10:00:00Z"
    }
  ],
  "total": 42
}
```

> `total` 为满足筛选条件的记录总数（忽略 limit/offset），用于前端分页计算。

---

### 3. 获取单条推理详情

```
GET /history/{request_id}
```

**路径参数**

| 参数 | 说明 |
|------|------|
| `request_id` | 推理记录的唯一 ID（UUID） |

**响应体 `200`**

```json
{
  "request_id": "550e8400-e29b-41d4-a716-446655440000",
  "prompt": "完整的输入 prompt 内容",
  "result": "模型生成的完整文本",
  "status": "success",
  "duration_ms": 320,
  "max_tokens": 512,
  "temperature": 0.7,
  "created_at": "2026-03-25T10:00:00Z"
}
```

**错误**

| 状态码 | 触发条件 |
|--------|---------|
| `404` | `request_id` 不存在于数据库 |

---

### 4. 重试推理请求

```
POST /inference/{request_id}/retry
```

读取原记录的 `prompt`、`max_tokens`、`temperature`，重新提交推理并生成新的 `request_id`。

**路径参数**

| 参数 | 说明 |
|------|------|
| `request_id` | 原推理记录的 UUID |

**响应体 `200`**（格式同"提交推理请求"）

```json
{
  "request_id": "新生成的 UUID",
  "result": "模型生成的文本内容",
  "status": "success",
  "created_at": "2026-03-25T10:05:00Z"
}
```

**错误**

| 状态码 | 触发条件 |
|--------|---------|
| `404` | 原 `request_id` 不存在 |

---

## 内部调度协议（预留）

网关通过 `_call_scheduler` 方法与下游调度器通信。当前为 mock 实现，
待调度器服务就绪后，替换为实际 HTTP 调用：

```
POST http://<SCHEDULER_HOST>/api/v1/schedule
Content-Type: application/json

{
  "prompt": "string",
  "max_tokens": 512,
  "temperature": 0.7
}
```

预期响应：

```json
{
  "result": "string",
  "duration_ms": 320
}
```

---

## 数据库表结构

表名：`request_records`（SQLite）

| 字段 | 类型 | 说明 |
|------|------|------|
| `id` | INTEGER PK | 自增主键 |
| `request_id` | TEXT UNIQUE | UUID，对外暴露的标识 |
| `prompt` | TEXT | 完整输入文本 |
| `max_tokens` | INTEGER | 请求参数 |
| `temperature` | REAL | 请求参数 |
| `result` | TEXT | 推理结果（可为 NULL） |
| `status` | TEXT | `success` / `failed` |
| `created_at` | DATETIME | UTC 时间戳 |
| `duration_ms` | INTEGER | 调度器耗时（毫秒，可为 NULL） |
