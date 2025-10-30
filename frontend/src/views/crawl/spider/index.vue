<template>
  <div class="app-container">
    <!-- 查询条件 -->
    <el-form :model="queryParams" ref="queryRef" :inline="true" v-show="showSearch" label-width="80px">
      <el-form-item label="id" prop="id">
        <el-input v-model="queryParams.id" placeholder="请输入id" clearable style="width: 200px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="网站名称" prop="siteName">
        <el-input v-model="queryParams.siteName" placeholder="请输入网站名称" clearable style="width: 200px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="栏目名称" prop="columnName">
        <el-input v-model="queryParams.columnName" placeholder="请输入栏目名称" clearable style="width: 200px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="主域名" prop="domain">
        <el-input v-model="queryParams.domain" placeholder="请输入主域名" clearable style="width: 200px" @keyup.enter="handleQuery" />
      </el-form-item>
      <el-form-item label="状态" prop="status">
        <el-select v-model="queryParams.status" placeholder="请选择状态" clearable style="width: 160px">
          <el-option label="运行" value="running" />
          <el-option label="停止" value="stopped" />
        </el-select>
      </el-form-item>
      <el-form-item label="修改时间" prop="dateRange">
        <el-date-picker v-model="dateRange" type="daterange" range-separator="-" start-placeholder="开始日期" end-placeholder="结束日期" value-format="YYYY-MM-DD" style="width: 300px" />
      </el-form-item>
      <el-form-item>
        <el-button type="primary" icon="Search" @click="handleQuery">搜索</el-button>
        <el-button icon="Refresh" @click="resetQuery">重置</el-button>
      </el-form-item>
    </el-form>

    <!-- 工具栏 -->
    <el-row :gutter="10" class="mb8">
      <el-col :span="1.5">
        <el-button type="primary" plain icon="Plus" @click="handleAdd">新增任务</el-button>
      </el-col>
      <right-toolbar v-model:showSearch="showSearch" @queryTable="getList" />
    </el-row>

    <!-- 列表 -->
    <el-table v-loading="loading" :data="spiderList" @selection-change="handleSelectionChange">
      <el-table-column type="selection" width="55" align="center" />
      <el-table-column label="id" width="100" align="center" prop="id" />
      <el-table-column label="任务名称" align="center" :show-overflow-tooltip="true">
        <template #default="scope">
          <el-button 
            link 
            type="primary" 
            @click="handleDetail(scope.row)"
            class="task-name-link"
          >
            {{ (scope.row.siteName || scope.row.taskName || '') + '_' + (scope.row.columnName || '') }}
          </el-button>
        </template>
      </el-table-column>
      <el-table-column label="主域名" align="center" :show-overflow-tooltip="true">
        <template #default="scope">
          <a
            :href="((scope.row.domain || scope.row.mainHost || '').startsWith('http') ? (scope.row.domain || scope.row.mainHost) : 'https://' + (scope.row.domain || scope.row.mainHost || ''))"
            target="_blank"
            rel="noopener noreferrer"
          >
            {{ scope.row.mainHost || scope.row.domain || '-' }}
          </a>
        </template>
      </el-table-column>
      <el-table-column label="最后修改时间" width="170" align="center" prop="updatedAt" />
      <el-table-column label="采集开始时间" width="170" align="center" prop="crawlStartAt" />
      <el-table-column label="状态" width="100" align="center" prop="status">
        <template #default="scope">
          <el-tag :type="scope.row.status === 'running' ? 'success' : 'danger'">{{ scope.row.status === 'running' ? '运行' : '停止' }}</el-tag>
        </template>
      </el-table-column>
      
      <el-table-column label="操作" align="center" width="220" class-name="small-padding fixed-width">
        <template #default="scope">
          <el-tooltip content="编辑" placement="top">
            <el-button link type="primary" icon="Edit" @click="handleUpdate(scope.row)"></el-button>
          </el-tooltip>
          <el-tooltip content="查看" placement="top">
            <el-button link type="primary" icon="View" @click="handleView(scope.row)"></el-button>
          </el-tooltip>
          <el-tooltip content="复制" placement="top">
            <el-button link type="primary" icon="CopyDocument" @click="handleCopy(scope.row)"></el-button>
          </el-tooltip>
          <el-tooltip :content="scope.row.status === 'running' ? '停止' : '启动'" placement="top">
            <el-button link :type="scope.row.status === 'running' ? 'danger' : 'success'" :icon="scope.row.status === 'running' ? 'Close' : 'VideoPlay'" @click="toggleStatus(scope.row)"></el-button>
          </el-tooltip>
        </template>
      </el-table-column>
    </el-table>

    <pagination v-show="total > 0" :total="total" v-model:page="queryParams.pageNum" v-model:limit="queryParams.pageSize" @pagination="getList" />

    <!-- 新增/编辑 -->
    <el-dialog :title="title" v-model="open" width="600px" append-to-body>
      <el-form :model="form" ref="spiderRef" label-width="90px">
        <el-form-item label="网站名称" prop="siteName">
          <el-input v-model="form.siteName" placeholder="请输入网站名称" />
        </el-form-item>
        <el-form-item label="栏目名称" prop="columnName">
          <el-input v-model="form.columnName" placeholder="请输入栏目名称" />
        </el-form-item>
        <el-form-item label="主域名" prop="domain">
          <el-input v-model="form.domain" placeholder="例如：www.example.com" />
        </el-form-item>
      </el-form>
      <template #footer>
        <div class="dialog-footer">
          <el-button @click="open=false">取 消</el-button>
          <el-button type="primary" @click="submitForm">确 定</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
  
