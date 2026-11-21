<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { get, post, patch } from '../../utils/request'
import { useUserStore } from '../../store/user'
import { parseApiError } from '../../utils/error'
import { hardRedirectToLogin } from '../../utils/authRedirect'

const userStore = useUserStore()
const roleLabels: Record<string, string> = {
  super_admin: '超级管理员',
  operator: '运营主管',
  content_editor: '内容编辑',
  viewer: '只读查看',
}
const loading = ref(false)
const saving = ref(false)
const passwordSaving = ref(false)
const profile = ref({ id: 0, phone: '', nickname: '', admin_role: '' })
const passwordForm = ref({ old_password: '', new_password: '', confirm: '' })

async function load() {
  loading.value = true
  try {
    profile.value = await get('/api/v1/admin/me')
  } finally {
    loading.value = false
  }
}

async function saveProfile() {
  saving.value = true
  try {
    await patch('/api/v1/admin/me', { nickname: profile.value.nickname })
    ElMessage.success('资料已保存')
  } finally {
    saving.value = false
  }
}

async function changePassword() {
  if (passwordForm.value.new_password.length < 6) {
    ElMessage.warning('新密码至少 6 位')
    return
  }
  if (passwordForm.value.new_password !== passwordForm.value.confirm) {
    ElMessage.warning('两次密码不一致')
    return
  }
  passwordSaving.value = true
  try {
    await post(
      '/api/v1/admin/me/password',
      {
        old_password: passwordForm.value.old_password,
        new_password: passwordForm.value.new_password,
      },
      { skipGlobalErrorHandler: true },
    )
    userStore.logout()
    ElMessage.success('密码已修改，请重新登录')
    hardRedirectToLogin('/admin', 'password_changed')
  } catch (err) {
    ElMessage.error(parseApiError(err))
  } finally {
    passwordSaving.value = false
  }
}

onMounted(load)
</script>

<template>
  <div v-loading="loading" class="admin-page">
    <div class="admin-page-header">
      <div>
        <h2>管理员资料</h2>
        <p class="admin-page-desc">管理您的账号信息与登录密码</p>
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :xs="24" :lg="12">
        <el-card shadow="never" header="基本资料">
          <el-form label-width="100px" style="max-width: 480px">
            <el-form-item label="登录账号">
              <el-input :model-value="profile.phone" disabled />
            </el-form-item>
            <el-form-item label="角色">
              <el-tag type="warning">{{ roleLabels[profile.admin_role] || '管理员' }}</el-tag>
            </el-form-item>
            <el-form-item label="昵称">
              <el-input v-model="profile.nickname" placeholder="请输入昵称" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" :loading="saving" @click="saveProfile">保存资料</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <el-col :xs="24" :lg="12">
        <el-card shadow="never" header="修改密码">
          <el-form label-width="100px" style="max-width: 480px" @submit.prevent="changePassword">
            <el-form-item label="原密码">
              <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入原密码" />
            </el-form-item>
            <el-form-item label="新密码">
              <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="请输入新密码" />
            </el-form-item>
            <el-form-item label="确认密码">
              <el-input v-model="passwordForm.confirm" type="password" show-password placeholder="再次输入新密码" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" native-type="submit" :loading="passwordSaving">修改密码</el-button>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>
