<template>
  <div class="batch-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <b>批量识别</b>
          <div class="header-actions" v-if="results.length">
            <el-button size="small" @click="exportCSV">导出 CSV</el-button>
            <el-button size="small" @click="exportJSON">导出 JSON</el-button>
          </div>
        </div>
      </template>

      <!-- Upload area -->
      <el-upload
        class="batch-upload"
        multiple
        drag
        :auto-upload="false"
        :show-file-list="false"
        accept="image/*"
        :on-change="onFilesChange"
        :disabled="running"
      >
        <el-icon size="36" color="#c0c4cc"><UploadFilled /></el-icon>
        <p>拖拽多张图片到此处，或<em>点击上传</em></p>
        <p class="upload-hint">支持 JPG/PNG/BMP/WebP，最多 50 张</p>
      </el-upload>

      <!-- File list -->
      <div v-if="files.length" class="file-list">
        <div
          v-for="(f, i) in files"
          :key="f.name + i"
          class="file-item"
        >
          <el-icon color="#909399"><Document /></el-icon>
          <span class="file-name">{{ f.name }}</span>
          <span class="file-size">{{ (f.size / 1024).toFixed(1) }} KB</span>
          <el-icon class="remove-icon" @click="removeFile(i)"><Close /></el-icon>
        </div>
      </div>

      <!-- Actions -->
      <div class="batch-actions">
        <el-button
          type="primary"
          :loading="running"
          :disabled="!files.length"
          @click="runBatch"
        >
          <el-icon><VideoPlay /></el-icon>
          {{ running ? `处理中 ${completedCount}/${totalCount}…` : `开始批量识别（${files.length} 张）` }}
        </el-button>
        <el-button v-if="files.length" @click="clearAll" :disabled="running">
          清空
        </el-button>
      </div>

      <!-- Progress -->
      <el-progress
        v-if="running || (taskStatus === 'done' && totalCount > 0)"
        :percentage="progress"
        :status="taskStatus === 'done' ? 'success' : taskStatus === 'failed' ? 'exception' : ''"
        style="margin-top: 12px"
      />

      <!-- Results table -->
      <div v-if="results.length" class="results-section">
        <div class="results-title">识别结果（{{ results.length }} 条）</div>
        <el-table :data="results" size="small" stripe max-height="400">
          <el-table-column label="文件名" prop="filename" min-width="140" show-overflow-tooltip />
          <el-table-column label="结果" width="100">
            <template #default="{ row }">
              <el-tag :type="tagType(row.result_type)" size="small">
                {{ row.label_zh || row.label }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="置信度" width="90">
            <template #default="{ row }">
              {{ (row.confidence * 100).toFixed(1) }}%
            </template>
          </el-table-column>
          <el-table-column label="耗时(ms)" width="90">
            <template #default="{ row }">{{ row.elapsed_ms?.toFixed(0) }}</template>
          </el-table-column>
          <el-table-column label="标注图" width="80">
            <template #default="{ row }">
              <el-image
                v-if="row.annotated_image_url"
                :src="row.annotated_image_url"
                style="width:40px;height:40px;object-fit:cover;border-radius:4px"
                :preview-src-list="[row.annotated_image_url]"
              />
              <span v-else style="color:#c0c4cc">—</span>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { inferBatch, getTaskStatus } from '@/api/index.js'

const POLL_INTERVAL_MS = 800
const POLL_TIMEOUT_MS = 5 * 60 * 1000  // 5 minutes

const files = ref([])
const running = ref(false)
const taskStatus = ref('')
const completedCount = ref(0)
const totalCount = ref(0)
const results = ref([])

const progress = computed(() =>
  totalCount.value ? Math.round((completedCount.value / totalCount.value) * 100) : 0
)

function tagType(type) {
  return { pest: 'danger', disease: 'warning', healthy: 'success', error: 'info' }[type] || 'info'
}

function onFilesChange(file) {
  if (files.value.length >= 50) {
    ElMessage.warning('最多上传 50 张图片')
    return
  }
  if (!files.value.find((f) => f.name === file.raw.name && f.size === file.raw.size)) {
    files.value.push(file.raw)
  }
}

function removeFile(index) {
  files.value.splice(index, 1)
}

function clearAll() {
  files.value = []
  results.value = []
  completedCount.value = 0
  totalCount.value = 0
  taskStatus.value = ''
}

async function runBatch() {
  if (!files.value.length) return
  running.value = true
  results.value = []
  completedCount.value = 0
  taskStatus.value = 'pending'

  try {
    const res = await inferBatch(files.value)
    const taskId = res.task_id
    totalCount.value = res.total
    await pollTask(taskId)
  } catch {
    running.value = false
    taskStatus.value = 'failed'
  }
}

async function pollTask(taskId) {
  const deadline = Date.now() + POLL_TIMEOUT_MS
  while (Date.now() < deadline) {
    await new Promise((r) => setTimeout(r, POLL_INTERVAL_MS))
    try {
      const t = await getTaskStatus(taskId)
      completedCount.value = t.completed
      taskStatus.value = t.status
      if (t.status === 'done' || t.status === 'failed') {
        results.value = t.results || []
        running.value = false
        if (t.status === 'done') ElMessage.success(`批量识别完成，共 ${results.value.length} 条`)
        else ElMessage.error(`任务失败: ${t.error || '未知错误'}`)
        return
      }
    } catch {
      running.value = false
      taskStatus.value = 'failed'
      return
    }
  }
  // Timeout reached
  running.value = false
  taskStatus.value = 'failed'
  ElMessage.error('任务等待超时（5分钟），请检查后端服务')
}

function exportCSV() {
  const headers = ['文件名', '结果类型', '中文标签', '置信度', '耗时(ms)']
  const rows = results.value.map((r) => [
    r.filename,
    r.result_type,
    r.label_zh || r.label,
    (r.confidence * 100).toFixed(1) + '%',
    r.elapsed_ms?.toFixed(0)
  ])
  const csv = [headers, ...rows].map((r) => r.map((c) => `"${c}"`).join(',')).join('\n')
  const bom = '\uFEFF'
  download(bom + csv, 'batch_results.csv', 'text/csv')
}

function exportJSON() {
  download(JSON.stringify(results.value, null, 2), 'batch_results.json', 'application/json')
}

function download(content, filename, type) {
  const blob = new Blob([content], { type })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = filename
  a.click()
  URL.revokeObjectURL(url)
}
</script>

<style scoped>
.batch-page { height: 100%; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.header-actions { display: flex; gap: 8px; }
.batch-upload :deep(.el-upload-dragger) { padding: 20px; height: 140px; width: 100%; }
.batch-upload em { color: #409eff; font-style: normal; }
.upload-hint { font-size: 12px; color: #909399; margin: 4px 0 0; }
.file-list { margin: 12px 0; max-height: 180px; overflow-y: auto; }
.file-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 6px 8px;
  border-radius: 4px;
  font-size: 13px;
}
.file-item:hover { background: #f5f7fa; }
.file-name { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.file-size { color: #909399; white-space: nowrap; }
.remove-icon { cursor: pointer; color: #c0c4cc; }
.remove-icon:hover { color: #f56c6c; }
.batch-actions { display: flex; gap: 8px; margin-top: 8px; }
.results-section { margin-top: 20px; }
.results-title { font-size: 14px; font-weight: 600; margin-bottom: 8px; color: #303133; }
</style>
