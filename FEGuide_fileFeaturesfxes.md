# Frontend Integration Guide - File Management & Storage Updates

## 📋 **Overview**

This guide covers all the backend changes made to the Django file management system and how to integrate them into your React Native frontend. The changes include enhanced file features (hidden, favorite, lock, password), improved storage management, and new API endpoints.

---

## 🎯 **New Features Summary**

### **File Management Features:**
1. **Hidden Files**: Hide/show files from normal view
2. **Favorite Files**: Mark files as favorites for quick access
3. **File Locking**: Password-protect files with secure access
4. **Enhanced Security**: Improved password validation and access control

### **Storage Management Features:**
1. **Accurate Storage Calculation**: Fixed phantom usage issues
2. **Real-time Validation**: Cross-validation between database and S3
3. **Orphan File Cleanup**: Automatic cleanup of unused files
4. **Enhanced Analytics**: Detailed storage breakdown and insights

---

## 🔗 **Updated API Endpoints**

### **New File Management Endpoints**

```javascript
// Base URL for all endpoints
const BASE_URL = 'https://your-api-domain.com/file_management';

// File Management APIs
const FILE_API = {
  // Existing endpoints (enhanced)
  uploadFile: 'POST /api/upload/',
  listFiles: 'GET /api/files/',
  deleteFile: 'DELETE /api/files/{id}/',
  
  // NEW: File feature endpoints
  toggleFavorite: 'POST /api/files/{id}/toggle-favorite/',
  toggleHidden: 'POST /api/files/{id}/toggle-hidden/',
  lockFile: 'POST /api/files/{id}/lock/',
  unlockFile: 'POST /api/files/{id}/unlock/',
  accessLockedFile: 'POST /api/files/{id}/access-locked/',
  
  // Enhanced mobile endpoints
  mobileFileList: 'GET /api/mobile/files/',
  mobileFileDetail: 'GET /api/mobile/files/{id}/',
  mobileUpload: 'POST /api/mobile/upload/',
  
  // Document pairing
  createPair: 'POST /api/documents/create-pair/',
  breakPair: 'POST /api/documents/{id}/break-pair/',
  getPairedDocs: 'GET /api/documents/paired/',
};

// Storage Management APIs
const STORAGE_API = {
  getStorageInfo: 'GET /storage_management/api/storage/',
  recalculateStorage: 'POST /storage_management/api/storage/recalculate/',
  getAnalytics: 'GET /storage_management/api/storage/analytics/',
  cleanOrphans: 'POST /storage_management/api/storage/clean_orphans/',
};
```

---

## 📱 **React Native Service Classes**

### **1. Enhanced File Service**

```javascript
// services/FileService.js
import AsyncStorage from '@react-native-async-storage/async-storage';

class FileService {
  constructor() {
    this.baseURL = 'https://your-api-domain.com/file_management';
  }

  async getAuthHeaders() {
    const token = await AsyncStorage.getItem('authToken');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  // ====== FILE LISTING WITH FILTERS ======
  async getFiles(filters = {}) {
    const queryParams = new URLSearchParams();
    
    // Add filter parameters
    if (filters.category) queryParams.append('category', filters.category);
    if (filters.fileType) queryParams.append('file_type', filters.fileType);
    if (filters.search) queryParams.append('search', filters.search);
    if (filters.showHidden) queryParams.append('show_hidden', filters.showHidden);
    if (filters.favoritesOnly) queryParams.append('favorites_only', filters.favoritesOnly);

    const response = await fetch(
      `${this.baseURL}/api/mobile/files/?${queryParams}`,
      {
        method: 'GET',
        headers: await this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch files: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      files: data.files || [],
      categories: data.categories || [],
      counts: data.counts || {},
    };
  }

  // ====== FAVORITE MANAGEMENT ======
  async toggleFavorite(fileId) {
    const response = await fetch(
      `${this.baseURL}/api/files/${fileId}/toggle-favorite/`,
      {
        method: 'POST',
        headers: await this.getAuthHeaders(),
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to toggle favorite');
    }

    return {
      isFavorite: data.is_favorite,
      message: data.message,
    };
  }

  // ====== HIDDEN FILE MANAGEMENT ======
  async toggleHidden(fileId) {
    const response = await fetch(
      `${this.baseURL}/api/files/${fileId}/toggle-hidden/`,
      {
        method: 'POST',
        headers: await this.getAuthHeaders(),
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to toggle hidden status');
    }

    return {
      isHidden: data.is_hidden,
      message: data.message,
    };
  }

  // ====== FILE LOCKING ======
  async lockFile(fileId, password) {
    // Validate password on frontend first
    if (!password || password.length < 6) {
      throw new Error('Password must be at least 6 characters long');
    }

    const response = await fetch(
      `${this.baseURL}/api/files/${fileId}/lock/`,
      {
        method: 'POST',
        headers: await this.getAuthHeaders(),
        body: JSON.stringify({ password }),
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      // Handle validation errors
      if (data.errors) {
        const errorMessage = Object.values(data.errors).flat().join(', ');
        throw new Error(errorMessage);
      }
      throw new Error(data.error || 'Failed to lock file');
    }

    return {
      message: data.message,
      lockedAt: data.locked_at,
    };
  }

  async unlockFile(fileId, password) {
    const response = await fetch(
      `${this.baseURL}/api/files/${fileId}/unlock/`,
      {
        method: 'POST',
        headers: await this.getAuthHeaders(),
        body: JSON.stringify({ password }),
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to unlock file');
    }

    return {
      message: data.message,
    };
  }

  // ====== SECURE FILE ACCESS ======
  async accessLockedFile(fileId, password) {
    const response = await fetch(
      `${this.baseURL}/api/files/${fileId}/access-locked/`,
      {
        method: 'POST',
        headers: await this.getAuthHeaders(),
        body: JSON.stringify({ password }),
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Access denied');
    }

    return {
      accessUrl: data.access_url,
      expiresIn: data.expires_in,
      file: data.file,
    };
  }

  // ====== FILE UPLOAD WITH ENHANCED FEATURES ======
  async uploadFile(fileData, options = {}) {
    const formData = new FormData();
    formData.append('file', {
      uri: fileData.uri,
      type: fileData.type,
      name: fileData.name,
    });
    formData.append('file_type', fileData.fileType);
    
    if (options.categoryId) {
      formData.append('category_id', options.categoryId);
    }

    const token = await AsyncStorage.getItem('authToken');
    const response = await fetch(
      `${this.baseURL}/api/mobile/upload/`,
      {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'multipart/form-data',
        },
        body: formData,
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Upload failed');
    }

    return {
      file: data.file,
      storageInfo: data.storage_info,
      ocrResult: data.ocr_result,
    };
  }

  // ====== FILE DELETION ======
  async deleteFile(fileId) {
    const response = await fetch(
      `${this.baseURL}/api/mobile/files/${fileId}/`,
      {
        method: 'DELETE',
        headers: await this.getAuthHeaders(),
      }
    );

    const data = await response.json();
    
    if (!data.success && response.status !== 200) {
      throw new Error(data.error || 'Failed to delete file');
    }

    return {
      message: data.message || 'File deleted successfully',
    };
  }

  // ====== DOCUMENT PAIRING ======
  async createDocumentPair(frontFileId, backFileId, documentTypeName) {
    const response = await fetch(
      `${this.baseURL}/api/documents/create-pair/`,
      {
        method: 'POST',
        headers: await this.getAuthHeaders(),
        body: JSON.stringify({
          front_file_id: frontFileId,
          back_file_id: backFileId,
          document_type_name: documentTypeName,
        }),
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to create document pair');
    }

    return {
      frontFile: data.front_file,
      backFile: data.back_file,
      message: data.message,
    };
  }

  async breakDocumentPair(fileId) {
    const response = await fetch(
      `${this.baseURL}/api/documents/${fileId}/break-pair/`,
      {
        method: 'POST',
        headers: await this.getAuthHeaders(),
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to break document pair');
    }

    return {
      message: data.message,
    };
  }
}

export default new FileService();
```

