// services/apiService.js - API service for document management
import AsyncStorage from '@react-native-async-storage/async-storage';

const BASE_URL = 'http://your-django-server.com'; // Replace with your actual server URL

class ApiService {
  constructor() {
    this.baseURL = BASE_URL;
    this.token = null;
  }

  async init() {
    try {
      this.token = await AsyncStorage.getItem('authToken');
    } catch (error) {
      console.log('Error loading auth token:', error);
    }
  }

  async setAuthToken(token) {
    this.token = token;
    await AsyncStorage.setItem('authToken', token);
  }

  async getAuthHeaders() {
    if (!this.token) {
      await this.init();
    }
    
    return {
      'Content-Type': 'application/json',
      'Authorization': `Bearer ${this.token}`,
    };
  }

  async getMultipartHeaders() {
    if (!this.token) {
      await this.init();
    }
    
    return {
      'Content-Type': 'multipart/form-data',
      'Authorization': `Bearer ${this.token}`,
    };
  }

  async makeRequest(endpoint, options = {}) {
    try {
      const url = `${this.baseURL}${endpoint}`;
      const headers = options.multipart 
        ? await this.getMultipartHeaders() 
        : await this.getAuthHeaders();

      const config = {
        ...options,
        headers: {
          ...headers,
          ...options.headers,
        },
      };

      console.log(`Making ${config.method || 'GET'} request to:`, url);
      
      const response = await fetch(url, config);
      
      if (!response.ok) {
        const errorText = await response.text();
        throw new Error(`HTTP ${response.status}: ${errorText}`);
      }

      const data = await response.json();
      return data;
    } catch (error) {
      console.error('API Request Error:', error);
      throw error;
    }
  }

  // File Management APIs
  async getUserFiles(params = {}) {
    const queryString = new URLSearchParams(params).toString();
    const endpoint = `/file_management/api/mobile/files/${queryString ? `?${queryString}` : ''}`;
    
    return await this.makeRequest(endpoint, {
      method: 'GET',
    });
  }

  async uploadFile(formData) {
    return await this.makeRequest('/file_management/api/mobile/upload/', {
      method: 'POST',
      body: formData,
      multipart: true,
    });
  }

  async getFileDetail(fileId) {
    return await this.makeRequest(`/file_management/api/mobile/files/${fileId}/`, {
      method: 'GET',
    });
  }

  async deleteFile(fileId) {
    return await this.makeRequest(`/file_management/api/mobile/files/${fileId}/`, {
      method: 'DELETE',
    });
  }

  async moveFile(fileId, categoryId) {
    return await this.makeRequest(`/file_management/api/mobile/files/${fileId}/move/`, {
      method: 'POST',
      body: JSON.stringify({ category_id: categoryId }),
    });
  }

  async shareFile(fileId) {
    return await this.makeRequest(`/file_management/api/mobile/files/${fileId}/share/`, {
      method: 'POST',
    });
  }

