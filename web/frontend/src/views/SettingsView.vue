<template>
  <div class="settings-page">
    <el-card shadow="never" style="max-width:640px">
      <template #header><b>参数设置</b></template>

      <el-form :model="form" label-width="160px" size="default">
        <el-form-item label="虫害检测阈值">
          <div class="slider-wrap">
            <el-slider
              v-model="form.pest_conf_threshold"
              :min="0.1" :max="1" :step="0.01"
              show-input
              :input-size="'small'"
            />
          </div>
          <div class="hint">YOLO 虫害检测置信度下限，低于此值的检测框将被丢弃（默认 0.5）</div>
        </el-form-item>

        <el-form-item label="病害分类阈值">
          <div class="slider-wrap">
            <el-slider
              v-model="form.disease_conf_threshold"
              :min="0.1" :max="1" :step="0.01"
              show-input
              :input-size="'small'"
            />
          </div>
          <div class="hint">病害分类概率低于此值时判定为"健康（置信度低）"（默认 0.5）</div>
        </el-form-item>

        <el-form-item label="健康判定阈值">
          <div class="slider-wrap">
            <el-slider
              v-model="form.healthy_threshold"
              :min="0.1" :max="1" :step="0.01"
              show-input
              :input-size="'small'"
            />
          </div>
          <div class="hint">分类结果为"healthy"且置信度高于此值才判定为健康（默认 0.8）</div>
        </el-form-item>

        <el-form-item>
          <el-button type="primary" :loading="saving" @click="save">
            <el-icon><Check /></el-icon> 保存设置
          </el-button>
          <el-button @click="reset">恢复默认</el-button>
        </el-form-item>
      </el-form>

      <el-divider />

      <el-descriptions title="当前生效设置" :column="1" border size="small">
        <el-descriptions-item label="虫害检测阈值">{{ current.pest_conf_threshold }}</el-descriptions-item>
        <el-descriptions-item label="病害分类阈值">{{ current.disease_conf_threshold }}</el-descriptions-item>
        <el-descriptions-item label="健康判定阈值">{{ current.healthy_threshold }}</el-descriptions-item>
      </el-descriptions>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getModels, updateSettings } from '@/api/index.js'

const defaults = { pest_conf_threshold: 0.5, disease_conf_threshold: 0.5, healthy_threshold: 0.8 }

const form = ref({ ...defaults })
const current = ref({ ...defaults })
const saving = ref(false)

onMounted(async () => {
  try {
    const info = await getModels()
    if (info.settings) {
      Object.assign(current.value, info.settings)
      Object.assign(form.value, info.settings)
    }
  } catch {}
})

async function save() {
  saving.value = true
  try {
    const res = await updateSettings(form.value)
    Object.assign(current.value, res.settings)
    ElMessage.success('设置已保存')
  } catch {
    // interceptor handles
  } finally {
    saving.value = false
  }
}

function reset() {
  Object.assign(form.value, defaults)
}
</script>

<style scoped>
.settings-page { height: 100%; }
.slider-wrap { width: 100%; }
.hint { font-size: 12px; color: #909399; margin-top: 4px; line-height: 1.5; }
</style>