### **2. Storage Management Service**

```javascript
// services/StorageService.js
import AsyncStorage from '@react-native-async-storage/async-storage';

class StorageService {
  constructor() {
    this.baseURL = 'https://your-api-domain.com/storage_management';
  }

  async getAuthHeaders() {
    const token = await AsyncStorage.getItem('authToken');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  // ====== STORAGE INFO ======
  async getStorageInfo() {
    const response = await fetch(
      `${this.baseURL}/api/storage/`,
      {
        method: 'GET',
        headers: await this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch storage info: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      used: data.storage_used,
      limit: data.storage_limit,
      usedFormatted: data.storage_used_formatted,
      limitFormatted: data.storage_limit_formatted,
      availableFormatted: data.available_storage_formatted,
      usagePercentage: data.usage_percentage,
      subscriptionInfo: data.subscription_info,
      validation: data.validation, // New: validation info
    };
  }

  // ====== STORAGE ANALYTICS ======
  async getStorageAnalytics() {
    const response = await fetch(
      `${this.baseURL}/api/storage/analytics/`,
      {
        method: 'GET',
        headers: await this.getAuthHeaders(),
      }
    );

    if (!response.ok) {
      throw new Error(`Failed to fetch analytics: ${response.statusText}`);
    }

    const data = await response.json();
    return {
      storageOverview: data.storage_overview,
      storageBreakdown: data.storage_breakdown,
      monthlyTrends: data.monthly_trends,
      isSparkle: data.is_sparkle,
      sparkleAnalytics: data.sparkle_analytics,
    };
  }

  // ====== STORAGE MAINTENANCE ======
  async recalculateStorage() {
    const response = await fetch(
      `${this.baseURL}/api/storage/recalculate/`,
      {
        method: 'POST',
        headers: await this.getAuthHeaders(),
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to recalculate storage');
    }

    return {
      message: data.message,
      storageInfo: data.storage_info,
    };
  }

  async cleanOrphanedFiles(dryRun = true) {
    const response = await fetch(
      `${this.baseURL}/api/storage/clean_orphans/`,
      {
        method: 'POST',
        headers: await this.getAuthHeaders(),
        body: JSON.stringify({ dry_run: dryRun }),
      }
    );

    const data = await response.json();
    
    if (!data.success) {
      throw new Error(data.error || 'Failed to clean orphaned files');
    }

    return {
      orphanInfo: data.orphan_info,
      dryRun: data.dry_run,
    };
  }
}

export default new StorageService();
```

---

## 🎨 **UI Components Guide**

### **1. Enhanced File List Component**

