<template>
  <section class="page-stack">
    <div class="page-lead">
      <div>
        <h2>批量测试中心</h2>
        <p>
          用表格统一查看批量任务状态、进度和模型归属，并支持导出当前数据为 CSV。
        </p>
      </div>
      <div class="batch-actions">
        <el-button @click="store.reseedTasks()">刷新示例任务</el-button>
        <el-button type="primary" @click="handleExport">导出测试报告</el-button>
      </div>
    </div>

    <el-card class="panel cyber-glow" shadow="never">
      <el-table :data="store.tasks" stripe class="batch-table">
        <el-table-column prop="fileName" label="文件名" min-width="220" />
        <el-table-column prop="modelName" label="模型" min-width="120" />
        <el-table-column label="状态" min-width="120">
          <template #default="{ row }">
            <el-tag :type="tagType(row.status)" round>{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="进度" min-width="220">
          <template #default="{ row }">
            <el-progress
              :percentage="row.progress"
              :status="row.status === 'error' ? 'exception' : row.progress === 100 ? 'success' : ''"
            />
          </template>
        </el-table-column>
        <el-table-column prop="rtf" label="RTF" min-width="100">
          <template #default="{ row }">
            <span class="numeric">{{ row.rtf }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="duration" label="总时长" min-width="100">
          <template #default="{ row }">
            <span class="numeric">{{ row.duration }}</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </section>
</template>

<script setup lang="ts">
import { ElMessage } from "element-plus";

import { useBatchStore } from "../store/batch";
import { exportBatchTasks } from "../utils/exportReport";

const store = useBatchStore();

const tagType = (status: string) => {
  if (status === "finished") return "success";
  if (status === "running") return "warning";
  if (status === "error") return "danger";
  return "info";
};

const handleExport = () => {
  exportBatchTasks(store.tasks);
  ElMessage.success("批量测试报告已导出");
};
</script>

<style scoped>
.batch-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

.batch-table :deep(.cell) {
  color: #dce7f4;
}
</style>
