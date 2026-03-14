<template>
  <el-container class="layout-container">
    <!-- Sidebar -->
    <el-aside width="200px" class="sidebar">
      <div class="logo">
        <el-icon size="28" color="#67c23a"><Leaf /></el-icon>
        <span>番茄识别系统</span>
      </div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#1e3a1e"
        text-color="#c0e8a0"
        active-text-color="#ffffff"
      >
        <el-menu-item index="/">
          <el-icon><HomeFilled /></el-icon>
          <span>首页</span>
        </el-menu-item>
        <el-menu-item index="/infer">
          <el-icon><Search /></el-icon>
          <span>单张识别</span>
        </el-menu-item>
        <el-menu-item index="/batch">
          <el-icon><Files /></el-icon>
          <span>批量识别</span>
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><Clock /></el-icon>
          <span>历史记录</span>
        </el-menu-item>
        <el-menu-item index="/settings">
          <el-icon><Setting /></el-icon>
          <span>参数设置</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <!-- Main content -->
    <el-container>
      <el-header class="top-header">
        <span class="page-title">{{ pageTitle }}</span>
        <div class="header-status">
          <el-tag :type="modelsLoaded ? 'success' : 'warning'" size="small" effect="light">
            <el-icon><CircleCheck v-if="modelsLoaded" /><Warning v-else /></el-icon>
            {{ modelsLoaded ? '模型已加载' : '模型未加载' }}
          </el-tag>
        </div>
      </el-header>
      <el-main class="main-content">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { healthCheck } from '@/api/index.js'

const route = useRoute()
const modelsLoaded = ref(false)

const activeMenu = computed(() => route.path)
const pageTitle = computed(() => route.meta?.title || '番茄病虫害智能识别系统')

onMounted(async () => {
  try {
    const res = await healthCheck()
    modelsLoaded.value = res.models_loaded
  } catch {
    modelsLoaded.value = false
  }
})
</script>

<style>
* {
  box-sizing: border-box;
}
html,
body,
#app {
  height: 100%;
  margin: 0;
  font-family: 'PingFang SC', 'Microsoft YaHei', sans-serif;
}
.layout-container {
  height: 100vh;
}
.sidebar {
  background: #1e3a1e;
  display: flex;
  flex-direction: column;
}
.sidebar .el-menu {
  border-right: none;
  flex: 1;
}
.logo {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 18px 16px;
  color: #c0e8a0;
  font-size: 15px;
  font-weight: 600;
  border-bottom: 1px solid #2e5a2e;
}
.top-header {
  background: #fff;
  border-bottom: 1px solid #e4e7ed;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
  height: 56px;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
  color: #303133;
}
.header-status {
  display: flex;
  align-items: center;
  gap: 8px;
}
.main-content {
  background: #f5f7fa;
  overflow-y: auto;
}
</style>