```javascript
// components/FileList.jsx
import React, { useState, useEffect, useCallback } from 'react';
import { 
  View, 
  FlatList, 
  Text, 
  TouchableOpacity, 
  Alert,
  StyleSheet 
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialIcons';
import FileService from '../services/FileService';

const FileList = ({ navigation }) => {
  const [files, setFiles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [counts, setCounts] = useState({});
  const [filters, setFilters] = useState({
    category: 'all',
    showHidden: false,
    favoritesOnly: false,
  });
  const [loading, setLoading] = useState(false);

  const loadFiles = useCallback(async () => {
    setLoading(true);
    try {
      const data = await FileService.getFiles(filters);
      setFiles(data.files);
      setCategories(data.categories);
      setCounts(data.counts);
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  }, [filters]);

  useEffect(() => {
    loadFiles();
  }, [loadFiles]);

  const handleToggleFavorite = async (fileId) => {
    try {
      const result = await FileService.toggleFavorite(fileId);
      
      // Update local state
      setFiles(prevFiles => 
        prevFiles.map(file => 
          file.id === fileId 
            ? { ...file, is_favorite: result.isFavorite }
            : file
        )
      );
      
      // Show success message
      Alert.alert('Success', result.message);
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const handleToggleHidden = async (fileId) => {
    try {
      const result = await FileService.toggleHidden(fileId);
      
      // If not showing hidden files, remove from list
      if (!filters.showHidden && result.isHidden) {
        setFiles(prevFiles => prevFiles.filter(file => file.id !== fileId));
      } else {
        // Update local state
        setFiles(prevFiles => 
          prevFiles.map(file => 
            file.id === fileId 
              ? { ...file, is_hidden: result.isHidden }
              : file
          )
        );
      }
      
      Alert.alert('Success', result.message);
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const handleLockFile = (file) => {
    navigation.navigate('LockFile', { fileId: file.id, fileName: file.original_filename });
  };

  const handleAccessFile = (file) => {
    if (file.is_locked) {
      navigation.navigate('UnlockFile', { 
        fileId: file.id, 
        fileName: file.original_filename 
      });
    } else {
      navigation.navigate('FileViewer', { file });
    }
  };

  const renderFileItem = ({ item: file }) => (
    <View style={styles.fileItem}>
      <View style={styles.fileInfo}>
        <Text style={styles.fileName}>
          {file.original_filename}
          {file.is_locked && <Icon name="lock" size={16} color="#ff6b35" />}
          {file.is_hidden && <Icon name="visibility-off" size={16} color="#666" />}
        </Text>
        <Text style={styles.fileSize}>{file.file_size_display}</Text>
        <Text style={styles.fileCategory}>{file.category?.name || 'Uncategorized'}</Text>
      </View>
      
      <View style={styles.fileActions}>
        {/* Favorite Button */}
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => handleToggleFavorite(file.id)}
        >
          <Icon 
            name={file.is_favorite ? "favorite" : "favorite-border"} 
            size={24} 
            color={file.is_favorite ? "#ff6b35" : "#666"} 
          />
        </TouchableOpacity>

        {/* Hidden Toggle */}
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => handleToggleHidden(file.id)}
        >
          <Icon 
            name={file.is_hidden ? "visibility-off" : "visibility"} 
            size={24} 
            color="#666" 
          />
        </TouchableOpacity>

        {/* Lock/Unlock */}
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => handleLockFile(file)}
        >
          <Icon 
            name={file.is_locked ? "lock" : "lock-open"} 
            size={24} 
            color={file.is_locked ? "#ff6b35" : "#666"} 
          />
        </TouchableOpacity>

        {/* Access File */}
        <TouchableOpacity
          style={styles.actionButton}
          onPress={() => handleAccessFile(file)}
        >
          <Icon name="open-in-new" size={24} color="#007AFF" />
        </TouchableOpacity>
      </View>
    </View>
  );

  const renderFilters = () => (
    <View style={styles.filtersContainer}>
      <TouchableOpacity
        style={[
          styles.filterButton,
          filters.favoritesOnly && styles.filterButtonActive
        ]}
        onPress={() => setFilters(prev => ({ 
          ...prev, 
          favoritesOnly: !prev.favoritesOnly 
        }))}
      >
        <Icon name="favorite" size={16} />
        <Text>Favorites ({counts.favorites || 0})</Text>
      </TouchableOpacity>

      <TouchableOpacity
        style={[
          styles.filterButton,
          filters.showHidden && styles.filterButtonActive
        ]}
        onPress={() => setFilters(prev => ({ 
          ...prev, 
          showHidden: !prev.showHidden 
        }))}
      >
        <Icon name="visibility-off" size={16} />
        <Text>Hidden ({counts.hidden || 0})</Text>
      </TouchableOpacity>
    </View>
  );

  return (
    <View style={styles.container}>
      {renderFilters()}
      
      <FlatList
        data={files}
        renderItem={renderFileItem}
        keyExtractor={item => item.id.toString()}
        refreshing={loading}
        onRefresh={loadFiles}
        ListEmptyComponent={
          <Text style={styles.emptyText}>No files found</Text>
        }
      />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#fff',
  },
  filtersContainer: {
    flexDirection: 'row',
    padding: 16,
    backgroundColor: '#f8f9fa',
  },
  filterButton: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 8,
    marginRight: 12,
    borderRadius: 8,
    backgroundColor: '#e9ecef',
  },
  filterButtonActive: {
    backgroundColor: '#007AFF',
  },
  fileItem: {
    flexDirection: 'row',
    padding: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  fileInfo: {
    flex: 1,
  },
  fileName: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 4,
  },
  fileSize: {
    fontSize: 14,
    color: '#666',
    marginBottom: 2,
  },
  fileCategory: {
    fontSize: 12,
    color: '#007AFF',
  },
  fileActions: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  actionButton: {
    padding: 8,
    marginLeft: 4,
  },
  emptyText: {
    textAlign: 'center',
    marginTop: 50,
    fontSize: 16,
    color: '#666',
  },
});

export default FileList;
```

### **2. File Lock/Unlock Component**

