<template>
  <el-container style="min-height:100vh;">
    <el-header style="font-size: 24px; font-weight: bold; text-align:center; background:#f5f7fa;">MinerU PDF 批量解析工具</el-header>
    <el-main>
      <el-row :gutter="24">
        <!-- 左侧：已上传文件 -->
        <el-col :span="8">
          <el-card shadow="hover" style="margin-bottom: 24px;">
            <div style="font-weight:bold; font-size:18px; margin-bottom:10px;">已上传文件</div>
            <el-upload
              class="upload-demo"
              drag
              multiple
              :action="''"
              :before-upload="handleBeforeUpload"
              :http-request="dummyRequest"
              :file-list="fileList"
              :auto-upload="false"
              :on-remove="handleRemove"
              :on-change="handleChange"
              style="margin-bottom:10px;"
            >
              <i class="el-icon-upload"></i>
              <div class="el-upload__text">拖拽或 <em>点击上传</em> PDF 文件</div>
            </el-upload>
            <el-button type="primary" @click="uploadFiles" :loading="uploading" style="margin-bottom:10px;">上传文件</el-button>
            <el-table :data="uploadedList" @selection-change="handleUploadedSelection" ref="uploadedTable" size="small" style="width:100%;margin-top:10px;">
              <el-table-column type="selection" width="45" />
              <el-table-column prop="name" label="文件名" />
              <el-table-column prop="size" label="大小" width="80">
                <template #default="scope">{{ (scope.row.size/1024).toFixed(1) }} KB</template>
              </el-table-column>
              <el-table-column label="操作" width="180">
                <template #default="scope">
                  <el-button size="small" text type="primary" @click="downloadUploaded(scope.row)">下载</el-button>
                  <el-button size="small" text type="warning" @click="parseUploaded(scope.row)">解析</el-button>
                  <el-button size="small" text type="danger" @click="deleteUploaded(scope.row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div style="margin-top:10px;">
              <el-button size="small" type="success" :disabled="selectedUploaded.length===0" @click="batchDownloadUploaded">批量下载</el-button>
              <el-button size="small" type="danger" :disabled="selectedUploaded.length===0" @click="batchDeleteUploaded" style="margin-left:8px;">批量删除</el-button>
              <el-button size="small" type="primary" :disabled="selectedUploaded.length===0" @click="batchParseUploaded" style="margin-left:8px;">批量解析</el-button>
            </div>
          </el-card>
        </el-col>
        <!-- 右侧：已解析文件 -->
        <el-col :span="16">
          <el-card shadow="hover">
            <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:10px;">
              <div style="font-weight:bold; font-size:18px;">已解析 Markdown 文件</div>
              <el-button size="small" type="primary" icon="el-icon-refresh" circle @click="refreshMdList" :loading="refreshing" title="刷新列表"></el-button>
            </div>
            <el-table :data="mdList" @selection-change="handleMdSelection" ref="mdTable" size="small" style="width:100%;">
              <el-table-column type="selection" width="45" />
              <el-table-column prop="name" label="文件名" width="220" />
              <el-table-column prop="path" label="相对路径" />
              <el-table-column prop="size" label="大小" width="80">
                <template #default="scope">{{ (scope.row.size/1024).toFixed(1) }} KB</template>
              </el-table-column>
              <el-table-column label="操作" width="180">
                <template #default="scope">
                  <el-button size="small" text type="primary" @click="previewMd(scope.row)">预览</el-button>
                  <el-button size="small" text type="success" @click="downloadMd(scope.row)">下载</el-button>
                  <el-button size="small" text type="danger" @click="deleteMd(scope.row)">删除</el-button>
                </template>
              </el-table-column>
            </el-table>
            <div style="margin-top:18px;">
              <el-button type="success" :disabled="selectedMd.length===0" @click="batchDownloadMd">批量下载完整内容</el-button>
              <el-button type="primary" :disabled="selectedMd.length===0" @click="batchDownloadMdOnly" style="margin-left:8px;">只下载MD文件</el-button>
              <el-button type="danger" :disabled="selectedMd.length===0" @click="batchDeleteMd" style="margin-left:8px;">批量删除所选</el-button>
            </div>
          </el-card>
        </el-col>
      </el-row>
      <!-- 预览弹窗 -->
      <el-dialog v-model="showPreview" width="60%" title="Markdown 预览" :destroy-on-close="true">
        <pre style="background:#f6f8fa;max-height:60vh;overflow:auto;white-space:pre-wrap;">{{ previewContent }}</pre>
      </el-dialog>
    </el-main>
  </el-container>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import axios from 'axios'
import { ElMessage, ElMessageBox } from 'element-plus';

