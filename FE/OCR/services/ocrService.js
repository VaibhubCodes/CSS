import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = 'http://your-backend-url.com'; // Replace with your actual URL

class OCRService {
  async getAuthToken() {
    return await AsyncStorage.getItem('authToken');
  }

  async getAuthHeaders() {
    const token = await this.getAuthToken();
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  // Upload file with OCR processing
  async uploadFile(fileData, fileType, categoryId = null) {
    try {
      const formData = new FormData();
      formData.append('file', {
        uri: fileData.uri,
        type: fileData.type || 'application/octet-stream',
        name: fileData.name || 'upload.pdf',
      });
      formData.append('file_type', fileType);
      
      if (categoryId) {
        formData.append('category_id', categoryId.toString());
      }

      const token = await this.getAuthToken();
      const response = await fetch(`${API_BASE_URL}/file_management/api/mobile/upload/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
        body: formData,
      });

      if (!response.ok) {
        throw new Error(`Upload failed: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('File upload error:', error);
      throw error;
    }
  }

  // Get OCR status for a specific file
  async getOCRStatus(fileId) {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/file_management/api/mobile/files/${fileId}/ocr/`, {
        headers,
      });

      if (!response.ok) {
        throw new Error(`Failed to get OCR status: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('OCR status error:', error);
      throw error;
    }
  }

  // Manually trigger OCR processing
  async processOCR(fileId) {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/file_management/api/mobile/files/${fileId}/process-ocr/`, {
        method: 'POST',
        headers,
      });

      if (!response.ok) {
        throw new Error(`OCR processing failed: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('OCR processing error:', error);
      throw error;
    }
  }

  // Get file details with OCR text
  async getFileDetails(fileId) {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/file_management/api/mobile/files/${fileId}/`, {
        headers,
      });

      if (!response.ok) {
        throw new Error(`Failed to get file details: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('File details error:', error);
      throw error;
    }
  }

  // Get files list
  async getFiles(category = null, search = null) {
    try {
      const headers = await this.getAuthHeaders();
      let url = `${API_BASE_URL}/file_management/api/mobile/files/`;
      
      const params = new URLSearchParams();
      if (category) params.append('category', category);
      if (search) params.append('search', search);
      
      if (params.toString()) {
        url += `?${params.toString()}`;
      }

      const response = await fetch(url, { headers });

      if (!response.ok) {
        throw new Error(`Failed to get files: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Get files error:', error);
      throw error;
    }
  }

  // Get OCR preferences
  async getOCRPreferences() {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/file_management/api/mobile/ocr-preferences/`, {
        headers,
      });

      if (!response.ok) {
        throw new Error(`Failed to get OCR preferences: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('OCR preferences error:', error);
      throw error;
    }
  }

  // Update OCR preferences
  async updateOCRPreferences(preference) {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}/file_management/api/mobile/ocr-preferences/`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ preference }),
      });

      if (!response.ok) {
        throw new Error(`Failed to update OCR preferences: ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error('Update OCR preferences error:', error);
      throw error;
    }
  }
}

export default new OCRService();