```javascript
// components/LockFile.jsx
import React, { useState } from 'react';
import { 
  View, 
  Text, 
  TextInput, 
  TouchableOpacity, 
  Alert,
  StyleSheet 
} from 'react-native';
import FileService from '../services/FileService';

const LockFile = ({ route, navigation }) => {
  const { fileId, fileName } = route.params;
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const validatePassword = (pwd) => {
    if (pwd.length < 6) {
      return 'Password must be at least 6 characters long';
    }
    if (!/\d/.test(pwd)) {
      return 'Password must contain at least one digit';
    }
    if (!/[a-zA-Z]/.test(pwd)) {
      return 'Password must contain at least one letter';
    }
    return null;
  };

  const handleLockFile = async () => {
    // Validate inputs
    const passwordError = validatePassword(password);
    if (passwordError) {
      Alert.alert('Invalid Password', passwordError);
      return;
    }

    if (password !== confirmPassword) {
      Alert.alert('Error', 'Passwords do not match');
      return;
    }

    setLoading(true);
    try {
      const result = await FileService.lockFile(fileId, password);
      
      Alert.alert(
        'Success', 
        result.message,
        [
          {
            text: 'OK',
            onPress: () => navigation.goBack(),
          },
        ]
      );
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Lock File</Text>
      <Text style={styles.fileName}>{fileName}</Text>

      <View style={styles.form}>
        <Text style={styles.label}>Password</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholder="Enter password (min 6 characters)"
          autoCapitalize="none"
        />

        <Text style={styles.label}>Confirm Password</Text>
        <TextInput
          style={styles.input}
          value={confirmPassword}
          onChangeText={setConfirmPassword}
          secureTextEntry
          placeholder="Confirm password"
          autoCapitalize="none"
        />

        <View style={styles.requirements}>
          <Text style={styles.requirementsTitle}>Password Requirements:</Text>
          <Text style={styles.requirement}>• At least 6 characters long</Text>
          <Text style={styles.requirement}>• Must contain at least one letter</Text>
          <Text style={styles.requirement}>• Must contain at least one digit</Text>
        </View>

        <TouchableOpacity
          style={[styles.button, loading && styles.buttonDisabled]}
          onPress={handleLockFile}
          disabled={loading}
        >
          <Text style={styles.buttonText}>
            {loading ? 'Locking...' : 'Lock File'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

// UnlockFile component (similar structure)
const UnlockFile = ({ route, navigation }) => {
  const { fileId, fileName } = route.params;
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleUnlockFile = async () => {
    if (!password) {
      Alert.alert('Error', 'Please enter the password');
      return;
    }

    setLoading(true);
    try {
      const result = await FileService.unlockFile(fileId, password);
      
      Alert.alert(
        'Success', 
        result.message,
        [
          {
            text: 'OK',
            onPress: () => navigation.goBack(),
          },
        ]
      );
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleAccessFile = async () => {
    if (!password) {
      Alert.alert('Error', 'Please enter the password');
      return;
    }

    setLoading(true);
    try {
      const result = await FileService.accessLockedFile(fileId, password);
      
      // Navigate to file viewer with access URL
      navigation.navigate('FileViewer', { 
        file: result.file,
        accessUrl: result.accessUrl,
        expiresIn: result.expiresIn,
      });
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={styles.container}>
      <Text style={styles.title}>Access Locked File</Text>
      <Text style={styles.fileName}>{fileName}</Text>

      <View style={styles.form}>
        <Text style={styles.label}>Password</Text>
        <TextInput
          style={styles.input}
          value={password}
          onChangeText={setPassword}
          secureTextEntry
          placeholder="Enter file password"
          autoCapitalize="none"
        />

        <View style={styles.buttonContainer}>
          <TouchableOpacity
            style={[styles.button, styles.unlockButton]}
            onPress={handleUnlockFile}
            disabled={loading}
          >
            <Text style={styles.buttonText}>Unlock Permanently</Text>
          </TouchableOpacity>

          <TouchableOpacity
            style={[styles.button, styles.accessButton]}
            onPress={handleAccessFile}
            disabled={loading}
          >
            <Text style={styles.buttonText}>Access Temporarily</Text>
          </TouchableOpacity>
        </View>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#fff',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 10,
  },
  fileName: {
    fontSize: 16,
    color: '#666',
    marginBottom: 30,
  },
  form: {
    flex: 1,
  },
  label: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 8,
    marginTop: 16,
  },
  input: {
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  requirements: {
    marginTop: 20,
    padding: 16,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
  },
  requirementsTitle: {
    fontSize: 14,
    fontWeight: '500',
    marginBottom: 8,
  },
  requirement: {
    fontSize: 12,
    color: '#666',
    marginBottom: 4,
  },
  button: {
    backgroundColor: '#007AFF',
    padding: 16,
    borderRadius: 8,
    alignItems: 'center',
    marginTop: 24,
  },
  buttonDisabled: {
    backgroundColor: '#ccc',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '500',
  },
  buttonContainer: {
    marginTop: 24,
  },
  unlockButton: {
    backgroundColor: '#28a745',
    marginBottom: 12,
  },
  accessButton: {
    backgroundColor: '#007AFF',
  },
});

export { LockFile, UnlockFile };
```

### **3. Storage Dashboard Component**