  async lockFile(fileId, password) {
    return await this.makeRequest(`/file_management/api/mobile/files/${fileId}/lock/`, {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
  }

  async unlockFile(fileId, password) {
    return await this.makeRequest(`/file_management/api/mobile/files/${fileId}/unlock/`, {
      method: 'POST',
      body: JSON.stringify({ password }),
    });
  }

  async renameFile(fileId, newName) {
    return await this.makeRequest(`/file_management/api/mobile/files/${fileId}/rename/`, {
      method: 'POST',
      body: JSON.stringify({ new_name: newName }),
    });
  }

  // OCR APIs
  async getOCRStatus(fileId) {
    return await this.makeRequest(`/file_management/api/mobile/files/${fileId}/ocr/`, {
      method: 'GET',
    });
  }

  async processOCR(fileId) {
    return await this.makeRequest(`/file_management/api/mobile/files/${fileId}/process-ocr/`, {
      method: 'POST',
    });
  }

  async getOCRPreferences() {
    return await this.makeRequest('/file_management/api/mobile/ocr-preferences/', {
      method: 'GET',
    });
  }

  async updateOCRPreferences(preference) {
    return await this.makeRequest('/file_management/api/mobile/ocr-preferences/', {
      method: 'POST',
      body: JSON.stringify({ preference }),
    });
  }

  // Document Pairing APIs
  async createDocumentPair(pairData) {
    return await this.makeRequest('/file_management/api/documents/create-pair/', {
      method: 'POST',
      body: JSON.stringify(pairData),
    });
  }

  async breakDocumentPair(fileId) {
    return await this.makeRequest(`/file_management/api/documents/${fileId}/break-pair/`, {
      method: 'POST',
    });
  }

  async getPairedDocuments() {
    return await this.makeRequest('/file_management/api/documents/paired/', {
      method: 'GET',
    });
  }

  // Category APIs
  async getCategories() {
    return await this.makeRequest('/file_management/api/categories/', {
      method: 'GET',
    });
  }

  async createCategory(categoryData) {
    return await this.makeRequest('/file_management/api/categories/', {
      method: 'POST',
      body: JSON.stringify(categoryData),
    });
  }

  // Card Management APIs
  async getCards() {
    return await this.makeRequest('/file_management/api/cards/', {
      method: 'GET',
    });
  }

  async createCard(cardData) {
    return await this.makeRequest('/file_management/api/cards/', {
      method: 'POST',
      body: JSON.stringify(cardData),
    });
  }

  async deleteCard(cardId) {
    return await this.makeRequest(`/file_management/api/cards/${cardId}/`, {
      method: 'DELETE',
    });
  }

  async extractCardFromDocument(fileId) {
    return await this.makeRequest('/file_management/api/cards/extract_from_document/', {
      method: 'POST',
      body: JSON.stringify({ file_id: fileId }),
    });
  }

  // Subscription Management APIs
  async getSubscriptions() {
    return await this.makeRequest('/file_management/api/subscriptions/', {
      method: 'GET',
    });
  }

  async createSubscription(subscriptionData) {
    return await this.makeRequest('/file_management/api/subscriptions/', {
      method: 'POST',
      body: JSON.stringify(subscriptionData),
    });
  }

  async deleteSubscription(subscriptionId) {
    return await this.makeRequest(`/file_management/api/subscriptions/${subscriptionId}/`, {
      method: 'DELETE',
    });
  }

  async extractSubscriptionFromDocument(fileId) {
    return await this.makeRequest('/file_management/api/subscriptions/extract_from_document/', {
      method: 'POST',
      body: JSON.stringify({ file_id: fileId }),
    });
  }

  // Expired Items API
  async getExpiredItems() {
    return await this.makeRequest('/file_management/api/expired-items/', {
      method: 'GET',
    });
  }

  // Search API
  async searchFiles(searchParams) {
    return await this.makeRequest('/file_management/api/files/search/', {
      method: 'POST',
      body: JSON.stringify(searchParams),
    });
  }

  // Authentication APIs (if needed)
  async login(credentials) {
    return await this.makeRequest('/auth/login/', {
      method: 'POST',
      body: JSON.stringify(credentials),
    });
  }

  async logout() {
    try {
      await this.makeRequest('/auth/logout/', {
        method: 'POST',
      });
    } catch (error) {
      console.log('Logout error:', error);
    } finally {
      this.token = null;
      await AsyncStorage.removeItem('authToken');
    }
  }

  async refreshToken() {
    try {
      const refreshToken = await AsyncStorage.getItem('refreshToken');
      if (!refreshToken) {
        throw new Error('No refresh token available');
      }

      const response = await this.makeRequest('/auth/refresh/', {
        method: 'POST',
        body: JSON.stringify({ refresh: refreshToken }),
      });

      if (response.access) {
        await this.setAuthToken(response.access);
        return response.access;
      }
      
      throw new Error('Failed to refresh token');
    } catch (error) {
      console.error('Token refresh error:', error);
      // Force logout if refresh fails
      await this.logout();
      throw error;
    }
  }

  // Utility method for handling token expiry
  async makeAuthenticatedRequest(endpoint, options = {}) {
    try {
      return await this.makeRequest(endpoint, options);
    } catch (error) {
      if (error.message.includes('401') || error.message.includes('403')) {
        try {
          await this.refreshToken();
          return await this.makeRequest(endpoint, options);
        } catch (refreshError) {
          throw new Error('Authentication failed. Please login again.');
        }
      }
      throw error;
    }
  }
}

// Create and export a singleton instance
const apiService = new ApiService();

export { apiService };
export default apiService;