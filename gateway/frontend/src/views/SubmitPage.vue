<template>
  <div>
    <el-card class="form-card" shadow="never">
      <template #header>
        <span class="card-title">
          <el-icon><Edit /></el-icon> 提交推理请求
        </span>
      </template>

      <el-form :model="form" label-position="top" :disabled="loading">
        <!-- Prompt 输入 -->
        <el-form-item label="Prompt">
          <el-input
            v-model="form.prompt"
            type="textarea"
            :rows="8"
            placeholder="在此输入推理内容..."
            resize="vertical"
          />
        </el-form-item>

        <!-- 参数配置 -->
        <el-row :gutter="32">
          <el-col :span="12">
            <el-form-item>
              <template #label>
                Max Tokens
                <el-tag size="small" style="margin-left:8px">{{ form.max_tokens }}</el-tag>
              </template>
              <el-slider
                v-model="form.max_tokens"
                :min="64"
                :max="4096"
                :step="64"
                show-input
                :input-size="'small'"
              />
            </el-form-item>
          </el-col>

          <el-col :span="12">
            <el-form-item>
              <template #label>
                Temperature
                <el-tag size="small" style="margin-left:8px">{{ form.temperature.toFixed(2) }}</el-tag>
              </template>
              <el-slider
                v-model="form.temperature"
                :min="0"
                :max="2"
                :step="0.01"
                show-input
                :input-size="'small'"
              />
            </el-form-item>
          </el-col>
        </el-row>

        <!-- 提交按钮 -->
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            :loading="loading"
            :disabled="!form.prompt.trim()"
            @click="handleSubmit"
          >
            {{ loading ? '推理中...' : '提交' }}
          </el-button>
          <el-button size="large" @click="resetForm" :disabled="loading">重置</el-button>
        </el-form-item>
      </el-form>
    </el-card>

    <!-- 成功结果 -->
    <el-card v-if="result" class="result-card" shadow="never">
      <template #header>
        <div style="display:flex;justify-content:space-between;align-items:center">
          <span class="card-title">
            <el-icon><CircleCheck /></el-icon> 推理结果
          </span>
          <el-tag type="success" size="small">{{ result.request_id }}</el-tag>
        </div>
      </template>

      <div class="result-meta">
        <span class="meta-label">Request ID：</span>
        <el-text type="info" size="small" style="font-family:monospace">{{ result.request_id }}</el-text>
      </div>

      <el-divider />

      <div class="result-body">
        <pre>{{ result.result }}</pre>
      </div>
    </el-card>

    <!-- 错误提示 -->
    <el-card v-if="error" class="error-card" shadow="never">
      <template #header>
        <span class="card-title" style="color:#f56c6c">
          <el-icon><CircleClose /></el-icon> 请求失败
        </span>
      </template>
      <el-alert :title="error" type="error" show-icon :closable="false" />
      <div style="margin-top:16px">
        <el-button type="danger" @click="handleSubmit">重试</el-button>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { submitInference } from '../api/inference'

const form = reactive({
  prompt: '',
  max_tokens: 512,
  temperature: 0.7,
})

const loading = ref(false)
const result = ref(null)
const error = ref(null)

async function handleSubmit() {
  if (!form.prompt.trim()) return
  loading.value = true
  result.value = null
  error.value = null

  try {
    const data = await submitInference({
      prompt: form.prompt,
      max_tokens: form.max_tokens,
      temperature: form.temperature,
    })
    result.value = data
  } catch (err) {
    error.value = err.message
  } finally {
    loading.value = false
  }
}

function resetForm() {
  form.prompt = ''
  form.max_tokens = 512
  form.temperature = 0.7
  result.value = null
  error.value = null
}
</script>

<style scoped>
.form-card, .result-card, .error-card {
  border-radius: 12px;
  margin-bottom: 24px;
}
.card-title {
  font-size: 15px;
  font-weight: 600;
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.result-meta {
  margin-bottom: 8px;
}
.meta-label {
  font-size: 13px;
  color: #909399;
}
.result-body pre {
  white-space: pre-wrap;
  word-break: break-word;
  font-family: 'Courier New', monospace;
  font-size: 14px;
  line-height: 1.6;
  background: #f5f7fa;
  padding: 16px;
  border-radius: 8px;
  max-height: 400px;
  overflow-y: auto;
}
</style>
