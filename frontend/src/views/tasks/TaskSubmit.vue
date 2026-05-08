<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance, type FormRules } from 'element-plus'
import { useTasksStore } from '../../stores/tasks'

const router = useRouter()
const tasksStore = useTasksStore()
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  name: '',
  task_type: 'custom',
  container_image: 'python:3.11-slim',
  container_command: '',
  gpu_count: 0,
  gpu_model: '',
  min_memory_gb: undefined as number | undefined,
  priority: 1,
})

const rules: FormRules<typeof form> = {
  name: [{ required: true, message: '请输入任务名称', trigger: 'blur' }],
  task_type: [{ required: true, message: '请选择任务类型', trigger: 'change' }],
  container_image: [{ required: true, message: '请输入容器镜像', trigger: 'blur' }],
  container_command: [{ required: true, message: '请输入执行命令', trigger: 'blur' }],
}

const handleSubmit = async () => {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) {
    return
  }

  submitting.value = true
  try {
    const task = await tasksStore.createTask({
      name: form.name,
      task_type: form.task_type,
      container_image: form.container_image,
      container_command: form.container_command,
      priority: form.priority,
      gpu_count: form.gpu_count,
      gpu_model: form.gpu_model || null,
      min_memory_mb: form.min_memory_gb ? form.min_memory_gb * 1024 : null,
      config_json: {
        gpu_count: form.gpu_count,
        gpu_model: form.gpu_model || null,
        min_memory_mb: form.min_memory_gb ? form.min_memory_gb * 1024 : null,
      },
    })
    await tasksStore.submitTask(task.id)
    ElMessage.success('任务已创建并提交到队列')
    await router.push('/tasks')
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="page-shell">
    <div class="page-header">
      <div>
        <h2 class="page-title">提交任务</h2>
        <p class="page-subtitle">创建任务记录后立即提交到调度队列。</p>
      </div>
    </div>

    <section class="section-card glass-card">
      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        label-position="top"
        class="submit-form"
      >
        <el-row :gutter="20">
          <el-col :span="12">
            <el-form-item label="任务名称" prop="name">
              <el-input v-model="form.name" placeholder="例如：ResNet50 训练任务" />
            </el-form-item>
          </el-col>
          <el-col :span="12">
            <el-form-item label="任务类型" prop="task_type">
              <el-select v-model="form.task_type">
                <el-option label="训练" value="train" />
                <el-option label="推理" value="inference" />
                <el-option label="自定义" value="custom" />
              </el-select>
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="容器镜像" prop="container_image">
          <el-input v-model="form.container_image" placeholder="pytorch/pytorch:2.0-cuda11.8" />
        </el-form-item>

        <el-form-item label="执行命令" prop="container_command">
          <el-input
            v-model="form.container_command"
            type="textarea"
            :rows="6"
            placeholder="python train.py --epochs 10"
          />
        </el-form-item>

        <el-row :gutter="20">
          <el-col :span="8">
            <el-form-item label="GPU 数量">
              <el-input-number v-model="form.gpu_count" :min="0" :max="8" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="GPU 型号">
              <el-input v-model="form.gpu_model" placeholder="不限 / RTX3090" />
            </el-form-item>
          </el-col>
          <el-col :span="8">
            <el-form-item label="最低显存 (GB)">
              <el-input-number v-model="form.min_memory_gb" :min="0" :max="80" />
            </el-form-item>
          </el-col>
        </el-row>

        <el-form-item label="优先级">
          <el-radio-group v-model="form.priority">
            <el-radio :label="2">高</el-radio>
            <el-radio :label="1">普通</el-radio>
            <el-radio :label="0">低</el-radio>
          </el-radio-group>
        </el-form-item>

        <div class="submit-actions">
          <el-button @click="router.push('/tasks')">取消</el-button>
          <el-button type="primary" :loading="submitting" @click="handleSubmit">
            提交任务
          </el-button>
        </div>
      </el-form>
    </section>
  </div>
</template>

<style scoped>
.submit-form {
  max-width: 980px;
}

.submit-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 8px;
}
</style>
