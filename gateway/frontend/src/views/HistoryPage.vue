<template>
  <div>
    <el-card shadow="never" class="list-card">
      <template #header>
        <div class="list-header">
          <span class="card-title">
            <el-icon><List /></el-icon> 历史记录（最近 20 条）
          </span>

          <!-- 筛选工具栏 -->
          <div class="toolbar">
            <el-select
              v-model="filterStatus"
              placeholder="全部状态"
              clearable
              style="width:130px"
              @change="applyFilter"
            >
              <el-option label="全部" value="" />
              <el-option label="成功" value="success" />
              <el-option label="失败" value="failed" />
            </el-select>

            <el-select
              v-model="sortOrder"
              style="width:130px"
              @change="applyFilter"
            >
              <el-option label="最新优先" value="desc" />
              <el-option label="最早优先" value="asc" />
            </el-select>

            <el-button
              :loading="listLoading"
              @click="loadHistory"
              :icon="Refresh"
            >
              刷新
            </el-button>
          </div>
        </div>
      </template>

      <el-alert
        v-if="listError"
        :title="listError"
        type="error"
        show-icon
        :closable="false"
        style="margin-bottom:16px"
      />

      <el-table
        :data="displayedRows"
        v-loading="listLoading"
        stripe
        style="width:100%"
        row-key="request_id"
        @row-click="toggleExpand"
        :row-class-name="() => 'clickable-row'"
        empty-text="暂无记录"
      >
        <!-- 展开列 -->
        <el-table-column type="expand">
          <template #default="{ row }">
            <div v-if="!row._detailLoading && !row._detail" class="expand-loading">
              <el-icon class="is-loading"><Loading /></el-icon> 加载中...
            </div>
            <div v-else-if="row._detailError" class="expand-error">
              <el-alert :title="row._detailError" type="error" :closable="false" show-icon />
            </div>
            <div v-else-if="row._detail" class="expand-content">
              <el-row :gutter="24">
                <el-col :span="12">
                  <div class="expand-label">完整 Prompt</div>
                  <pre class="expand-pre">{{ row._detail.prompt }}</pre>
                </el-col>
                <el-col :span="12">
                  <div class="expand-label">推理结果</div>
                  <pre class="expand-pre">{{ row._detail.result ?? '—' }}</pre>
                </el-col>
              </el-row>
              <el-row :gutter="24" style="margin-top:12px">
                <el-col :span="8">
                  <div class="expand-label">耗时</div>
                  <el-text>{{ row._detail.elapsed_ms != null ? row._detail.elapsed_ms + ' ms' : '—' }}</el-text>
                </el-col>
                <el-col :span="8">
                  <div class="expand-label">Max Tokens</div>
                  <el-text>{{ row._detail.max_tokens ?? '—' }}</el-text>
                </el-col>
                <el-col :span="8">
                  <div class="expand-label">Temperature</div>
                  <el-text>{{ row._detail.temperature ?? '—' }}</el-text>
                </el-col>
              </el-row>
            </div>
          </template>
        </el-table-column>

        <el-table-column prop="request_id" label="Request ID" min-width="200">
          <template #default="{ row }">
            <el-text size="small" style="font-family:monospace">{{ row.request_id }}</el-text>
          </template>
        </el-table-column>

        <el-table-column prop="prompt_preview" label="Prompt 预览" min-width="220" show-overflow-tooltip />

        <el-table-column prop="status" label="状态" width="90">
          <template #default="{ row }">
            <el-tag
              :type="row.status === 'success' ? 'success' : 'danger'"
              size="small"
              effect="light"
            >
              {{ row.status === 'success' ? '成功' : '失败' }}
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="created_at" label="创建时间" width="180" sortable>
          <template #default="{ row }">
            {{ formatDate(row.created_at) }}
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { Refresh, Loading } from '@element-plus/icons-vue'
import { fetchHistory, fetchInferenceDetail } from '../api/inference'

const rows = ref([])            // 原始数据
const displayedRows = ref([])  // 筛选/排序后的数据
const listLoading = ref(false)
const listError = ref(null)

const filterStatus = ref('')
const sortOrder = ref('desc')

// 展开行状态（由 el-table 内部管理，额外存明细数据在行对象上）
const expandedIds = reactive(new Set())

async function loadHistory() {
  listLoading.value = true
  listError.value = null
  try {
    const data = await fetchHistory({ limit: 20 })
    // 兼容直接返回数组 or { items: [] }
    rows.value = Array.isArray(data) ? data : (data.items ?? [])
    applyFilter()
  } catch (err) {
    listError.value = err.message
  } finally {
    listLoading.value = false
  }
}

function applyFilter() {
  let list = [...rows.value]

  if (filterStatus.value) {
    list = list.filter((r) => r.status === filterStatus.value)
  }

  list.sort((a, b) => {
    const ta = new Date(a.created_at).getTime()
    const tb = new Date(b.created_at).getTime()
    return sortOrder.value === 'desc' ? tb - ta : ta - tb
  })

  displayedRows.value = list
}

async function toggleExpand(row) {
  if (row._detail || row._detailLoading) return
  row._detailLoading = true
  try {
    const detail = await fetchInferenceDetail(row.request_id)
    row._detail = detail
  } catch (err) {
    row._detailError = err.message
  } finally {
    row._detailLoading = false
  }
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', {
    year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', second: '2-digit',
  })
}

onMounted(loadHistory)
</script>

<style scoped>
.list-card { border-radius: 12px; }

.list-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.toolbar {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

:deep(.clickable-row) { cursor: pointer; }
:deep(.clickable-row:hover td) { background: #ecf5ff !important; }

.expand-loading {
  color: #909399;
  padding: 12px 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.expand-error { padding: 12px 16px; }
.expand-content { padding: 16px 24px; }
.expand-label {
  font-size: 12px;
  color: #909399;
  margin-bottom: 4px;
}
.expand-pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Courier New', monospace;
  font-size: 13px;
  line-height: 1.55;
  background: #f5f7fa;
  padding: 12px;
  border-radius: 6px;
  max-height: 240px;
  overflow-y: auto;
}
</style>