```javascript
// components/StorageDashboard.jsx
import React, { useState, useEffect } from 'react';
import { 
  View, 
  Text, 
  TouchableOpacity, 
  ScrollView,
  Alert,
  StyleSheet 
} from 'react-native';
import { PieChart, BarChart } from 'react-native-chart-kit';
import StorageService from '../services/StorageService';

const StorageDashboard = () => {
  const [storageInfo, setStorageInfo] = useState(null);
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    loadStorageData();
  }, []);

  const loadStorageData = async () => {
    setLoading(true);
    try {
      const [storage, analyticsData] = await Promise.all([
        StorageService.getStorageInfo(),
        StorageService.getStorageAnalytics(),
      ]);
      
      setStorageInfo(storage);
      setAnalytics(analyticsData);
    } catch (error) {
      Alert.alert('Error', error.message);
    } finally {
      setLoading(false);
    }
  };

  const handleRecalculateStorage = async () => {
    try {
      const result = await StorageService.recalculateStorage();
      Alert.alert('Success', result.message);
      loadStorageData(); // Refresh data
    } catch (error) {
      Alert.alert('Error', error.message);
    }
  };

  const handleCleanOrphans = async () => {
    Alert.alert(
      'Clean Orphaned Files',
      'This will remove files from storage that are not linked to any records. Continue?',
      [
        { text: 'Cancel', style: 'cancel' },
        {
          text: 'Clean',
          style: 'destructive',
          onPress: async () => {
            try {
              const result = await StorageService.cleanOrphanedFiles(false);
              const cleaned = result.orphanInfo.orphaned_files?.length || 0;
              Alert.alert('Success', `Cleaned ${cleaned} orphaned files`);
              loadStorageData();
            } catch (error) {
              Alert.alert('Error', error.message);
            }
          },
        },
      ]
    );
  };

  const renderStorageOverview = () => {
    if (!storageInfo) return null;

    const usagePercentage = storageInfo.usagePercentage || 0;
    const isSparkle = storageInfo.subscriptionInfo?.is_sparkle || false;

    return (
      <View style={styles.overviewCard}>
        <Text style={styles.cardTitle}>Storage Overview</Text>
        
        <View style={styles.usageContainer}>
          <View style={styles.usageBar}>
            <View 
              style={[
                styles.usageProgress, 
                { 
                  width: `${usagePercentage}%`,
                  backgroundColor: usagePercentage > 90 ? '#ff4757' : 
                                  usagePercentage > 75 ? '#ffa502' : '#2ed573'
                }
              ]} 
            />
          </View>
          <Text style={styles.usageText}>
            {storageInfo.usedFormatted} of {storageInfo.limitFormatted} used ({usagePercentage.toFixed(1)}%)
          </Text>
        </View>

        {isSparkle && (
          <View style={styles.sparkleBadge}>
            <Text style={styles.sparkleText}>✨ Sparkle Plan</Text>
          </View>
        )}

        {/* Validation Status */}
        {storageInfo.validation && (
          <View style={styles.validationStatus}>
            <Text style={styles.validationTitle}>Storage Validation:</Text>
            <Text style={styles.validationText}>
              Database: {formatBytes(storageInfo.validation.db_size)}
            </Text>
            <Text style={styles.validationText}>
              S3: {formatBytes(storageInfo.validation.s3_size)}
            </Text>
            <Text style={styles.validationText}>
              Method: {storageInfo.validation.method}
            </Text>
          </View>
        )}

        <View style={styles.actionButtons}>
          <TouchableOpacity
            style={styles.actionButton}
            onPress={handleRecalculateStorage}
          >
            <Text style={styles.actionButtonText}>Recalculate</Text>
          </TouchableOpacity>
          
          <TouchableOpacity
            style={[styles.actionButton, styles.dangerButton]}
            onPress={handleCleanOrphans}
          >
            <Text style={styles.actionButtonText}>Clean Orphans</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  };

  const renderStorageBreakdown = () => {
    if (!analytics?.storageBreakdown) return null;

    const chartData = analytics.storageBreakdown.map((item, index) => ({
      name: item.category,
      size: item.size,
      color: getColorForIndex(index),
      legendFontColor: '#7F7F7F',
      legendFontSize: 12,
    }));

    return (
      <View style={styles.chartCard}>
        <Text style={styles.cardTitle}>Storage by Category</Text>
        
        {chartData.length > 0 ? (
          <PieChart
            data={chartData}
            width={300}
            height={200}
            chartConfig={{
              color: (opacity = 1) => `rgba(26, 255, 146, ${opacity})`,
            }}
            accessor="size"
            backgroundColor="transparent"
            paddingLeft="15"
          />
        ) : (
          <Text style={styles.emptyText}>No data available</Text>
        )}
      </View>
    );
  };

  const renderSparkleAnalytics = () => {
    if (!analytics?.isSparkle || !analytics?.sparkleAnalytics) return null;

    const sparkleData = analytics.sparkleAnalytics;

    return (
      <View style={styles.sparkleCard}>
        <Text style={styles.cardTitle}>✨ Sparkle Analytics</Text>
        
        <View style={styles.statsGrid}>
          <View style={styles.statItem}>
            <Text style={styles.statValue}>{sparkleData.total_files}</Text>
            <Text style={styles.statLabel}>Total Files</Text>
          </View>
          
          <View style={styles.statItem}>
            <Text style={styles.statValue}>
              {formatBytes(sparkleData.average_file_size)}
            </Text>
            <Text style={styles.statLabel}>Avg File Size</Text>
          </View>
        </View>

        <Text style={styles.subTitle}>File Types</Text>
        {sparkleData.file_types?.map((type, index) => (
          <View key={index} style={styles.fileTypeItem}>
            <Text style={styles.fileTypeName}>{type.file_type}</Text>
            <Text style={styles.fileTypeCount}>{type.count} files</Text>
            <Text style={styles.fileTypeSize}>{formatBytes(type.total_size)}</Text>
          </View>
        ))}
      </View>
    );
  };

  const formatBytes = (bytes) => {
    if (bytes === 0) return '0 B';
    const k = 1024;
    const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
  };

  const getColorForIndex = (index) => {
    const colors = ['#ff6b6b', '#4ecdc4', '#45b7d1', '#96ceb4', '#ffeaa7', '#dda0dd'];
    return colors[index % colors.length];
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <Text>Loading storage data...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {renderStorageOverview()}
      {renderStorageBreakdown()}
      {renderSparkleAnalytics()}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  overviewCard: {
    backgroundColor: '#fff',
    margin: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  chartCard: {
    backgroundColor: '#fff',
    margin: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    alignItems: 'center',
  },
  sparkleCard: {
    backgroundColor: '#fff',
    margin: 16,
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
    borderWidth: 2,
    borderColor: '#ffd700',
  },
  cardTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 16,
    color: '#333',
  },
  usageContainer: {
    marginBottom: 20,
  },
  usageBar: {
    height: 12,
    backgroundColor: '#e9ecef',
    borderRadius: 6,
    marginBottom: 8,
  },
  usageProgress: {
    height: '100%',
    borderRadius: 6,
  },
  usageText: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
  },
  sparkleBadge: {
    backgroundColor: '#ffd700',
    paddingHorizontal: 12,
    paddingVertical: 4,
    borderRadius: 16,
    alignSelf: 'flex-start',
    marginBottom: 16,
  },
  sparkleText: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#333',
  },
  validationStatus: {
    backgroundColor: '#f8f9fa',
    padding: 12,
    borderRadius: 8,
    marginBottom: 16,
  },
  validationTitle: {
    fontSize: 14,
    fontWeight: 'bold',
    marginBottom: 4,
  },
  validationText: {
    fontSize: 12,
    color: '#666',
    marginBottom: 2,
  },
  actionButtons: {
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  actionButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    flex: 0.48,
  },
  dangerButton: {
    backgroundColor: '#ff4757',
  },
  actionButtonText: {
    color: '#fff',
    textAlign: 'center',
    fontWeight: '500',
  },
  emptyText: {
    textAlign: 'center',
    color: '#666',
    marginTop: 20,
  },
  statsGrid: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginBottom: 20,
  },
  statItem: {
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#333',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 4,
  },
  subTitle: {
    fontSize: 16,
    fontWeight: 'bold',
    marginBottom: 12,
    color: '#333',
  },
  fileTypeItem: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 8,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  fileTypeName: {
    fontSize: 14,
    fontWeight: '500',
    flex: 1,
  },
  fileTypeCount: {
    fontSize: 12,
    color: '#666',
    flex: 1,
    textAlign: 'center',
  },
  fileTypeSize: {
    fontSize: 12,
    color: '#666',
    flex: 1,
    textAlign: 'right',
  },
});

export default StorageDashboard;
```

