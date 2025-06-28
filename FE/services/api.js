import axios from 'axios';

// Base URL - Ensure this points to your backend
const BASE_URL = 'http://10.0.2.2:8000/';

// Create Axios instance
const apiClient = axios.create({
  baseURL: BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Automatically fetch CSRF Token before making POST requests
const getCsrfToken = async () => {
  try {
    const response = await axios.get(`${BASE_URL}/auth/auth/csrf/`); // Endpoint should return CSRF token
    return response.data.csrf_token;
  } catch (error) {
    console.error('Failed to fetch CSRF token:', error);
    return null;
  }
};

// Function to set Authorization Token
export const setAuthToken = (token) => {
  if (token) {
    apiClient.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    delete apiClient.defaults.headers.common['Authorization'];
  }
};

/**
 * 🔹 File Management APIs
 */
import AsyncStorage from '@react-native-async-storage/async-storage';

export const getAuthHeadersForUpload = async () => {
  const token = await AsyncStorage.getItem('accessToken');
  return {
    Authorization: `Bearer ${token}`,
  };
};

export const uploadFile = async (fileUri, fileType, categoryId = null, originalName = null) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const uriParts = fileUri.split('/');
    const fallbackName = uriParts[uriParts.length - 1];
    const fileName = originalName || fallbackName; // ✅ Use passed name if available

    const fileExtension = fileName.split('.').pop().toLowerCase();

    let mimeType;
    if (fileType === 'document') {
      if (fileExtension === 'pdf') mimeType = 'application/pdf';
      else if (['doc', 'docx'].includes(fileExtension)) mimeType = 'application/msword';
      else if (fileExtension === 'txt') mimeType = 'text/plain';
      else mimeType = 'application/octet-stream';
    } else if (fileType === 'image') {
      if (['jpg', 'jpeg'].includes(fileExtension)) mimeType = 'image/jpeg';
      else if (fileExtension === 'png') mimeType = 'image/png';
      else mimeType = 'image/jpeg';
    } else {
      mimeType = 'application/octet-stream';
    }

    const formData = new FormData();
    formData.append('file', {
      uri: fileUri,
      name: fileName, // ✅ This is now accurate
      type: mimeType,
    });
    formData.append('file_type', fileType);
    if (categoryId) {
      formData.append('category_id', categoryId?.toString());
    }

    const response = await fetch('http://10.0.2.2:8000/file_management/api/mobile/files/', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
      },
      body: formData,
    });

    const data = await response.json();
    if (data.success) {
      // Parse OCR status if available
      const result = {
        ...data.data,
        auto_categorizing: data.data?.pending_auto_categorization || false,
        ocr_status: data.data?.ocr_status || null
      };
      return result;
    } else {
      throw new Error(data.error || 'Upload failed');
    }
  } catch (error) {
    console.error('Upload error:', error);
    throw error;
  }
};

export const getFiles = async (filters = {}) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const queryParams = new URLSearchParams();
    if (filters.category) queryParams.append('category', filters.category);
    if (filters.file_type) queryParams.append('file_type', filters.file_type);
    if (filters.search) queryParams.append('search', filters.search);

    const queryString = queryParams.toString() ? `?${queryParams.toString()}` : '';

    const response = await fetch(`http://10.0.2.2:8000/file_management/api/mobile/files/${queryString}`, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (data.success) {
      return data.data;
    } else {
      throw new Error(data.error || 'Failed to fetch files');
    }
  } catch (error) {
    console.error('Get files error:', error);
    throw error;
  }
};

/**
 * 🔹 Payments APIs
 */
export const paymentsAPI = {
  listPlans: () => apiClient.get('/payment/plans/'),
  createSubscription: (planType) => apiClient.post(`/payment/subscribe/${planType}/`),
  paymentCallback: (paymentData) => apiClient.post('/payment/payment/callback/', paymentData),
};

/**
 * 🔹 Storage Management APIs
 */
export const storageAPI = {
  getStorageInfo: () => apiClient.get('/storage/info/'),
};

/**
 * 🔹 Users Authentication APIs
 */
export const usersAPI = {
  googleLogin: () => apiClient.get('/auth/login/google/'),
  googleCallback: (code, state) => apiClient.get(`/auth/login/google/callback/?code=${code}&state=${state}`),
  signUp: (userData) => apiClient.post('/auth/signup/', userData),
  verifyEmail: (otp) => apiClient.post('/auth/verify-email/', { otp }),
};

