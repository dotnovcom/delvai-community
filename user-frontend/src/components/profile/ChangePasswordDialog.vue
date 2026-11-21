<script setup lang="ts">
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { post } from '../../utils/request'

const visible = ref(false)
const saving = ref(false)
const form = ref({ old_password: '', new_password: '', confirm: '' })

function open() {
  form.value = { old_password: '', new_password: '', confirm: '' }
  visible.value = true
}

async function submit() {
  if (form.value.new_password !== form.value.confirm) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  saving.value = true
  try {
    await post('/api/v1/auth/change-password', {
      old_password: form.value.old_password,
      new_password: form.value.new_password,
    })
    ElMessage.success('密码已修改')
    visible.value = false
  } finally {
    saving.value = false
  }
}

defineExpose({ open })
</script>

<template>
  <el-dialog v-model="visible" title="修改登录密码" width="440px" destroy-on-close>
    <el-form label-width="88px">
      <el-form-item label="原密码">
        <el-input v-model="form.old_password" type="password" show-password autocomplete="current-password" />
      </el-form-item>
      <el-form-item label="新密码">
        <el-input v-model="form.new_password" type="password" show-password autocomplete="new-password" />
      </el-form-item>
      <el-form-item label="确认密码">
        <el-input v-model="form.confirm" type="password" show-password autocomplete="new-password" />
      </el-form-item>
    </el-form>
    <template #footer>
      <el-button @click="visible = false">取消</el-button>
      <el-button type="primary" :loading="saving" @click="submit">确认修改</el-button>
    </template>
  </el-dialog>
</template>