---

## 🔄 **State Management Integration**

### **Redux/Context Setup**

```javascript
// store/fileSlice.js (Redux Toolkit example)
import { createSlice, createAsyncThunk } from '@reduxjs/toolkit';
import FileService from '../services/FileService';

// Async thunks
export const fetchFiles = createAsyncThunk(
  'files/fetchFiles',
  async (filters) => {
    const response = await FileService.getFiles(filters);
    return response;
  }
);

export const toggleFileFavorite = createAsyncThunk(
  'files/toggleFavorite',
  async (fileId) => {
    const response = await FileService.toggleFavorite(fileId);
    return { fileId, ...response };
  }
);

export const toggleFileHidden = createAsyncThunk(
  'files/toggleHidden',
  async (fileId) => {
    const response = await FileService.toggleHidden(fileId);
    return { fileId, ...response };
  }
);

export const lockFile = createAsyncThunk(
  'files/lockFile',
  async ({ fileId, password }) => {
    const response = await FileService.lockFile(fileId, password);
    return { fileId, ...response };
  }
);

const fileSlice = createSlice({
  name: 'files',
  initialState: {
    files: [],
    categories: [],
    counts: {},
    filters: {
      category: 'all',
      showHidden: false,
      favoritesOnly: false,
    },
    loading: false,
    error: null,
  },
  reducers: {
    setFilters: (state, action) => {
      state.filters = { ...state.filters, ...action.payload };
    },
    clearError: (state) => {
      state.error = null;
    },
  },
  extraReducers: (builder) => {
    builder
      // Fetch files
      .addCase(fetchFiles.pending, (state) => {
        state.loading = true;
        state.error = null;
      })
      .addCase(fetchFiles.fulfilled, (state, action) => {
        state.loading = false;
        state.files = action.payload.files;
        state.categories = action.payload.categories;
        state.counts = action.payload.counts;
      })
      .addCase(fetchFiles.rejected, (state, action) => {
        state.loading = false;
        state.error = action.error.message;
      })
      
      // Toggle favorite
      .addCase(toggleFileFavorite.fulfilled, (state, action) => {
        const { fileId, isFavorite } = action.payload;
        const fileIndex = state.files.findIndex(file => file.id === fileId);
        if (fileIndex !== -1) {
          state.files[fileIndex].is_favorite = isFavorite;
        }
      })
      
      // Toggle hidden
      .addCase(toggleFileHidden.fulfilled, (state, action) => {
        const { fileId, isHidden } = action.payload;
        const fileIndex = state.files.findIndex(file => file.id === fileId);
        if (fileIndex !== -1) {
          if (!state.filters.showHidden && isHidden) {
            // Remove from list if hidden and not showing hidden files
            state.files = state.files.filter(file => file.id !== fileId);
          } else {
            state.files[fileIndex].is_hidden = isHidden;
          }
        }
      })
      
      // Lock file
      .addCase(lockFile.fulfilled, (state, action) => {
        const { fileId } = action.payload;
        const fileIndex = state.files.findIndex(file => file.id === fileId);
        if (fileIndex !== -1) {
          state.files[fileIndex].is_locked = true;
        }
      });
  },
});

export const { setFilters, clearError } = fileSlice.actions;
export default fileSlice.reducer;
```

### **React Context Alternative**

