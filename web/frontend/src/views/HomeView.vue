<template>
  <div class="home-page">
    <!-- Hero -->
    <el-card class="hero-card" shadow="never">
      <div class="hero-content">
        <div class="hero-text">
          <h1 class="hero-title">🍅 番茄病虫害智能识别系统</h1>
          <p class="hero-desc">
            基于深度学习的番茄叶片病虫害识别平台，支持单张识别、批量处理与历史追溯。
            采用级联流程：<strong>虫害检测（YOLOv8）</strong> → <strong>病害分类（ResNet）</strong>，准确高效。
          </p>
          <div class="hero-actions">
            <el-button type="primary" size="large" @click="$router.push('/infer')">
              <el-icon><Search /></el-icon> 开始识别
            </el-button>
            <el-button size="large" @click="$router.push('/batch')">
              <el-icon><Files /></el-icon> 批量识别
            </el-button>
          </div>
        </div>
        <div class="hero-icon">🍃</div>
      </div>
    </el-card>

    <!-- Model Status -->
    <el-row :gutter="16" class="status-row">
      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="status-card">
          <div class="status-header">
            <el-icon size="24" :color="pestLoaded ? '#67c23a' : '#e6a23c'">
              <component :is="pestLoaded ? 'CircleCheck' : 'Warning'" />
            </el-icon>
            <span class="status-label">虫害检测模型</span>
            <el-tag :type="pestLoaded ? 'success' : 'warning'" size="small">
              {{ pestLoaded ? '已加载' : '未加载' }}
            </el-tag>
          </div>
          <div class="status-body">
            <div class="status-row-item">
              <span class="key">文件名</span><span class="val">pest_detect.pt</span>
            </div>
            <div class="status-row-item">
              <span class="key">类型</span><span class="val">YOLOv8</span>
            </div>
            <div class="status-row-item">
              <span class="key">阈值</span>
              <span class="val">{{ modelInfo.settings?.pest_conf_threshold ?? '—' }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="12" :md="8">
        <el-card shadow="hover" class="status-card">
          <div class="status-header">
            <el-icon size="24" :color="diseaseLoaded ? '#67c23a' : '#e6a23c'">
              <component :is="diseaseLoaded ? 'CircleCheck' : 'Warning'" />
            </el-icon>
            <span class="status-label">病害分类模型</span>
            <el-tag :type="diseaseLoaded ? 'success' : 'warning'" size="small">
              {{ diseaseLoaded ? '已加载' : '未加载' }}
            </el-tag>
          </div>
          <div class="status-body">
            <div class="status-row-item">
              <span class="key">文件名</span><span class="val">disease_cls.pth</span>
            </div>
            <div class="status-row-item">
              <span class="key">类别数</span>
              <span class="val">{{ modelInfo.disease_cls?.classes?.length ?? '—' }}</span>
            </div>
            <div class="status-row-item">
              <span class="key">阈值</span>
              <span class="val">{{ modelInfo.settings?.disease_conf_threshold ?? '—' }}</span>
            </div>
          </div>
        </el-card>
      </el-col>

      <el-col :xs="24" :sm="24" :md="8">
        <el-card shadow="hover" class="status-card">
          <div class="status-header">
            <el-icon size="24" color="#409eff"><DataAnalysis /></el-icon>
            <span class="status-label">系统统计</span>
          </div>
          <div class="status-body">
            <div class="status-row-item">
              <span class="key">历史记录数</span>
              <span class="val">{{ historyTotal }}</span>
            </div>
            <div class="status-row-item">
              <span class="key">健康阈值</span>
              <span class="val">{{ modelInfo.settings?.healthy_threshold ?? '—' }}</span>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Workflow -->
    <el-card shadow="never" class="workflow-card">
      <template #header><b>识别流程</b></template>
      <div class="workflow">
        <div class="step">
          <div class="step-icon">📷</div>
          <div class="step-text">上传图片</div>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-icon">🔍</div>
          <div class="step-text">虫害检测<br />(YOLOv8)</div>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-icon">🌿</div>
          <div class="step-text">病害分类<br />(ResNet)</div>
        </div>
        <div class="step-arrow">→</div>
        <div class="step">
          <div class="step-icon">📊</div>
          <div class="step-text">结果输出</div>
        </div>
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { getModels, getHistory } from '@/api/index.js'

const modelInfo = ref({ settings: {}, pest_detect: {}, disease_cls: {} })
const historyTotal = ref(0)

const pestLoaded = computed(() => modelInfo.value.pest_detect?.loaded)
const diseaseLoaded = computed(() => modelInfo.value.disease_cls?.loaded)

onMounted(async () => {
  try {
    modelInfo.value = await getModels()
  } catch {}
  try {
    const h = await getHistory(1, 1)
    historyTotal.value = h.total
  } catch {}
})
</script>

<style scoped>
.home-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.hero-card {
  background: linear-gradient(135deg, #1e3a1e 0%, #2d6a2d 100%);
  color: #fff;
  border: none;
}
.hero-content {
  display: flex;
  align-items: center;
  justify-content: space-between;
}
.hero-title {
  font-size: 26px;
  font-weight: 700;
  color: #fff;
  margin: 0 0 10px;
}
.hero-desc {
  color: #c0e8a0;
  font-size: 14px;
  line-height: 1.7;
  max-width: 640px;
  margin: 0 0 20px;
}
.hero-actions {
  display: flex;
  gap: 12px;
}
.hero-icon {
  font-size: 80px;
  opacity: 0.6;
}
.status-row {
  margin-top: 0;
}
.status-card .status-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 12px;
}
.status-label {
  flex: 1;
  font-weight: 600;
  font-size: 14px;
  color: #303133;
}
.status-body .status-row-item {
  display: flex;
  justify-content: space-between;
  font-size: 13px;
  padding: 4px 0;
  border-bottom: 1px solid #f0f0f0;
}
.status-body .key {
  color: #909399;
}
.status-body .val {
  color: #303133;
  font-weight: 500;
}
.workflow-card {
  margin-top: 0;
}
.workflow {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
  padding: 8px 0;
}
.step {
  text-align: center;
  min-width: 80px;
}
.step-icon {
  font-size: 32px;
  margin-bottom: 6px;
}
.step-text {
  font-size: 13px;
  color: #606266;
  line-height: 1.4;
}
.step-arrow {
  font-size: 24px;
  color: #c0c4cc;
}
</style>