/**
 * 🔹 Voice Assistant APIs
 */
export const voiceAssistantAPI = {
  assistantView: () => apiClient.get('/voice/assistant/'),
  processVoice: async (audioFile) => {
    const csrfToken = await getCsrfToken();
    if (!csrfToken) throw new Error('CSRF Token missing');

    const formData = new FormData();
    formData.append('audio', audioFile);

    return apiClient.post('/voice/voice/process/', formData, {
      headers: { 'Content-Type': 'multipart/form-data', 'X-CSRFToken': csrfToken },
    });
  },
};

/**
 * 🔹 AWS APIs
 */
export const awsAPI = {
  s3Upload: (file, authHeaders) => axios.put('AWS_S3_UPLOAD_URL', file, { headers: authHeaders }),
  s3Download: (authHeaders) => axios.get('AWS_S3_DOWNLOAD_URL', { headers: authHeaders }),
  textractProcess: (document, authHeaders) => axios.post('AWS_TEXTRACT_URL', document, { headers: authHeaders }),
};

/**
 * 🔹 OpenAI APIs
 */
export const openAIApi = {
  transcribeAudio: (audioFile, openAIKey) => {
    const formData = new FormData();
    formData.append('file', audioFile);
    return axios.post('OPENAI_TRANSCRIPTION_URL', formData, {
      headers: { Authorization: `Bearer ${openAIKey}` },
    });
  },
  chatCompletion: (messages, openAIKey) => axios.post('OPENAI_CHAT_COMPLETION_URL', { messages }, {
    headers: { Authorization: `Bearer ${openAIKey}` },
  }),
  textToSpeech: (inputText, openAIKey) => axios.post('OPENAI_TEXT_TO_SPEECH_URL', { input: inputText }, {
    headers: { Authorization: `Bearer ${openAIKey}` },
  }),
};

/**
 * 🔹 Razorpay APIs
 */
export const razorpayAPI = {
  createOrder: (orderData, razorpayAuth) => axios.post('RAZORPAY_ORDER_URL', orderData, {
    headers: { Authorization: `Bearer ${razorpayAuth}` },
  }),
  verifyPayment: (paymentData, razorpayAuth) => axios.post('RAZORPAY_VERIFY_PAYMENT_URL', paymentData, {
    headers: { Authorization: `Bearer ${razorpayAuth}` },
  }),
};

/**
 * 🔹 Google OAuth APIs
 */
export const googleOAuthAPI = {
  auth: (scope, redirectUri) => axios.get('GOOGLE_AUTH_URL', {
    params: { scope, redirect_uri: redirectUri },
  }),
  getUserInfo: (token) => axios.get('GOOGLE_USER_INFO_URL', {
    headers: { Authorization: `Bearer ${token}` },
  }),
};

export const processTextCommand = async (text, includeAudio = true) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const response = await fetch('http://10.0.2.2:8000/voice/api/process/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        text,
        include_audio: includeAudio.toString(), // true or false as string
      }),
    });

    const result = await response.json();

    if (!result.success) {
      throw new Error(result.error || 'Sparkle processing failed');
    }

    const data = result.data;

    // 🔥 Log the complete response for debugging
    console.log("🔥 Sparkle API response:", JSON.stringify(data, null, 2));

    // Extract file details if present and valid
    const file_details =
      data?.action?.type === 'display_file' && data?.action?.payload?.fileUrl
        ? {
            ...data.action.payload,
            fileExtension:
              data.action.payload.fileName?.split('.').pop()?.toLowerCase() || null,
          }
        : null;

    // Optional: Log warning if expected fileUrl is missing
    if (data?.action?.type === 'display_file' && !data?.action?.payload?.fileUrl) {
      console.warn('⚠️ File display action received, but no fileUrl found:', data.action.payload);
    }

    return {
      success: true,
      prompt: data.prompt,
      response: data.response,
      audio_url: data.audio_url || null,
      interaction_id: data.interaction_id,
      interaction_success: data.interaction_success || false,
      file_details,
      action: data?.action || null, // for future use (e.g. summarize, list, search)
    };
  } catch (err) {
    console.error('🔥 Error processing text command:', err);
    throw err;
  }
};

