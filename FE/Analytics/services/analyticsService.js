
import apiClient from './api'; // Assuming you have a configured axios instance

export const getStorageAnalytics = async () => {
  try {
    const response = await apiClient.get('/storage/api/storage/analytics/');
    return response.data;
  } catch (error) {
    console.error("Error fetching storage analytics:", error.response?.data || error.message);
    throw error;
  }
};