</template>

<script setup name="SpiderTask">
import { listSpider, addSpider, updateSpider, startSpider, stopSpider, delSpider } from '@/api/crawl/spider'

const { proxy } = getCurrentInstance();

const spiderList = ref([]);
const loading = ref(true);
const showSearch = ref(true);
const ids = ref([]);
const single = ref(true);
const multiple = ref(true);
const total = ref(0);
const dateRange = ref([]);

const data = reactive({
  form: {},
  queryParams: {
    pageNum: 1,
    pageSize: 10,
    id: undefined,
    siteName: undefined,
    columnName: undefined,
    domain: undefined,
    status: undefined
  }
});

const { queryParams, form } = toRefs(data);

function mockRows(pageNum, pageSize) {
  const baseId = (pageNum - 1) * pageSize + 160000;
  return Array.from({ length: pageSize }).map((_, i) => {
    const id = baseId + i + 1;
    const running = i % 3 !== 2;
    return {
      id,
      siteName: i % 2 ? '国家政务服务平台' : '示例网站',
      taskName: i % 2 ? '国家政务服务平台' : '示例网站',
      columnName: i % 2 ? '最新公告' : '新闻中心',
      mainHost: i % 2 ? 'www.gov.cn' : 'www.example.com',
      updatedAt: '2025-10-13',
      crawlStartAt: '2025-10-13 11:50:44',
      status: running ? 'running' : 'stopped'
    }
  })
}

/** 查询列表 */
function getList() {
  loading.value = true;
  listSpider(proxy.addDateRange(queryParams.value, dateRange.value)).then(response => {
    // 期望后端返回 { rows: [], total: 0 }
    spiderList.value = response?.rows || [];
    total.value = response?.total || 0;
    loading.value = false;
  }).catch(() => {
    // 无后端时使用模拟数据以便预览
    const rows = mockRows(queryParams.value.pageNum, queryParams.value.pageSize);
    spiderList.value = rows;
    total.value = 53289;
    loading.value = false;
  });
}

/** 搜索按钮 */
function handleQuery() {
  queryParams.value.pageNum = 1;
  getList();
}

/** 重置按钮 */
function resetQuery() {
  dateRange.value = [];
  proxy.resetForm('queryRef');
  queryParams.value.pageNum = 1;
  getList();
}

// 多选框选中数据
function handleSelectionChange(selection) {
  ids.value = selection.map(item => item.id);
  single.value = selection.length != 1;
  multiple.value = !selection.length;
}

function handleAdd() {
  form.value = { siteName: '', columnName: '', domain: '' };
  title.value = '添加任务';
  open.value = true;
}

function handleUpdate(row) {
  form.value = { ...row };
  form.value.siteName = form.value.siteName || form.value.taskName || '';
  title.value = '编辑任务';
  open.value = true;
}

function handleView(row) {
  const name = `${row.siteName || row.taskName || ''}_${row.columnName || ''}`;
  proxy.$modal.msg(`查看任务：${name}`);
}

function handleDetail(row) {
  // 跳转到详情配置页面
  proxy.$router.push(`/crawl/spider/detail/${row.id}`);
}

function handleCopy(row) {
  const name = `${row.siteName || row.taskName || ''}_${row.columnName || ''}`;
  const host = row.mainHost || row.domain || '';
  const text = `${name} - ${host}`;
  if (navigator.clipboard) {
    navigator.clipboard.writeText(text).then(() => proxy.$modal.msgSuccess('复制成功'))
      .catch(() => proxy.$modal.msgWarning('复制失败'))
  } else {
    proxy.$modal.msg(text);
  }
}

function toggleStatus(row) {
  const isRunning = row.status === 'running';
  const api = isRunning ? stopSpider : startSpider;
  api(row.id).finally(() => {
    row.status = isRunning ? 'stopped' : 'running';
    proxy.$modal.msgSuccess(isRunning ? '已停止' : '已启动');
  });
}

const open = ref(false);
const title = ref('');

function submitForm() {
  if (!form.value.siteName || !form.value.columnName) {
    proxy.$modal.msgWarning('请填写网站名称与栏目名称');
    return;
  }
  const isEdit = !!form.value.id;
  const api = isEdit ? updateSpider : addSpider;
  api(form.value).finally(() => {
    proxy.$modal.msgSuccess(isEdit ? '修改成功' : '新增成功');
    open.value = false;
    getList();
  });
}

getList();
</script>

<style scoped>
.mb8 { margin-bottom: 8px; }

.task-name-link {
  font-weight: 500;
  text-decoration: none;
}

.task-name-link:hover {
  text-decoration: underline;
}
</style>