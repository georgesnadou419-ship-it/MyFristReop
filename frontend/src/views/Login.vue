<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()

const form = reactive({
  username: '',
  password: '',
})

const rules: FormRules<typeof form> = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

const handleLogin = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }

  await authStore.login(form)
  ElMessage.success('登录成功')
  const redirect = (route.query.redirect as string) || '/'
  await router.push(redirect)
}
</script>

<template>
  <div class="login-page">
    <div class="login-page__hero">
      <div class="login-page__copy">
        <div class="login-page__eyebrow">SUIT API</div>
        <h1>统一纳管校内 GPU 资源，面向任务与模型双场景调度。</h1>
        <p>
          前端控制台聚合节点状态、任务提交、调度结果和运行日志，作为管控节点的唯一操作入口。
        </p>
      </div>
    </div>

    <div class="login-card glass-card">
      <div class="login-card__header">
        <span class="login-card__kicker">Control Console</span>
        <h2>登录控制台</h2>
        <p>输入管理员或普通用户账号，进入算力调度台。</p>
      </div>

      <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
        <el-form-item label="用户名" prop="username">
          <el-input v-model="form.username" placeholder="请输入用户名" :prefix-icon="User" />
        </el-form-item>
        <el-form-item label="密码" prop="password">
          <el-input
            v-model="form.password"
            type="password"
            show-password
            placeholder="请输入密码"
            :prefix-icon="Lock"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-button
          class="login-card__submit"
          type="primary"
          :loading="authStore.loading"
          @click="handleLogin"
        >
          登录
        </el-button>
      </el-form>
    </div>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: grid;
  grid-template-columns: 1.2fr minmax(420px, 480px);
  background:
    radial-gradient(circle at left top, rgba(20, 184, 166, 0.18), transparent 32%),
    linear-gradient(120deg, #e7f3ef 0%, #eff4fb 55%, #f7fafc 100%);
}

.login-page__hero {
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 48px;
}

.login-page__copy {
  max-width: 560px;
}

.login-page__eyebrow {
  color: #0f766e;
  text-transform: uppercase;
  letter-spacing: 0.18em;
  font-size: 13px;
  font-weight: 700;
}

.login-page__copy h1 {
  margin: 20px 0 16px;
  font-size: 52px;
  line-height: 1.08;
}

.login-page__copy p {
  margin: 0;
  font-size: 18px;
  color: #475569;
}

.login-card {
  margin: auto 40px auto 0;
  padding: 36px 32px;
  border-radius: 30px;
}

.login-card__header {
  margin-bottom: 24px;
}

.login-card__kicker {
  color: #0f766e;
  font-size: 13px;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.14em;
}

.login-card__header h2 {
  margin: 12px 0 8px;
  font-size: 32px;
}

.login-card__header p {
  margin: 0;
  color: #64748b;
}

.login-card__submit {
  width: 100%;
  margin-top: 8px;
  height: 46px;
}
</style>
