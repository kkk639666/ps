<template>
  <div class="infer-page">
    <el-row :gutter="24">
      <!-- Left: Upload -->
      <el-col :xs="24" :md="10">
        <el-card shadow="never">
          <template #header><b>上传图片</b></template>

          <el-upload
            class="upload-area"
            drag
            :auto-upload="false"
            :show-file-list="false"
            accept="image/*"
            :on-change="onFileChange"
          >
            <div v-if="!previewUrl" class="upload-placeholder">
              <el-icon size="48" color="#c0c4cc"><UploadFilled /></el-icon>
              <p>拖拽图片到此处，或<em>点击上传</em></p>
              <p class="upload-hint">支持 JPG / PNG / BMP / WebP</p>
            </div>
            <div v-else class="preview-wrap">
              <img :src="previewUrl" class="preview-img" alt="预览" />
              <div class="preview-mask">点击重新选择</div>
            </div>
          </el-upload>

          <div class="upload-actions">
            <el-button
              type="primary"
              :loading="loading"
              :disabled="!selectedFile"
              @click="runInfer"
              style="width: 100%"
            >
              <el-icon><Search /></el-icon>
              {{ loading ? '识别中…' : '开始识别' }}
            </el-button>
          </div>

          <!-- Upload progress -->
          <el-progress
            v-if="uploadPct > 0 && uploadPct < 100"
            :percentage="uploadPct"
            status="striped"
            striped-flow
            :duration="6"
            style="margin-top: 12px"
          />
        </el-card>
      </el-col>

      <!-- Right: Result -->
      <el-col :xs="24" :md="14">
        <el-card shadow="never">
          <template #header><b>识别结果</b></template>

          <div v-if="!result" class="empty-result">
            <el-empty description="请上传图片后点击「开始识别」" />
          </div>

          <template v-else>
            <!-- Result badge -->
            <div class="result-summary">
              <el-tag
                size="large"
                :type="resultTagType"
                effect="dark"
                class="result-tag"
              >
                {{ result.label_zh || result.label }}
              </el-tag>
              <div class="result-meta">
                <span>置信度：<b>{{ (result.confidence * 100).toFixed(1) }}%</b></span>
                <span>耗时：<b>{{ result.elapsed_ms?.toFixed(0) }} ms</b></span>
              </div>
            </div>

            <!-- Message -->
            <el-alert
              v-if="result.message"
              :title="result.message"
              :type="result.result_type === 'error' ? 'error' : 'info'"
              show-icon
              :closable="false"
              style="margin-bottom: 12px"
            />

            <!-- Images -->
            <el-row :gutter="12">
              <el-col :span="result.annotated_image_url ? 12 : 24">
                <div class="img-wrap">
                  <div class="img-label">原始图片</div>
                  <el-image
                    :src="result.input_image_url"
                    fit="contain"
                    class="result-img"
                    :preview-src-list="[result.input_image_url]"
                  />
                </div>
              </el-col>
              <el-col v-if="result.annotated_image_url" :span="12">
                <div class="img-wrap">
                  <div class="img-label">检测标注图</div>
                  <el-image
                    :src="result.annotated_image_url"
                    fit="contain"
                    class="result-img"
                    :preview-src-list="[result.annotated_image_url]"
                  />
                </div>
              </el-col>
            </el-row>

            <!-- Bounding boxes table -->
            <template v-if="result.boxes && result.boxes.length">
              <div class="section-title">检测框详情</div>
              <el-table :data="result.boxes" size="small" stripe>
                <el-table-column label="标签" prop="label" width="80" />
                <el-table-column label="置信度" width="90">
                  <template #default="{ row }">
                    {{ (row.confidence * 100).toFixed(1) }}%
                  </template>
                </el-table-column>
                <el-table-column label="位置 (x1,y1,x2,y2)">
                  <template #default="{ row }">
                    {{ row.x1.toFixed(0) }}, {{ row.y1.toFixed(0) }},
                    {{ row.x2.toFixed(0) }}, {{ row.y2.toFixed(0) }}
                  </template>
                </el-table-column>
              </el-table>
            </template>
          </template>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, computed, onUnmounted } from 'vue'
import { ElMessage } from 'element-plus'
import { inferSingle } from '@/api/index.js'

const selectedFile = ref(null)
const previewUrl = ref('')
const loading = ref(false)
const uploadPct = ref(0)
const result = ref(null)

const resultTagType = computed(() => {
  const map = { pest: 'danger', disease: 'warning', healthy: 'success', error: 'info' }
  return map[result.value?.result_type] || 'info'
})

function onFileChange(file) {
  // Revoke previous object URL to free memory
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
  selectedFile.value = file.raw
  previewUrl.value = URL.createObjectURL(file.raw)
  result.value = null
  uploadPct.value = 0
}

async function runInfer() {
  if (!selectedFile.value) return
  loading.value = true
  uploadPct.value = 0
  result.value = null
  try {
    result.value = await inferSingle(selectedFile.value, (e) => {
      uploadPct.value = Math.round((e.loaded / e.total) * 100)
    })
    ElMessage.success('识别完成')
  } catch {
    // error already shown by interceptor
  } finally {
    loading.value = false
    uploadPct.value = 0
  }
}

onUnmounted(() => {
  if (previewUrl.value) URL.revokeObjectURL(previewUrl.value)
})
</script>

<style scoped>
.infer-page {
  height: 100%;
}
.upload-area :deep(.el-upload-dragger) {
  width: 100%;
  height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
}
.upload-placeholder {
  text-align: center;
}
.upload-placeholder em {
  color: #409eff;
  font-style: normal;
}
.upload-hint {
  font-size: 12px;
  color: #909399;
  margin: 4px 0 0;
}
.preview-wrap {
  position: relative;
  width: 100%;
  height: 100%;
}
.preview-img {
  width: 100%;
  height: 100%;
  object-fit: contain;
}
.preview-mask {
  position: absolute;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  color: #fff;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  opacity: 0;
  transition: opacity 0.2s;
}
.preview-wrap:hover .preview-mask {
  opacity: 1;
}
.upload-actions {
  margin-top: 12px;
}
.empty-result {
  min-height: 200px;
  display: flex;
  align-items: center;
  justify-content: center;
}
.result-summary {
  display: flex;
  align-items: center;
  gap: 16px;
  margin-bottom: 16px;
}
.result-tag {
  font-size: 15px;
  padding: 8px 16px;
}
.result-meta {
  display: flex;
  gap: 20px;
  font-size: 14px;
  color: #606266;
}
.img-wrap {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  overflow: hidden;
  background: #fafafa;
}
.img-label {
  font-size: 12px;
  color: #909399;
  padding: 6px 10px;
  border-bottom: 1px solid #e4e7ed;
}
.result-img {
  width: 100%;
  height: 200px;
  display: block;
}
.section-title {
  font-size: 13px;
  font-weight: 600;
  color: #606266;
  margin: 12px 0 6px;
}
</style>
