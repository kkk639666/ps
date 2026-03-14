<template>
  <div class="history-page">
    <el-card shadow="never">
      <template #header>
        <div class="card-header">
          <b>历史记录</b>
          <el-text type="info" size="small">共 {{ total }} 条</el-text>
        </div>
      </template>

      <el-table
        :data="records"
        v-loading="loading"
        size="small"
        stripe
        row-class-name="history-row"
        @row-click="openDetail"
        style="cursor:pointer"
      >
        <el-table-column label="时间" width="160">
          <template #default="{ row }">{{ formatDate(row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="文件名" prop="filename" min-width="150" show-overflow-tooltip />
        <el-table-column label="结果" width="120">
          <template #default="{ row }">
            <el-tag :type="tagType(row.result_type)" size="small">
              {{ row.label_zh || row.label }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="置信度" width="90">
          <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
        </el-table-column>
        <el-table-column label="耗时(ms)" width="90">
          <template #default="{ row }">{{ row.elapsed_ms?.toFixed(0) }}</template>
        </el-table-column>
        <el-table-column label="操作" width="80">
          <template #default="{ row }">
            <el-button link size="small" type="primary" @click.stop="openDetail(row)">
              详情
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination-wrap">
        <el-pagination
          v-model:current-page="page"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50]"
          layout="total, sizes, prev, pager, next"
          @change="loadHistory"
        />
      </div>
    </el-card>

    <!-- Detail Dialog -->
    <el-dialog v-model="dialogVisible" title="识别详情" width="720px" top="5vh">
      <div v-if="detailLoading" class="dialog-loading">
        <el-skeleton :rows="5" animated />
      </div>
      <template v-else-if="detail">
        <el-descriptions :column="2" border size="small">
          <el-descriptions-item label="文件名">{{ detail.filename }}</el-descriptions-item>
          <el-descriptions-item label="时间">{{ formatDate(detail.created_at) }}</el-descriptions-item>
          <el-descriptions-item label="结果类型">
            <el-tag :type="tagType(detail.result_type)" size="small">
              {{ detail.label_zh || detail.label }}
            </el-tag>
          </el-descriptions-item>
          <el-descriptions-item label="置信度">
            {{ (detail.confidence * 100).toFixed(2) }}%
          </el-descriptions-item>
          <el-descriptions-item label="耗时(ms)">{{ detail.elapsed_ms?.toFixed(0) }}</el-descriptions-item>
          <el-descriptions-item label="标签">{{ detail.label }}</el-descriptions-item>
        </el-descriptions>

        <el-row :gutter="12" style="margin-top:16px">
          <el-col :span="detail.annotated_image_url ? 12 : 24">
            <div class="img-box">
              <div class="img-label">原始图片</div>
              <el-image
                v-if="detail.input_image_url"
                :src="detail.input_image_url"
                fit="contain"
                style="width:100%;height:200px"
                :preview-src-list="[detail.input_image_url]"
              />
              <el-empty v-else description="图片不可用" :image-size="60" />
            </div>
          </el-col>
          <el-col v-if="detail.annotated_image_url" :span="12">
            <div class="img-box">
              <div class="img-label">标注图</div>
              <el-image
                :src="detail.annotated_image_url"
                fit="contain"
                style="width:100%;height:200px"
                :preview-src-list="[detail.annotated_image_url]"
              />
            </div>
          </el-col>
        </el-row>

        <template v-if="detail.boxes && detail.boxes.length">
          <div class="section-title">检测框（{{ detail.boxes.length }} 个）</div>
          <el-table :data="detail.boxes" size="small" stripe>
            <el-table-column label="标签" prop="label" width="80" />
            <el-table-column label="置信度" width="90">
              <template #default="{ row }">{{ (row.confidence * 100).toFixed(1) }}%</template>
            </el-table-column>
            <el-table-column label="坐标 (x1,y1,x2,y2)">
              <template #default="{ row }">
                {{ row.x1?.toFixed(0) }}, {{ row.y1?.toFixed(0) }},
                {{ row.x2?.toFixed(0) }}, {{ row.y2?.toFixed(0) }}
              </template>
            </el-table-column>
          </el-table>
        </template>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { getHistory, getHistoryDetail } from '@/api/index.js'

const records = ref([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const dialogVisible = ref(false)
const detailLoading = ref(false)
const detail = ref(null)

function tagType(type) {
  return { pest: 'danger', disease: 'warning', healthy: 'success', error: 'info' }[type] || 'info'
}

function formatDate(iso) {
  if (!iso) return '—'
  return new Date(iso).toLocaleString('zh-CN', { hour12: false })
}

async function loadHistory() {
  loading.value = true
  try {
    const res = await getHistory(page.value, pageSize.value)
    records.value = res.items
    total.value = res.total
  } catch {
    // handled by interceptor
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  dialogVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    detail.value = await getHistoryDetail(row.id)
  } catch {
    dialogVisible.value = false
  } finally {
    detailLoading.value = false
  }
}

onMounted(loadHistory)
</script>

<style scoped>
.history-page { height: 100%; }
.card-header { display: flex; align-items: center; justify-content: space-between; }
.pagination-wrap { display: flex; justify-content: flex-end; margin-top: 16px; }
.dialog-loading { padding: 20px 0; }
.img-box { border: 1px solid #e4e7ed; border-radius: 6px; overflow: hidden; background: #fafafa; }
.img-label { font-size: 12px; color: #909399; padding: 6px 10px; border-bottom: 1px solid #e4e7ed; }
.section-title { font-size: 13px; font-weight: 600; color: #606266; margin: 14px 0 6px; }
</style>
