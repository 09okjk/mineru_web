import { defineConfig } from 'vite';
import vue from '@vitejs/plugin-vue';

export default defineConfig({
  plugins: [vue()],
  server: {
    host: '0.0.0.0',
    proxy: {
      // 将所有 API 请求代理到后端
      '/upload': 'http://localhost:8600',
      '/list_uploaded_files': 'http://localhost:8600',
      '/delete_uploaded_file': 'http://localhost:8600',
      '/download_uploaded_file': 'http://localhost:8600',
      '/download_uploaded_files': 'http://localhost:8600',
      '/list_md_files': 'http://localhost:8600',
      '/preview_md_file': 'http://localhost:8600',
      '/delete_md_file': 'http://localhost:8600',
      '/batch_delete_md_files': 'http://localhost:8600',
      '/download_md_file': 'http://localhost:8600',
      '/download_md_files_only': 'http://localhost:8600',
      '/download_selected': 'http://localhost:8600',
      '/parse_async': 'http://localhost:8600',
      '/progress': 'http://localhost:8600'
    }
  }
});