```javascript
// contexts/FileContext.jsx
import React, { createContext, useContext, useReducer, useCallback } from 'react';
import FileService from '../services/FileService';

const FileContext = createContext();

const initialState = {
  files: [],
  categories: [],
  counts: {},
  filters: {
    category: 'all',
    showHidden: false,
    favoritesOnly: false,
  },
  loading: false,
  error: null,
};

const fileReducer = (state, action) => {
  switch (action.type) {
    case 'SET_LOADING':
      return { ...state, loading: action.payload };
    case 'SET_ERROR':
      return { ...state, error: action.payload, loading: false };
    case 'SET_FILES':
      return {
        ...state,
        files: action.payload.files,
        categories: action.payload.categories,
        counts: action.payload.counts,
        loading: false,
        error: null,
      };
    case 'SET_FILTERS':
      return { ...state, filters: { ...state.filters, ...action.payload } };
    case 'UPDATE_FILE':
      return {
        ...state,
        files: state.files.map(file =>
          file.id === action.payload.id
            ? { ...file, ...action.payload.updates }
            : file
        ),
      };
    case 'REMOVE_FILE':
      return {
        ...state,
        files: state.files.filter(file => file.id !== action.payload),
      };
    default:
      return state;
  }
};

export const FileProvider = ({ children }) => {
  const [state, dispatch] = useReducer(fileReducer, initialState);

  const loadFiles = useCallback(async (filters = state.filters) => {
    dispatch({ type: 'SET_LOADING', payload: true });
    try {
      const data = await FileService.getFiles(filters);
      dispatch({ type: 'SET_FILES', payload: data });
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
    }
  }, [state.filters]);

  const toggleFavorite = useCallback(async (fileId) => {
    try {
      const result = await FileService.toggleFavorite(fileId);
      dispatch({
        type: 'UPDATE_FILE',
        payload: {
          id: fileId,
          updates: { is_favorite: result.isFavorite },
        },
      });
      return result;
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
      throw error;
    }
  }, []);

  const toggleHidden = useCallback(async (fileId) => {
    try {
      const result = await FileService.toggleHidden(fileId);
      
      if (!state.filters.showHidden && result.isHidden) {
        dispatch({ type: 'REMOVE_FILE', payload: fileId });
      } else {
        dispatch({
          type: 'UPDATE_FILE',
          payload: {
            id: fileId,
            updates: { is_hidden: result.isHidden },
          },
        });
      }
      return result;
    } catch (error) {
      dispatch({ type: 'SET_ERROR', payload: error.message });
      throw error;
    }
  }, [state.filters.showHidden]);

  const setFilters = useCallback((newFilters) => {
    dispatch({ type: 'SET_FILTERS', payload: newFilters });
  }, []);

  const value = {
    ...state,
    loadFiles,
    toggleFavorite,
    toggleHidden,
    setFilters,
  };

  return (
    <FileContext.Provider value={value}>
      {children}
    </FileContext.Provider>
  );
};

export const useFiles = () => {
  const context = useContext(FileContext);
  if (!context) {
    throw new Error('useFiles must be used within a FileProvider');
  }
  return context;
};
```

---

## 🧪 **Testing Examples**

### **Service Layer Tests**

```javascript
// __tests__/FileService.test.js
import FileService from '../services/FileService';

// Mock fetch
global.fetch = jest.fn();

describe('FileService', () => {
  beforeEach(() => {
    fetch.mockClear();
  });

  describe('toggleFavorite', () => {
    it('should toggle favorite status successfully', async () => {
      const mockResponse = {
        success: true,
        is_favorite: true,
        message: 'File added to favorites',
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      const result = await FileService.toggleFavorite(123);

      expect(fetch).toHaveBeenCalledWith(
        expect.stringContaining('/api/files/123/toggle-favorite/'),
        expect.objectContaining({
          method: 'POST',
          headers: expect.objectContaining({
            'Authorization': expect.stringContaining('Bearer'),
          }),
        })
      );

      expect(result).toEqual({
        isFavorite: true,
        message: 'File added to favorites',
      });
    });

    it('should handle API errors', async () => {
      const mockResponse = {
        success: false,
        error: 'File not found',
      };

      fetch.mockResolvedValueOnce({
        ok: true,
        json: async () => mockResponse,
      });

      await expect(FileService.toggleFavorite(999)).rejects.toThrow('File not found');
    });
  });

  describe('lockFile', () => {
    it('should validate password before making API call', async () => {
      await expect(FileService.lockFile(123, 'weak')).rejects.toThrow(
        'Password must be at least 6 characters long'
      );

      expect(fetch).not.toHaveBeenCalled();
    });

    it('should handle password validation errors from API', async () => {
      const mockResponse = {
        success: false,
        errors: {
          password: ['Password must contain at least one digit'],
        },
      };

      fetch.mockResolvedValueOnce({
        ok: false,
        status: 400,
        json: async () => mockResponse,
      });

      await expect(FileService.lockFile(123, 'password')).rejects.toThrow(
        'Password must contain at least one digit'
      );
    });
  });
});
```

### **Component Tests**

```javascript
// __tests__/FileList.test.jsx
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import FileList from '../components/FileList';
import FileService from '../services/FileService';

// Mock the service
jest.mock('../services/FileService');

describe('FileList', () => {
  const mockFiles = [
    {
      id: 1,
      original_filename: 'test.pdf',
      is_favorite: false,
      is_hidden: false,
      is_locked: false,
      file_size_display: '1.2 MB',
      category: { name: 'Documents' },
    },
  ];

  beforeEach(() => {
    FileService.getFiles.mockResolvedValue({
      files: mockFiles,
      categories: [],
      counts: { favorites: 0, hidden: 0 },
    });
  });

  it('should render file list', async () => {
    const { getByText } = render(<FileList />);

    await waitFor(() => {
      expect(getByText('test.pdf')).toBeTruthy();
      expect(getByText('1.2 MB')).toBeTruthy();
      expect(getByText('Documents')).toBeTruthy();
    });
  });

  it('should toggle favorite when favorite button is pressed', async () => {
    FileService.toggleFavorite.mockResolvedValue({
      isFavorite: true,
      message: 'Added to favorites',
    });

    const { getByTestId } = render(<FileList />);

    await waitFor(() => {
      const favoriteButton = getByTestId('favorite-button-1');
      fireEvent.press(favoriteButton);
    });

    expect(FileService.toggleFavorite).toHaveBeenCalledWith(1);
  });
});
```

