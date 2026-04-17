import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000',
});

export const uploadFile = async (file: File) => {
  const formData = new FormData();
  formData.append('file', file);
  const response = await api.post('/api/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  });
  return response.data;
};

export const getDatasetSummary = async (datasetId: string) => {
  const response = await api.get(`/api/dataset/${datasetId}/summary`);
  return response.data;
};

export const sendChatMessage = async (datasetId: string, message: string) => {
  const response = await api.post('/api/chat', { dataset_id: datasetId, message });
  return response.data;
};

export const checkHealth = async () => {
    const response = await api.get('/api/health');
    return response.data;
}

export default api;