// 使用 Vite 代理转发请求到后端，不需要设置 baseURL

const fileList = ref([]); // el-upload组件文件列表
const uploading = ref(false);
const deleting = ref(false);
const parsing = ref(false);
const refreshing = ref(false);
const uploadedList = ref([]); // 已上传pdf文件
const mdList = ref([]); // 已解析md文件
const selectedMd = ref([]);
const selectedUploaded = ref([]);
const showPreview = ref(false);
const previewContent = ref('');
const mdTable = ref(null);
const uploadedTable = ref(null);
const backend = window.location.origin.replace(/:\d+$/, ':8600');

// 获取已上传pdf文件
async function fetchUploaded() {
  const res = await axios.get('/list_uploaded_files')
  uploadedList.value = res.data.files || []
}
// 获取md文件
async function fetchMdList() {
  const res = await axios.get('/list_md_files')
  mdList.value = res.data.files || []
}

// 刷新 Markdown 文件列表
async function refreshMdList() {
  refreshing.value = true;
  try {
    await fetchMdList();
    ElMessage.success('列表刷新成功');
  } catch (e) {
    ElMessage.error('刷新失败：' + (e?.message || e));
  } finally {
    refreshing.value = false;
  }
}

onMounted(() => {
  fetchUploaded();
  fetchMdList();
})