---

## 📱 **Navigation Setup**

```javascript
// navigation/AppNavigator.jsx
import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { createBottomTabNavigator } from '@react-navigation/bottom-tabs';
import Icon from 'react-native-vector-icons/MaterialIcons';

// Import screens
import FileList from '../components/FileList';
import { LockFile, UnlockFile } from '../components/LockFile';
import StorageDashboard from '../components/StorageDashboard';
import FileViewer from '../components/FileViewer';

const Stack = createStackNavigator();
const Tab = createBottomTabNavigator();

const FileStack = () => (
  <Stack.Navigator>
    <Stack.Screen 
      name="FileList" 
      component={FileList} 
      options={{ title: 'My Files' }}
    />
    <Stack.Screen 
      name="LockFile" 
      component={LockFile} 
      options={{ title: 'Lock File' }}
    />
    <Stack.Screen 
      name="UnlockFile" 
      component={UnlockFile} 
      options={{ title: 'Access File' }}
    />
    <Stack.Screen 
      name="FileViewer" 
      component={FileViewer} 
      options={{ title: 'View File' }}
    />
  </Stack.Navigator>
);

const AppNavigator = () => (
  <Tab.Navigator
    screenOptions={({ route }) => ({
      tabBarIcon: ({ focused, color, size }) => {
        let iconName;

        if (route.name === 'Files') {
          iconName = 'folder';
        } else if (route.name === 'Storage') {
          iconName = 'storage';
        }

        return <Icon name={iconName} size={size} color={color} />;
      },
    })}
  >
    <Tab.Screen name="Files" component={FileStack} />
    <Tab.Screen name="Storage" component={StorageDashboard} />
  </Tab.Navigator>
);

export default AppNavigator;
```

---

## 🔧 **Configuration & Constants**

```javascript
// config/api.js
export const API_CONFIG = {
  BASE_URL: __DEV__ 
    ? 'http://localhost:8000/file_management' 
    : 'https://your-production-api.com/file_management',
  
  STORAGE_BASE_URL: __DEV__
    ? 'http://localhost:8000/storage_management'
    : 'https://your-production-api.com/storage_management',

  ENDPOINTS: {
    // File Management
    FILES: '/api/mobile/files/',
    UPLOAD: '/api/mobile/upload/',
    TOGGLE_FAVORITE: '/api/files/{id}/toggle-favorite/',
    TOGGLE_HIDDEN: '/api/files/{id}/toggle-hidden/',
    LOCK_FILE: '/api/files/{id}/lock/',
    UNLOCK_FILE: '/api/files/{id}/unlock/',
    ACCESS_LOCKED: '/api/files/{id}/access-locked/',
    
    // Storage Management
    STORAGE_INFO: '/api/storage/',
    STORAGE_ANALYTICS: '/api/storage/analytics/',
    RECALCULATE_STORAGE: '/api/storage/recalculate/',
    CLEAN_ORPHANS: '/api/storage/clean_orphans/',
  },

  TIMEOUTS: {
    DEFAULT: 30000, // 30 seconds
    UPLOAD: 120000, // 2 minutes for file uploads
  },
};

// constants/fileTypes.js
export const FILE_TYPES = {
  DOCUMENT: 'document',
  IMAGE: 'image',
  AUDIO: 'audio',
};

export const SUPPORTED_MIME_TYPES = {
  [FILE_TYPES.DOCUMENT]: [
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
  ],
  [FILE_TYPES.IMAGE]: [
    'image/jpeg',
    'image/png',
    'image/gif',
    'image/webp',
  ],
  [FILE_TYPES.AUDIO]: [
    'audio/mpeg',
    'audio/wav',
    'audio/mp4',
  ],
};

export const PASSWORD_REQUIREMENTS = {
  MIN_LENGTH: 6,
  REQUIRE_DIGIT: true,
  REQUIRE_LETTER: true,
};
```

---

## 📋 **Implementation Checklist**

### **Backend Integration ✅**
- [x] Update API service classes with new endpoints
- [x] Implement file feature management (favorite, hidden, lock)
- [x] Add storage management and analytics
- [x] Set up proper error handling and validation
- [x] Configure state management (Redux/Context)

### **UI Components ✅**
- [x] Enhanced file list with feature buttons
- [x] Lock/unlock file modals with password validation
- [x] Storage dashboard with analytics
- [x] Filter and search functionality
- [x] Loading states and error handling

### **Testing 🔄**
- [ ] Unit tests for service classes
- [ ] Component integration tests
- [ ] E2E testing for critical flows
- [ ] Password validation testing
- [ ] Storage calculation accuracy tests

### **Performance 🔄**
- [ ] Implement proper caching strategies
- [ ] Add offline support for file metadata
- [ ] Optimize large file list rendering
- [ ] Background storage sync

### **Security 🔄**
- [ ] Secure token storage and refresh
- [ ] Validate file access permissions
- [ ] Implement secure file preview
- [ ] Add biometric authentication for locked files

---

This comprehensive guide provides everything your frontend team needs to integrate all the enhanced file management and storage features. The implementation covers API integration, state management, UI components, testing, and security considerations specific to React Native development.