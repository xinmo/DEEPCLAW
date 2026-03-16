import axios from 'axios';

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json',
  },
  timeout: 30000,
});

export type PromptInfo = {
  id: string;
  name: string;
  description: string;
};

export type PromptDetail = {
  id: string;
  name: string;
  description: string;
  content: string;
  default_content: string;
  variables: string[];
};

export type PromptUpdateResponse = {
  success: boolean;
  message: string;
};

export type PromptResetResponse = {
  success: boolean;
  content: string;
};

export const promptApi = {
  getPrompts: async (): Promise<{ prompts: PromptInfo[] }> => {
    const response = await apiClient.get('/claw/prompts');
    return response.data;
  },

  getPromptDetail: async (id: string): Promise<PromptDetail> => {
    const response = await apiClient.get(`/claw/prompts/${id}`);
    return response.data;
  },

  updatePrompt: async (
    id: string,
    content: string,
  ): Promise<PromptUpdateResponse> => {
    const response = await apiClient.put(`/claw/prompts/${id}`, { content });
    return response.data;
  },

  resetPrompt: async (id: string): Promise<PromptResetResponse> => {
    const response = await apiClient.post(`/claw/prompts/${id}/reset`);
    return response.data;
  },
};