/**
 * Delete a file
 * @param {number} fileId
 */
export const deleteFile = async (fileId) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const response = await fetch(`${BASE_URL}file_management/api/mobile/files/${fileId}/`, {
      method: 'DELETE',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json();
    if (data.success) {
      return true;
    } else {
      throw new Error(data.error || 'Failed to delete file');
    }
  } catch (error) {
    console.error('Delete file error:', error);
    throw error;
  }
};

/**
 * Move a file to a different category
 * @param {number} fileId
 * @param {number} categoryId
 */
export const moveFile = async (fileId, categoryId) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const response = await fetch(`${BASE_URL}file_management/api/mobile/files/${fileId}/move/`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ category_id: categoryId }),
    });

    const data = await response.json();
    if (data.success) {
      return data.file;
    } else {
      throw new Error(data.error || 'Failed to move file');
    }
  } catch (error) {
    console.error('Move file error:', error);
    throw error;
  }
};

/**
 * Rename a file
 * @param {number} fileId
 * @param {string} newName
 */
export const renameFile = async (fileId, newName) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const response = await fetch(`${BASE_URL}file_management/api/mobile/files/${fileId}/rename/`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ new_name: newName }),
    });

    const data = await response.json();
    if (data.success) {
      return data.file;
    } else {
      throw new Error(data.error || 'Failed to rename file');
    }
  } catch (error) {
    console.error('Rename file error:', error);
    throw error;
  }
};

/**
 * Get all file categories
 * Returns an array of { id, name, description }
 */
export const getCategories = async () => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const response = await fetch(`${BASE_URL}file_management/api/categories/`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
    });

    const data = await response.json();

    if (Array.isArray(data.results)) {
      return data.results;
    } else {
      throw new Error('Failed to fetch categories');
    }
  } catch (error) {
    console.error('Get categories error:', error);
    throw error;
  }
};

/**
 * Lock a file with password protection
 * @param {number} fileId
 * @param {string} password
 */
export const lockFile = async (fileId, password) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const response = await fetch(`${BASE_URL}file_management/api/mobile/files/${fileId}/lock/`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
    });

    const data = await response.json();
    if (data.success) {
      return true;
    } else {
      throw new Error(data.error || 'Failed to lock file');
    }
  } catch (error) {
    console.error('Lock file error:', error);
    throw error;
  }
};

/**
 * Unlock a file using password
 * @param {number} fileId
 * @param {string} password
 */
export const unlockFile = async (fileId, password) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const response = await fetch(`${BASE_URL}file_management/api/mobile/files/${fileId}/unlock/`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ password }),
    });

    const data = await response.json();
    if (data.success) {
      return true;
    } else {
      throw new Error(data.error || 'Failed to unlock file');
    }
  } catch (error) {
    console.error('Unlock file error:', error);
    throw error;
  }
};

export const toggleFileFavorite = async (fileId) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');

    const response = await fetch(`http://10.0.2.2:8000/file_management/api/mobile/files/${fileId}/favorite/`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${token}`,
        Accept: 'application/json', // ✅ Important to ensure JSON response
        'Content-Type': 'application/json',
      },
    });

    // Catch non-200 responses
    if (!response.ok) {
      const errorText = await response.text();
      console.error('❌ Non-200 response:', errorText);
      throw new Error('Server error occurred');
    }

    const data = await response.json();

    if (data.success) {
      return {
        isFavorite: data.is_favorite,
        message: data.message,
      };
    } else {
      throw new Error(data.error || 'Failed to toggle favorite status');
    }
  } catch (error) {
    console.error('🔥 Toggle favorite error:', error);
    throw error;
  }
};

// Add a new API function to get OCR status
export const getOcrStatus = async (fileId) => {
  try {
    const token = await AsyncStorage.getItem('accessToken');
    const response = await fetch(`http://10.0.2.2:8000/file_management/api/mobile/files/${fileId}/ocr/`, {
      method: 'GET',
      headers: {
        Authorization: `Bearer ${token}`,
      },
    });

    const data = await response.json();
    if (data.success) {
      return data.data;
    } else {
      throw new Error(data.error || 'Failed to get OCR status');
    }
  } catch (error) {
    console.error('OCR status error:', error);
    throw error;
  }
};