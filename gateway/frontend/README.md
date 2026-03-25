# Gateway Frontend

基于 Vue 3 + Element Plus 实现的推理网关前端。

## 功能页面

| 路径 | 说明 |
|------|------|
| `/submit` | 推理提交页面：输入 prompt、配置参数、查看结果 |
| `/history` | 历史记录页面：列表查看、筛选排序、点击展开详情 |

## 项目结构

```
frontend/
├── index.html
├── vite.config.js          # 开发服务器 & 代理配置
├── package.json
└── src/
    ├── main.js             # 应用入口，注册 Element Plus
    ├── App.vue             # 顶部导航布局
    ├── router/
    │   └── index.js        # Vue Router 路由定义
    ├── api/
    │   └── inference.js    # Axios 封装 + API 方法
    └── views/
        ├── SubmitPage.vue  # 推理提交页面
        └── HistoryPage.vue # 历史记录页面
```

## 快速启动

### 前提条件

- Node.js >= 18
- npm 或 yarn

### 安装依赖

```bash
cd gateway/frontend
npm install
```

### 启动开发服务器

```bash
npm run dev
```

浏览器访问 [http://localhost:5173](http://localhost:5173)，默认重定向到 `/submit`。

> **代理说明**：`vite.config.js` 已将 `/api` 路径代理到 `http://localhost:8000`，
> 确保后端服务在 8000 端口启动即可，无需手动配置跨域。
> 如需修改后端地址，编辑 `vite.config.js` 中的 `target`。

### 生产构建

```bash
npm run build    # 产物输出到 dist/
npm run preview  # 本地预览生产包
```

## API 接口约定

前端调用的后端接口如下，由 `src/api/inference.js` 统一管理：

| 方法 | 路径 | 说明 |
|------|------|------|
| `POST` | `/api/v1/inference` | 提交推理请求 |
| `GET` | `/api/v1/inference/history` | 获取历史记录列表（`?limit=20&status=success`） |
| `GET` | `/api/v1/inference/:id` | 获取单条记录详情 |

### 请求/响应示例

**POST /api/v1/inference**

```json

{ "prompt": "...", "max_tokens": 512, "temperature": 0.7 }


{ "request_id": "abc-123", "result": "..." }
```

**GET /api/v1/inference/history**

```json
[
  {
    "request_id": "abc-123",
    "prompt_preview": "你好，请...",
    "status": "success",
    "created_at": "2026-03-25T10:00:00Z"
  }
]
```

**GET /api/v1/inference/:id**

```json
{
  "request_id": "abc-123",
  "prompt": "完整 prompt 内容",
  "result": "推理结果",
  "elapsed_ms": 320,
  "max_tokens": 512,
  "temperature": 0.7
}
```

## 认证预留

`src/api/inference.js` 的请求拦截器中已预留 Bearer Token：

```js
const token = localStorage.getItem('access_token')
if (token) {
  config.headers.Authorization = `Bearer ${token}`
}
```

启用认证时，只需在 `localStorage` 中存入 `access_token` 即可自动附带。
