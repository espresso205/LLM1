<template>
  <el-container style="min-height: 100vh;">
    <el-header height="60px" class="header">
      <div class="logo">推理网关</div>
      <el-menu
        :default-active="activeRoute"
        mode="horizontal"
        router
        background-color="transparent"
        text-color="#fff"
        active-text-color="#ffd04b"
        class="nav-menu"
      >
        <el-menu-item index="/submit">
          <el-icon><Edit /></el-icon>推理提交
        </el-menu-item>
        <el-menu-item index="/history">
          <el-icon><List /></el-icon>历史记录
        </el-menu-item>
      </el-menu>
    </el-header>

    <el-main class="main-content">
      <router-view />
    </el-main>
  </el-container>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const activeRoute = computed(() => route.path)
</script>

<style>
* { box-sizing: border-box; margin: 0; padding: 0; }
body { font-family: 'Helvetica Neue', Arial, sans-serif; background: #f5f7fa; }

.header {
  background: linear-gradient(135deg, #409eff 0%, #006adb 100%);
  display: flex;
  align-items: center;
  padding: 0 24px;
  box-shadow: 0 2px 8px rgba(0,0,0,.15);
}
.logo {
  color: #fff;
  font-size: 18px;
  font-weight: 700;
  margin-right: 32px;
  white-space: nowrap;
}
.nav-menu {
  border-bottom: none !important;
  flex: 1;
}
.nav-menu .el-menu-item {
  color: rgba(255,255,255,.85) !important;
}
.main-content {
  max-width: 960px;
  margin: 0 auto;
  padding: 32px 24px;
}
</style>
