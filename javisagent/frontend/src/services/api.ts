import axios from 'axios';

const API_BASE_URL = '/api';

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: any) => {
    console.error('API Error:', error);
    if (error.response) {
      console.error('Response Data:', error.response.data);
      console.error('Response Status:', error.response.status);
    } else if (error.request) {
      console.error('Request:', error.request);
    } else {
      console.error('Error:', error.message);
    }
    return Promise.reject(error);
  }
);

interface Task {
  id: string;
  name: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  createdAt: string;
}

interface UploadResponse {
  file_id: string;
  file_name: string;
}

interface ParseResponse {
  task_id: string;
}

interface ExtractProgress {
  extracted_pages: number;
  total_pages: number;
}

interface TaskStatusResponse {
  task: Task;
  result?: string;
  progress?: ExtractProgress;
}

const api = {
  // 文件上传
  uploadFile: async (file: File): Promise<UploadResponse> => {
    const formData = new FormData();
    formData.append('file', file);
    const response = await apiClient.post<UploadResponse>('/document/upload', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  },

  // 解析文档
  parseDocument: async (fileId: string): Promise<ParseResponse> => {
    const requestBody = { file_id: fileId };
    console.log('Sending parse request:', requestBody);
    const response = await apiClient.post<ParseResponse>('/document/parse', requestBody);
    return response.data;
  },

  // 解析网页链接
  parseUrl: async (url: string): Promise<ParseResponse> => {
    const response = await apiClient.post<ParseResponse>('/document/parse', {
      url,
    });
    return response.data;
  },

  // 获取任务状态
  getTaskStatus: async (taskId: string): Promise<TaskStatusResponse> => {
    const response = await apiClient.get<TaskStatusResponse>(`/document/task/${taskId}`);
    return response.data;
  },

  // 获取任务列表
  getTasks: async (): Promise<Task[]> => {
    const response = await apiClient.get<Task[]>('/document/tasks');
    return response.data;
  },

  // 创建新任务
  createTask: async (): Promise<Task> => {
    const response = await apiClient.post<Task>('/document/tasks');
    return response.data;
  },
};

export default api;