function handleBeforeUpload(file) {
  return false;
}
function dummyRequest() {}
function handleRemove(file, fileListNew) {
  fileList.value = fileListNew;
}
function handleChange(file, fileListNew) {
  fileList.value = fileListNew;
}
// 上传文件
async function uploadFiles() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请选择PDF文件');
    return;
  }
  uploading.value = true;
  try {
    const formData = new FormData();
    fileList.value.forEach(f => formData.append('files', f.raw));
    await axios.post('/upload', formData, {headers: {'Content-Type': 'multipart/form-data'}});
    ElMessage.success('上传成功');
    fileList.value = [];
    fetchUploaded();
  } catch {
    ElMessage.error('上传失败');
  }
  uploading.value = false;
}
// 下载上传文件
async function downloadUploaded(row) {
  const res = await axios.get('/download_uploaded_file', {params:{filename:row.name}, responseType:'blob'});
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', row.name);
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
// 批量下载上传文件
async function batchDownloadUploaded() {
  if (selectedUploaded.value.length === 0) return;
  const filenames = selectedUploaded.value.map(f => f.name);
  const res = await axios.post('/download_uploaded_files', filenames, {responseType:'blob'});
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', 'uploaded_files.zip');
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
// 删除上传文件
async function deleteUploaded(row) {
  await ElMessageBox.confirm(`确定要删除文件 ${row.name} 吗？`, '删除确认', {type:'warning'});
  deleting.value = true;
  try {
    const res = await axios.post('/delete_uploaded_file', {filenames: [row.name]});
    const r = res.data.results && res.data.results[0];
    if (r && r.success) {
      ElMessage.success('删除成功');
    } else {
      ElMessage.error(r && r.error ? `删除失败：${r.error}` : '删除失败');
    }
  } catch (e) {
    ElMessage.error('删除请求异常：' + (e?.message || e));
  } finally {
    deleting.value = false;
    fetchUploaded();
  }
}
// 批量删除上传文件
async function batchDeleteUploaded() {
  if (selectedUploaded.value.length === 0) return;
  await ElMessageBox.confirm(`确定要批量删除选中的 ${selectedUploaded.value.length} 个文件吗？`, '批量删除确认', {type:'warning'});
  deleting.value = true;
  try {
    const filenames = selectedUploaded.value.map(f => f.name);
    const res = await axios.post('/delete_uploaded_file', {filenames});
    const results = res.data.results || [];
    let failed = results.filter(r => !r.success);
    if (failed.length === 0) {
      ElMessage.success('批量删除成功');
    } else {
      ElMessage.error('部分文件删除失败：' + failed.map(r => `${r.filename}: ${r.error}`).join('; '));
    }
  } catch (e) {
    ElMessage.error('批量删除请求异常：' + (e?.message || e));
  } finally {
    deleting.value = false;
    fetchUploaded();
    selectedUploaded.value = [];
  }
}
// md选择
function handleMdSelection(val) {
  selectedMd.value = val;
}
// 上传文件选择
function handleUploadedSelection(val) {
  selectedUploaded.value = val;
}
// 预览md
async function previewMd(row) {
  const res = await axios.get('/preview_md_file', {params:{md_path:row.path}});
  previewContent.value = res.data.content;
  showPreview.value = true;
}
// 下载md（zip）
async function downloadMd(row) {
  const res = await axios.get('/download_md_file', {params:{md_path:row.path}, responseType:'blob'});
  const url = window.URL.createObjectURL(new Blob([res.data]));
  const link = document.createElement('a');
  link.href = url;
  link.setAttribute('download', row.name.replace(/\.md$/, '.zip'));
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}
// 删除md及目录
async function deleteMd(row) {
  await ElMessageBox.confirm(`确定要删除 ${row.name} 及其相关内容吗？`, '删除确认', {type:'warning'});
  deleting.value = true;
  try {
    await axios.post('/delete_md_file', {md_path: row.path});
    ElMessage.success('删除成功');
  } catch (e) {
    ElMessage.error('删除失败：' + (e?.message || e));
  } finally {
    deleting.value = false;
    fetchMdList();
  }
}
// 批量下载md及其完整内容
async function batchDownloadMd() {
  if (selectedMd.value.length === 0) return;
  try {
    const filenames = selectedMd.value.map(f => f.path);
    // 使用 body 而非 params
    const res = await axios.post('/download_selected', {filenames}, {responseType:'blob'});
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'selected_files.zip');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    ElMessage.success('批量下载完整内容成功');
  } catch (e) {
    ElMessage.error('批量下载失败：' + (e?.message || e));
  }
}

// 只批量下载md文件
async function batchDownloadMdOnly() {
  if (selectedMd.value.length === 0) return;
  try {
    const filenames = selectedMd.value.map(f => f.path);
    const res = await axios.post('/download_md_files_only', {filenames}, {responseType:'blob'});
    const url = window.URL.createObjectURL(new Blob([res.data]));
    const link = document.createElement('a');
    link.href = url;
    link.setAttribute('download', 'markdown_files.zip');
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
    ElMessage.success('只下载MD文件成功');
  } catch (e) {
    ElMessage.error('批量下载MD文件失败：' + (e?.message || e));
  }
}

// 批量删除md文件
async function batchDeleteMd() {
  if (selectedMd.value.length === 0) return;
  await ElMessageBox.confirm(`确定要批量删除选中的 ${selectedMd.value.length} 个文件及其目录吗？`, '批量删除确认', {type:'warning'});
  deleting.value = true;
  try {
    const md_paths = selectedMd.value.map(f => f.path);
    const res = await axios.post('/batch_delete_md_files', {md_paths});
    const results = res.data.results || [];
    let failed = results.filter(r => !r.success);
    if (failed.length === 0) {
      ElMessage.success('批量删除成功');
    } else {
      ElMessage.error('部分文件删除失败：' + failed.map(r => `${r.path}: ${r.error}`).join('; '));
    }
  } catch (e) {
    ElMessage.error('批量删除请求异常：' + (e?.message || e));
  } finally {
    deleting.value = false;
    fetchMdList();
    selectedMd.value = [];
  }
}
// 解析上传文件
async function parseUploaded(row) {
  parsing.value = true;
  try {
    const res = await axios.post('/parse_async', {filenames: [row.name]});
    if (res.data.task_id) {
      let msg = `已提交解析任务，task_id: ${res.data.task_id}`;
      if (res.data.errors && res.data.errors.length > 0) {
        msg += '，部分文件未能提交：' + res.data.errors.map(e => `${e.filename}: ${e.error}`).join('; ');
      }
      ElMessage.success(msg);
    } else {
      ElMessage.error((res.data.details && res.data.details.map(e => `${e.filename}: ${e.error}`).join('; ')) || res.data.error || '解析提交失败');
    }
  } catch (e) {
    ElMessage.error('解析请求异常：' + (e?.message || e));
  } finally {
    parsing.value = false;
    fetchMdList();
  }
}
// 批量解析上传文件
async function batchParseUploaded() {
  if (selectedUploaded.value.length === 0) return;
  parsing.value = true;
  try {
    const filenames = selectedUploaded.value.map(f => f.name);
    const res = await axios.post('/parse_async', {filenames});
    if (res.data.task_id) {
      let msg = `已提交解析任务，task_id: ${res.data.task_id}`;
      if (res.data.errors && res.data.errors.length > 0) {
        msg += '，部分文件未能提交：' + res.data.errors.map(e => `${e.filename}: ${e.error}`).join('; ');
      }
      ElMessage.success(msg);
    } else {
      ElMessage.error((res.data.details && res.data.details.map(e => `${e.filename}: ${e.error}`).join('; ')) || res.data.error || '解析提交失败');
    }
  } catch (e) {
    ElMessage.error('批量解析请求异常：' + (e?.message || e));
  } finally {
    parsing.value = false;
    fetchMdList();
  }
}
</script>

<style scoped>
.upload-demo {
  width: 100%;
  margin-bottom: 18px;
}
.el-card {
  border-radius: 10px;
}
</style>