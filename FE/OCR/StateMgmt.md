# Frontend State Management Guide for OCR System

## Table of Contents
1. [Overview](#overview)
2. [State Architecture](#state-architecture)
3. [Context API Setup](#context-api-setup)
4. [Custom Hooks](#custom-hooks)
5. [Component Integration](#component-integration)
6. [Data Flow Patterns](#data-flow-patterns)
7. [Performance Optimization](#performance-optimization)
8. [Error Handling](#error-handling)
9. [Testing Strategies](#testing-strategies)
10. [Best Practices](#best-practices)

## Overview

This guide provides a comprehensive approach to state management for the OCR document management system using React Native. The architecture combines React Context API, custom hooks, and local component state to create a scalable and maintainable solution.

### Why This Architecture?

- **Centralized OCR State**: Global state for files, categories, and processing status
- **Component Isolation**: Local state for UI-specific concerns
- **Performance**: Optimized re-renders and data fetching
- **Scalability**: Easy to extend with new features
- **Testability**: Clear separation of concerns

## State Architecture

### State Layers

```
┌─────────────────────────────────────────┐
│              Global State               │
│  (OCRContext + AsyncStorage)           │
├─────────────────────────────────────────┤
│              Hook Layer                 │
│     (useOCR, useFileUpload, etc.)      │
├─────────────────────────────────────────┤
│            Component State              │
│    (Local UI state, forms, etc.)       │
└─────────────────────────────────────────┘
```

### Global State Structure

```javascript
// Global OCR State Shape
{
  // Core Data
  files: Array<File>,
  categories: Array<Category>,
  ocrPreferences: OCRPreferences,
  
  // UI State
  loading: boolean,
  uploading: boolean,
  searchQuery: string,
  selectedCategory: string,
  
  // Processing State
  uploadQueue: Array<UploadItem>,
  processingFiles: Set<fileId>,
  pollingJobs: Map<fileId, intervalId>,
  
  // Cache
  fileCache: Map<fileId, File>,
  ocrResultsCache: Map<fileId, OCRResult>,
  
  // Statistics
  stats: {
    total: number,
    processed: number,
    processing: number,
    failed: number,
    successRate: number
  }
}
```

## Context API Setup

### 1. OCR Context Provider

```javascript
// context/OCRContext.js
import React, { createContext, useContext, useReducer, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import OCRService from '../services/ocrService';

const OCRContext = createContext();

// Initial State
const initialState = {
  // Core data
  files: [],
  categories: [],
  ocrPreferences: null,
  
  // UI state
  loading: false,
  uploading: false,
  searchQuery: '',
  selectedCategory: null,
  
  // Processing state
  uploadQueue: [],
  processingFiles: new Set(),
  pollingJobs: new Map(),
  
  // Cache
  fileCache: new Map(),
  ocrResultsCache: new Map(),
  
  // Stats
  stats: {
    total: 0,
    processed: 0,
    processing: 0,
    failed: 0,
    successRate: 0
  },
  
  // Error state
  error: null,
  networkStatus: 'online'
};

// Action Types
const ActionTypes = {
  // Data actions
  SET_FILES: 'SET_FILES',
  ADD_FILE: 'ADD_FILE',
  UPDATE_FILE: 'UPDATE_FILE',
  REMOVE_FILE: 'REMOVE_FILE',
  SET_CATEGORIES: 'SET_CATEGORIES',
  SET_OCR_PREFERENCES: 'SET_OCR_PREFERENCES',
  
  // UI actions
  SET_LOADING: 'SET_LOADING',
  SET_UPLOADING: 'SET_UPLOADING',
  SET_SEARCH_QUERY: 'SET_SEARCH_QUERY',
  SET_SELECTED_CATEGORY: 'SET_SELECTED_CATEGORY',
  
  // Processing actions
  ADD_TO_UPLOAD_QUEUE: 'ADD_TO_UPLOAD_QUEUE',
  REMOVE_FROM_UPLOAD_QUEUE: 'REMOVE_FROM_UPLOAD_QUEUE',
  ADD_PROCESSING_FILE: 'ADD_PROCESSING_FILE',
  REMOVE_PROCESSING_FILE: 'REMOVE_PROCESSING_FILE',
  SET_POLLING_JOB: 'SET_POLLING_JOB',
  CLEAR_POLLING_JOB: 'CLEAR_POLLING_JOB',
  
  // Cache actions
  CACHE_FILE: 'CACHE_FILE',
  CACHE_OCR_RESULT: 'CACHE_OCR_RESULT',
  CLEAR_CACHE: 'CLEAR_CACHE',
  
  // Error actions
  SET_ERROR: 'SET_ERROR',
  CLEAR_ERROR: 'CLEAR_ERROR',
  SET_NETWORK_STATUS: 'SET_NETWORK_STATUS',
  
  // Batch actions
  BATCH_UPDATE: 'BATCH_UPDATE',
  RESET_STATE: 'RESET_STATE'
};

// Reducer
const ocrReducer = (state, action) => {
  switch (action.type) {
    case ActionTypes.SET_FILES:
      return {
        ...state,
        files: action.payload,
        stats: calculateStats(action.payload)
      };
    
    case ActionTypes.ADD_FILE:
      const newFiles = [action.payload, ...state.files];
      return {
        ...state,
        files: newFiles,
        stats: calculateStats(newFiles)
      };
    
    case ActionTypes.UPDATE_FILE:
      const updatedFiles = state.files.map(file => 
        file.id === action.payload.id 
          ? { ...file, ...action.payload }
          : file
      );
      return {
        ...state,
        files: updatedFiles,
        stats: calculateStats(updatedFiles)
      };
    
    case ActionTypes.REMOVE_FILE:
      const filteredFiles = state.files.filter(file => file.id !== action.payload);
      return {
        ...state,
        files: filteredFiles,
        stats: calculateStats(filteredFiles)
      };
    
    case ActionTypes.SET_CATEGORIES:
      return { ...state, categories: action.payload };
    
    case ActionTypes.SET_OCR_PREFERENCES:
      return { ...state, ocrPreferences: action.payload };
    
    case ActionTypes.SET_LOADING:
      return { ...state, loading: action.payload };
    
    case ActionTypes.SET_UPLOADING:
      return { ...state, uploading: action.payload };
    
    case ActionTypes.SET_SEARCH_QUERY:
      return { ...state, searchQuery: action.payload };
    
    case ActionTypes.SET_SELECTED_CATEGORY:
      return { ...state, selectedCategory: action.payload };
    
    case ActionTypes.ADD_TO_UPLOAD_QUEUE:
      return {
        ...state,
        uploadQueue: [...state.uploadQueue, action.payload]
      };
    
    case ActionTypes.REMOVE_FROM_UPLOAD_QUEUE:
      return {
        ...state,
        uploadQueue: state.uploadQueue.filter(item => item.id !== action.payload)
      };
    
    case ActionTypes.ADD_PROCESSING_FILE:
      return {
        ...state,
        processingFiles: new Set([...state.processingFiles, action.payload])
      };
    
    case ActionTypes.REMOVE_PROCESSING_FILE:
      const newProcessingFiles = new Set(state.processingFiles);
      newProcessingFiles.delete(action.payload);
      return { ...state, processingFiles: newProcessingFiles };
    
    case ActionTypes.SET_POLLING_JOB:
      return {
        ...state,
        pollingJobs: new Map(state.pollingJobs).set(action.payload.fileId, action.payload.intervalId)
      };
    
    case ActionTypes.CLEAR_POLLING_JOB:
      const newPollingJobs = new Map(state.pollingJobs);
      newPollingJobs.delete(action.payload);
      return { ...state, pollingJobs: newPollingJobs };
    
    case ActionTypes.CACHE_FILE:
      return {
        ...state,
        fileCache: new Map(state.fileCache).set(action.payload.id, action.payload)
      };
    
    case ActionTypes.CACHE_OCR_RESULT:
      return {
        ...state,
        ocrResultsCache: new Map(state.ocrResultsCache).set(action.payload.fileId, action.payload.result)
      };
    
    case ActionTypes.CLEAR_CACHE:
      return {
        ...state,
        fileCache: new Map(),
        ocrResultsCache: new Map()
      };
    
    case ActionTypes.SET_ERROR:
      return { ...state, error: action.payload };
    
    case ActionTypes.CLEAR_ERROR:
      return { ...state, error: null };
    
    case ActionTypes.SET_NETWORK_STATUS:
      return { ...state, networkStatus: action.payload };
    
    case ActionTypes.BATCH_UPDATE:
      return { ...state, ...action.payload };
    
    case ActionTypes.RESET_STATE:
      return { ...initialState, networkStatus: state.networkStatus };
    
    default:
      return state;
  }
};

// Helper function to calculate stats
const calculateStats = (files) => {
  const total = files.length;
  const processed = files.filter(f => f.ocr_status === 'completed').length;
  const processing = files.filter(f => f.ocr_status === 'processing').length;
  const failed = files.filter(f => f.ocr_status === 'failed').length;
  const successRate = total > 0 ? (processed / total) * 100 : 0;
  
  return { total, processed, processing, failed, successRate };
};

// Provider Component
export const OCRProvider = ({ children }) => {
  const [state, dispatch] = useReducer(ocrReducer, initialState);

  // Persistence
  useEffect(() => {
    loadPersistedState();
  }, []);

  useEffect(() => {
    persistState(state);
  }, [state.files, state.categories, state.ocrPreferences]);

  const loadPersistedState = async () => {
    try {
      const persistedData = await AsyncStorage.getItem('ocrState');
      if (persistedData) {
        const { files, categories, ocrPreferences } = JSON.parse(persistedData);
        dispatch({ type: ActionTypes.BATCH_UPDATE, payload: { files, categories, ocrPreferences } });
      }
    } catch (error) {
      console.error('Failed to load persisted state:', error);
    }
  };

  const persistState = async (state) => {
    try {
      const dataToSave = {
        files: state.files,
        categories: state.categories,
        ocrPreferences: state.ocrPreferences
      };
      await AsyncStorage.setItem('ocrState', JSON.stringify(dataToSave));
    } catch (error) {
      console.error('Failed to persist state:', error);
    }
  };

  // Network status monitoring
  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(state => {
      dispatch({
        type: ActionTypes.SET_NETWORK_STATUS,
        payload: state.isConnected ? 'online' : 'offline'
      });
    });

    return unsubscribe;
  }, []);

  const value = {
    state,
    dispatch,
    ActionTypes
  };

  return <OCRContext.Provider value={value}>{children}</OCRContext.Provider>;
};

export const useOCRContext = () => {
  const context = useContext(OCRContext);
  if (!context) {
    throw new Error('useOCRContext must be used within an OCRProvider');
  }
  return context;
};
```

### 2. Action Creators

```javascript
// actions/ocrActions.js
export const ocrActions = {
  // File actions
  setFiles: (files) => ({ type: 'SET_FILES', payload: files }),
  addFile: (file) => ({ type: 'ADD_FILE', payload: file }),
  updateFile: (file) => ({ type: 'UPDATE_FILE', payload: file }),
  removeFile: (fileId) => ({ type: 'REMOVE_FILE', payload: fileId }),
  
  // UI actions
  setLoading: (loading) => ({ type: 'SET_LOADING', payload: loading }),
  setUploading: (uploading) => ({ type: 'SET_UPLOADING', payload: uploading }),
  setSearchQuery: (query) => ({ type: 'SET_SEARCH_QUERY', payload: query }),
  setSelectedCategory: (category) => ({ type: 'SET_SELECTED_CATEGORY', payload: category }),
  
  // Processing actions
  addProcessingFile: (fileId) => ({ type: 'ADD_PROCESSING_FILE', payload: fileId }),
  removeProcessingFile: (fileId) => ({ type: 'REMOVE_PROCESSING_FILE', payload: fileId }),
  
  // Error actions
  setError: (error) => ({ type: 'SET_ERROR', payload: error }),
  clearError: () => ({ type: 'CLEAR_ERROR' }),
  
  // Cache actions
  cacheFile: (file) => ({ type: 'CACHE_FILE', payload: file }),
  cacheOCRResult: (fileId, result) => ({ 
    type: 'CACHE_OCR_RESULT', 
    payload: { fileId, result } 
  }),
};
```

## Custom Hooks

### 1. useOCR Hook

```javascript
// hooks/useOCR.js
import { useCallback, useEffect } from 'react';
import { useOCRContext } from '../context/OCRContext';
import { ocrActions } from '../actions/ocrActions';
import OCRService from '../services/ocrService';

export const useOCR = () => {
  const { state, dispatch } = useOCRContext();

  // Load files
  const loadFiles = useCallback(async (options = {}) => {
    const { category, search, refresh = false } = options;
    
    try {
      dispatch(ocrActions.setLoading(true));
      
      // Check cache first
      if (!refresh && state.files.length > 0 && !category && !search) {
        return state.files;
      }
      
      const response = await OCRService.getFiles(category, search);
      
      if (response.files) {
        dispatch(ocrActions.setFiles(response.files));
        
        // Cache individual files
        response.files.forEach(file => {
          dispatch(ocrActions.cacheFile(file));
        });
      }
      
      if (response.categories) {
        dispatch({ type: 'SET_CATEGORIES', payload: response.categories });
      }
      
      return response.files || [];
    } catch (error) {
      dispatch(ocrActions.setError(error.message));
      throw error;
    } finally {
      dispatch(ocrActions.setLoading(false));
    }
  }, [state.files.length, dispatch]);

  // Upload file
  const uploadFile = useCallback(async (fileData, fileType, categoryId = null) => {
    try {
      dispatch(ocrActions.setUploading(true));
      
      // Add to upload queue
      const queueItem = {
        id: Date.now(),
        fileData,
        fileType,
        categoryId,
        status: 'uploading'
      };
      dispatch({ type: 'ADD_TO_UPLOAD_QUEUE', payload: queueItem });
      
      const response = await OCRService.uploadFile(fileData, fileType, categoryId);
      
      if (response.success) {
        // Add file to state
        dispatch(ocrActions.addFile(response.file));
        
        // Cache file
        dispatch(ocrActions.cacheFile(response.file));
        
        // Start OCR polling if needed
        if (response.ocr_result?.status === 'processing') {
          startOCRPolling(response.file.id);
        }
        
        // Remove from upload queue
        dispatch({ type: 'REMOVE_FROM_UPLOAD_QUEUE', payload: queueItem.id });
      }
      
      return response;
    } catch (error) {
      dispatch(ocrActions.setError(error.message));
      throw error;
    } finally {
      dispatch(ocrActions.setUploading(false));
    }
  }, [dispatch]);

  // Start OCR polling
  const startOCRPolling = useCallback((fileId) => {
    // Clear existing polling job
    if (state.pollingJobs.has(fileId)) {
      clearInterval(state.pollingJobs.get(fileId));
    }
    
    dispatch(ocrActions.addProcessingFile(fileId));
    
    const intervalId = setInterval(async () => {
      try {
        const response = await OCRService.getOCRStatus(fileId);
        
        if (response.success) {
          // Update file in state
          const updatedFile = {
            id: fileId,
            ocr_status: response.ocr_status,
            ocr_text: response.ocr_text
          };
          dispatch(ocrActions.updateFile(updatedFile));
          
          // Cache OCR result
          dispatch(ocrActions.cacheOCRResult(fileId, response));
          
          // Stop polling if completed or failed
          if (response.ocr_status === 'completed' || response.ocr_status === 'failed') {
            clearInterval(intervalId);
            dispatch({ type: 'CLEAR_POLLING_JOB', payload: fileId });
            dispatch(ocrActions.removeProcessingFile(fileId));
          }
        }
      } catch (error) {
        console.error('OCR polling error:', error);
        clearInterval(intervalId);
        dispatch({ type: 'CLEAR_POLLING_JOB', payload: fileId });
        dispatch(ocrActions.removeProcessingFile(fileId));
      }
    }, 5000);
    
    dispatch({ type: 'SET_POLLING_JOB', payload: { fileId, intervalId } });
  }, [state.pollingJobs, dispatch]);

  // Stop OCR polling
  const stopOCRPolling = useCallback((fileId) => {
    if (state.pollingJobs.has(fileId)) {
      clearInterval(state.pollingJobs.get(fileId));
      dispatch({ type: 'CLEAR_POLLING_JOB', payload: fileId });
      dispatch(ocrActions.removeProcessingFile(fileId));
    }
  }, [state.pollingJobs, dispatch]);

  // Process OCR manually
  const processOCR = useCallback(async (fileId) => {
    try {
      const response = await OCRService.processOCR(fileId);
      
      if (response.success) {
        // Update file status
        dispatch(ocrActions.updateFile({ id: fileId, ocr_status: 'processing' }));
        
        // Start polling
        startOCRPolling(fileId);
      }
      
      return response;
    } catch (error) {
      dispatch(ocrActions.setError(error.message));
      throw error;
    }
  }, [startOCRPolling, dispatch]);

  // Get file by ID
  const getFile = useCallback((fileId) => {
    // Check cache first
    if (state.fileCache.has(fileId)) {
      return state.fileCache.get(fileId);
    }
    
    // Look in files array
    return state.files.find(file => file.id === fileId);
  }, [state.fileCache, state.files]);

  // Search files
  const searchFiles = useCallback((query) => {
    dispatch(ocrActions.setSearchQuery(query));
    return loadFiles({ search: query });
  }, [loadFiles, dispatch]);

  // Filter by category
  const filterByCategory = useCallback((category) => {
    dispatch(ocrActions.setSelectedCategory(category));
    return loadFiles({ category });
  }, [loadFiles, dispatch]);

  // Cleanup polling on unmount
  useEffect(() => {
    return () => {
      state.pollingJobs.forEach((intervalId) => {
        clearInterval(intervalId);
      });
    };
  }, [state.pollingJobs]);

  return {
    // State
    files: state.files,
    categories: state.categories,
    loading: state.loading,
    uploading: state.uploading,
    searchQuery: state.searchQuery,
    selectedCategory: state.selectedCategory,
    processingFiles: state.processingFiles,
    stats: state.stats,
    error: state.error,
    networkStatus: state.networkStatus,
    
    // Actions
    loadFiles,
    uploadFile,
    processOCR,
    getFile,
    searchFiles,
    filterByCategory,
    startOCRPolling,
    stopOCRPolling,
    
    // Utilities
    clearError: () => dispatch(ocrActions.clearError()),
    refreshFiles: () => loadFiles({ refresh: true }),
  };
};
```

### 2. useFileUpload Hook

```javascript
// hooks/useFileUpload.js
import { useState, useCallback } from 'react';
import { useOCR } from './useOCR';
import DocumentPicker from 'react-native-document-picker';
import { launchImageLibrary, launchCamera } from 'react-native-image-picker';

export const useFileUpload = () => {
  const [uploadProgress, setUploadProgress] = useState({});
  const { uploadFile, uploading } = useOCR();

  const uploadDocument = useCallback(async (categoryId = null) => {
    try {
      const result = await DocumentPicker.pickSingle({
        type: [DocumentPicker.types.pdf, DocumentPicker.types.doc, DocumentPicker.types.docx],
        copyTo: 'cachesDirectory',
      });

      const uploadId = Date.now();
      setUploadProgress(prev => ({
        ...prev,
        [uploadId]: { status: 'uploading', progress: 0 }
      }));

      const response = await uploadFile(result, 'document', categoryId);
      
      setUploadProgress(prev => ({
        ...prev,
        [uploadId]: { status: 'completed', progress: 100 }
      }));

      return response;
    } catch (error) {
      if (!DocumentPicker.isCancel(error)) {
        throw error;
      }
    }
  }, [uploadFile]);

  const uploadFromCamera = useCallback(async (categoryId = null) => {
    return new Promise((resolve, reject) => {
      const options = {
        mediaType: 'photo',
        quality: 0.8,
        includeBase64: false,
      };

      launchCamera(options, async (response) => {
        if (response.assets && response.assets[0]) {
          try {
            const asset = response.assets[0];
            const fileData = {
              uri: asset.uri,
              type: asset.type,
              name: asset.fileName || 'camera_image.jpg',
            };

            const uploadId = Date.now();
            setUploadProgress(prev => ({
              ...prev,
              [uploadId]: { status: 'uploading', progress: 0 }
            }));

            const result = await uploadFile(fileData, 'image', categoryId);
            
            setUploadProgress(prev => ({
              ...prev,
              [uploadId]: { status: 'completed', progress: 100 }
            }));

            resolve(result);
          } catch (error) {
            reject(error);
          }
        } else {
          resolve(null);
        }
      });
    });
  }, [uploadFile]);

  const uploadFromGallery = useCallback(async (categoryId = null) => {
    return new Promise((resolve, reject) => {
      const options = {
        mediaType: 'photo',
        quality: 0.8,
        includeBase64: false,
      };

      launchImageLibrary(options, async (response) => {
        if (response.assets && response.assets[0]) {
          try {
            const asset = response.assets[0];
            const fileData = {
              uri: asset.uri,
              type: asset.type,
              name: asset.fileName || 'gallery_image.jpg',
            };

            const uploadId = Date.now();
            setUploadProgress(prev => ({
              ...prev,
              [uploadId]: { status: 'uploading', progress: 0 }
            }));

            const result = await uploadFile(fileData, 'image', categoryId);
            
            setUploadProgress(prev => ({
              ...prev,
              [uploadId]: { status: 'completed', progress: 100 }
            }));

            resolve(result);
          } catch (error) {
            reject(error);
          }
        } else {
          resolve(null);
        }
      });
    });
  }, [uploadFile]);

  const clearProgress = useCallback((uploadId) => {
    setUploadProgress(prev => {
      const newProgress = { ...prev };
      delete newProgress[uploadId];
      return newProgress;
    });
  }, []);

  return {
    uploadDocument,
    uploadFromCamera,
    uploadFromGallery,
    uploadProgress,
    uploading,
    clearProgress,
  };
};
```

### 3. useOCRPreferences Hook

```javascript
// hooks/useOCRPreferences.js
import { useState, useEffect, useCallback } from 'react';
import { useOCRContext } from '../context/OCRContext';
import OCRService from '../services/ocrService';

export const useOCRPreferences = () => {
  const { state, dispatch } = useOCRContext();
  const [loading, setLoading] = useState(false);
  const [saving, setSaving] = useState(false);

  // Load preferences on mount
  useEffect(() => {
    if (!state.ocrPreferences) {
      loadPreferences();
    }
  }, [state.ocrPreferences]);

  const loadPreferences = useCallback(async () => {
    try {
      setLoading(true);
      const response = await OCRService.getOCRPreferences();
      if (response.success) {
        dispatch({ type: 'SET_OCR_PREFERENCES', payload: response });
      }
    } catch (error) {
      console.error('Failed to load OCR preferences:', error);
    } finally {
      setLoading(false);
    }
  }, [dispatch]);

  const updatePreferences = useCallback(async (preference) => {
    try {
      setSaving(true);
      const response = await OCRService.updateOCRPreferences(preference);
      if (response.success) {
        dispatch({ type: 'SET_OCR_PREFERENCES', payload: response });
      }
      return response;
    } catch (error) {
      console.error('Failed to update OCR preferences:', error);
      throw error;
    } finally {
      setSaving(false);
    }
  }, [dispatch]);

  return {
    preferences: state.ocrPreferences,
    loading,
    saving,
    loadPreferences,
    updatePreferences,
  };
};
```

## Component Integration

### 1. Provider Setup

```javascript
// App.js
import React from 'react';
import { NavigationContainer } from '@react-navigation/native';
import { OCRProvider } from './context/OCRContext';
import { ErrorBoundary } from './components/ErrorBoundary';
import AppNavigator from './navigation/AppNavigator';

export default function App() {
  return (
    <ErrorBoundary>
      <OCRProvider>
        <NavigationContainer>
          <AppNavigator />
        </NavigationContainer>
      </OCRProvider>
    </ErrorBoundary>
  );
}
```

### 2. Component State Integration

```javascript
// components/FilesList.js
import React, { useEffect, useState } from 'react';
import { useOCR } from '../hooks/useOCR';

const FilesList = ({ navigation }) => {
  // Global state from OCR hook
  const {
    files,
    categories,
    loading,
    searchQuery,
    selectedCategory,
    stats,
    error,
    loadFiles,
    searchFiles,
    filterByCategory,
    clearError,
  } = useOCR();

  // Local component state
  const [refreshing, setRefreshing] = useState(false);
  const [showCategoryModal, setShowCategoryModal] = useState(false);

  // Load files on mount
  useEffect(() => {
    loadFiles();
  }, []);

  // Handle refresh
  const onRefresh = async () => {
    setRefreshing(true);
    try {
      await loadFiles({ refresh: true });
    } catch (error) {
      // Error is handled by global state
    } finally {
      setRefreshing(false);
    }
  };

  // Handle search
  const handleSearch = (query) => {
    searchFiles(query);
  };

  // Handle category filter
  const handleCategoryFilter = (category) => {
    filterByCategory(category);
    setShowCategoryModal(false);
  };

  // Error handling
  useEffect(() => {
    if (error) {
      Alert.alert('Error', error, [
        { text: 'OK', onPress: clearError }
      ]);
    }
  }, [error, clearError]);

  // Render component...
};
```

## Data Flow Patterns

### 1. Upload Flow

```
User Action → Component → Hook → Service → API
     ↓           ↓        ↓       ↓      ↓
 onUpload → uploadFile → OCRService → Backend
                ↓
         Update Global State
                ↓
         Start OCR Polling
                ↓
         Update UI Components
```

### 2. OCR Processing Flow

```
File Upload → OCR Status: processing
     ↓
Start Polling (useOCR hook)
     ↓
Poll API every 5 seconds
     ↓
Update Global State
     ↓
Components Re-render
     ↓
OCR Complete → Stop Polling
```

### 3. Search and Filter Flow

```
User Input → Update Local State → Dispatch Action
     ↓              ↓                ↓
Search Query → Component State → Global State
     ↓              ↓                ↓
API Call → Update Files → Re-render Components
```

## Performance Optimization

### 1. Memoization

```javascript
// hooks/useOCRMemo.js
import { useMemo } from 'react';
import { useOCR } from './useOCR';

export const useOCRMemo = () => {
  const ocrData = useOCR();

  const memoizedData = useMemo(() => ({
    // Memoize expensive calculations
    filesByCategory: ocrData.files.reduce((acc, file) => {
      const category = file.category || 'Uncategorized';
      if (!acc[category]) acc[category] = [];
      acc[category].push(file);
      return acc;
    }, {}),

    // Memoize filtered files
    filteredFiles: ocrData.files.filter(file => {
      const matchesSearch = !ocrData.searchQuery || 
        file.original_filename?.toLowerCase().includes(ocrData.searchQuery.toLowerCase()) ||
        file.ocr_text?.toLowerCase().includes(ocrData.searchQuery.toLowerCase());
      
      const matchesCategory = !ocrData.selectedCategory || 
        file.category === ocrData.selectedCategory;
      
      return matchesSearch && matchesCategory;
    }),

    // Memoize processing statistics
    processingStats: {
      ...ocrData.stats,
      processingRate: ocrData.processingFiles.size,
      completionRate: ocrData.stats.total > 0 ? 
        (ocrData.stats.processed / ocrData.stats.total) * 100 : 0
    },

    // Memoize recent files
    recentFiles: ocrData.files
      .sort((a, b) => new Date(b.upload_date) - new Date(a.upload_date))
      .slice(0, 10),

    // Memoize files by status
    filesByStatus: {
      completed: ocrData.files.filter(f => f.ocr_status === 'completed'),
      processing: ocrData.files.filter(f => f.ocr_status === 'processing'),
      failed: ocrData.files.filter(f => f.ocr_status === 'failed'),
      pending: ocrData.files.filter(f => f.ocr_status === 'not_started')
    }
  }), [
    ocrData.files,
    ocrData.searchQuery,
    ocrData.selectedCategory,
    ocrData.stats,
    ocrData.processingFiles.size
  ]);

  return {
    ...ocrData,
    ...memoizedData
  };
};
```

### 2. Component Optimization

```javascript
// components/OptimizedFileItem.js
import React, { memo } from 'react';
import { areEqual } from '../utils/componentUtils';

const FileItem = memo(({ file, onPress, onLongPress }) => {
  // Component implementation
  return (
    <TouchableOpacity onPress={() => onPress(file.id)}>
      {/* File item content */}
    </TouchableOpacity>
  );
}, areEqual);

// utils/componentUtils.js
export const areEqual = (prevProps, nextProps) => {
  // Custom comparison for file items
  return (
    prevProps.file.id === nextProps.file.id &&
    prevProps.file.ocr_status === nextProps.file.ocr_status &&
    prevProps.file.ocr_text === nextProps.file.ocr_text &&
    prevProps.file.category === nextProps.file.category
  );
};
```

### 3. Virtualization

```javascript
// components/VirtualizedFileList.js
import React from 'react';
import { FlatList } from 'react-native';
import { useOCRMemo } from '../hooks/useOCRMemo';

const VirtualizedFileList = ({ navigation }) => {
  const { filteredFiles } = useOCRMemo();

  const renderItem = ({ item }) => (
    <FileItem
      file={item}
      onPress={(fileId) => navigation.navigate('FileDetails', { fileId })}
    />
  );

  const getItemLayout = (data, index) => ({
    length: ITEM_HEIGHT,
    offset: ITEM_HEIGHT * index,
    index,
  });

  const keyExtractor = (item) => item.id.toString();

  return (
    <FlatList
      data={filteredFiles}
      renderItem={renderItem}
      keyExtractor={keyExtractor}
      getItemLayout={getItemLayout}
      removeClippedSubviews={true}
      maxToRenderPerBatch={10}
      updateCellsBatchingPeriod={50}
      initialNumToRender={20}
      windowSize={21}
    />
  );
};
```

## Error Handling

### 1. Error Boundary

```javascript
// components/ErrorBoundary.js
import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';

class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false, error: null };
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error };
  }

  componentDidCatch(error, errorInfo) {
    // Log error to monitoring service
    console.error('ErrorBoundary caught an error:', error, errorInfo);
  }

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.container}>
          <Text style={styles.title}>Something went wrong</Text>
          <Text style={styles.message}>
            The app encountered an unexpected error. Please try restarting.
          </Text>
          <TouchableOpacity
            style={styles.button}
            onPress={() => this.setState({ hasError: false, error: null })}
          >
            <Text style={styles.buttonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return this.props.children;
  }
}
```

### 2. Network Error Handling

```javascript
// hooks/useNetworkError.js
import { useEffect } from 'react';
import { useOCRContext } from '../context/OCRContext';
import NetInfo from '@react-native-community/netinfo';

export const useNetworkError = () => {
  const { state, dispatch } = useOCRContext();

  useEffect(() => {
    const unsubscribe = NetInfo.addEventListener(netState => {
      const isConnected = netState.isConnected && netState.isInternetReachable;
      
      dispatch({
        type: 'SET_NETWORK_STATUS',
        payload: isConnected ? 'online' : 'offline'
      });

      if (!isConnected && !state.error) {
        dispatch({
          type: 'SET_ERROR',
          payload: 'No internet connection. Some features may not work.'
        });
      } else if (isConnected && state.error?.includes('internet')) {
        dispatch({ type: 'CLEAR_ERROR' });
      }
    });

    return unsubscribe;
  }, [state.error, dispatch]);

  return {
    isOnline: state.networkStatus === 'online',
    hasNetworkError: state.error?.includes('internet')
  };
};
```

### 3. Retry Logic

```javascript
// utils/retryUtils.js
export const withRetry = async (fn, retries = 3, delay = 1000) => {
  for (let i = 0; i < retries; i++) {
    try {
      return await fn();
    } catch (error) {
      if (i === retries - 1) throw error;
      
      // Exponential backoff
      await new Promise(resolve => 
        setTimeout(resolve, delay * Math.pow(2, i))
      );
    }
  }
};

// hooks/useRetryableOCR.js
import { useCallback } from 'react';
import { useOCR } from './useOCR';
import { withRetry } from '../utils/retryUtils';

export const useRetryableOCR = () => {
  const ocrHook = useOCR();

  const uploadFileWithRetry = useCallback(async (fileData, fileType, categoryId) => {
    return withRetry(
      () => ocrHook.uploadFile(fileData, fileType, categoryId),
      3,
      2000
    );
  }, [ocrHook.uploadFile]);

  const loadFilesWithRetry = useCallback(async (options) => {
    return withRetry(
      () => ocrHook.loadFiles(options),
      2,
      1000
    );
  }, [ocrHook.loadFiles]);

  return {
    ...ocrHook,
    uploadFile: uploadFileWithRetry,
    loadFiles: loadFilesWithRetry,
  };
};
```

## Testing Strategies

### 1. Context Testing

```javascript
// __tests__/context/OCRContext.test.js
import React from 'react';
import { renderHook, act } from '@testing-library/react-hooks';
import { OCRProvider, useOCRContext } from '../../context/OCRContext';

const wrapper = ({ children }) => <OCRProvider>{children}</OCRProvider>;

describe('OCRContext', () => {
  test('should provide initial state', () => {
    const { result } = renderHook(() => useOCRContext(), { wrapper });
    
    expect(result.current.state.files).toEqual([]);
    expect(result.current.state.loading).toBe(false);
    expect(result.current.state.uploading).toBe(false);
  });

  test('should update files when SET_FILES action is dispatched', () => {
    const { result } = renderHook(() => useOCRContext(), { wrapper });
    
    const mockFiles = [
      { id: 1, name: 'test.pdf', ocr_status: 'completed' }
    ];

    act(() => {
      result.current.dispatch({
        type: 'SET_FILES',
        payload: mockFiles
      });
    });

    expect(result.current.state.files).toEqual(mockFiles);
    expect(result.current.state.stats.total).toBe(1);
    expect(result.current.state.stats.processed).toBe(1);
  });

  test('should handle file updates correctly', () => {
    const { result } = renderHook(() => useOCRContext(), { wrapper });
    
    // Set initial files
    act(() => {
      result.current.dispatch({
        type: 'SET_FILES',
        payload: [{ id: 1, name: 'test.pdf', ocr_status: 'processing' }]
      });
    });

    // Update file
    act(() => {
      result.current.dispatch({
        type: 'UPDATE_FILE',
        payload: { id: 1, ocr_status: 'completed', ocr_text: 'Sample text' }
      });
    });

    const updatedFile = result.current.state.files[0];
    expect(updatedFile.ocr_status).toBe('completed');
    expect(updatedFile.ocr_text).toBe('Sample text');
  });
});
```

### 2. Hook Testing

```javascript
// __tests__/hooks/useOCR.test.js
import { renderHook, act } from '@testing-library/react-hooks';
import { useOCR } from '../../hooks/useOCR';
import OCRService from '../../services/ocrService';

// Mock the OCR service
jest.mock('../../services/ocrService');

const wrapper = ({ children }) => <OCRProvider>{children}</OCRProvider>;

describe('useOCR', () => {
  beforeEach(() => {
    jest.clearAllMocks();
  });

  test('should load files successfully', async () => {
    const mockFiles = [
      { id: 1, name: 'test.pdf', ocr_status: 'completed' }
    ];

    OCRService.getFiles.mockResolvedValue({
      files: mockFiles,
      categories: []
    });

    const { result } = renderHook(() => useOCR(), { wrapper });

    await act(async () => {
      await result.current.loadFiles();
    });

    expect(result.current.files).toEqual(mockFiles);
    expect(result.current.loading).toBe(false);
  });

  test('should handle upload errors', async () => {
    const mockError = new Error('Upload failed');
    OCRService.uploadFile.mockRejectedValue(mockError);

    const { result } = renderHook(() => useOCR(), { wrapper });

    await act(async () => {
      try {
        await result.current.uploadFile({}, 'document');
      } catch (error) {
        // Expected to throw
      }
    });

    expect(result.current.error).toBe('Upload failed');
    expect(result.current.uploading).toBe(false);
  });

  test('should start OCR polling', async () => {
    jest.useFakeTimers();
    
    const { result } = renderHook(() => useOCR(), { wrapper });

    act(() => {
      result.current.startOCRPolling(1);
    });

    expect(result.current.processingFiles.has(1)).toBe(true);

    // Fast-forward time
    jest.advanceTimersByTime(5000);

    jest.useRealTimers();
  });
});
```

### 3. Component Testing

```javascript
// __tests__/components/FilesList.test.js
import React from 'react';
import { render, fireEvent, waitFor } from '@testing-library/react-native';
import FilesList from '../../components/FilesList';
import { useOCR } from '../../hooks/useOCR';

// Mock the hook
jest.mock('../../hooks/useOCR');

describe('FilesList', () => {
  const mockOCRHook = {
    files: [],
    categories: [],
    loading: false,
    searchQuery: '',
    selectedCategory: null,
    stats: { total: 0, processed: 0, processing: 0, failed: 0 },
    error: null,
    loadFiles: jest.fn(),
    searchFiles: jest.fn(),
    filterByCategory: jest.fn(),
    clearError: jest.fn(),
  };

  beforeEach(() => {
    useOCR.mockReturnValue(mockOCRHook);
  });

  test('should render empty state when no files', () => {
    const { getByText } = render(<FilesList />);
    
    expect(getByText('No files found')).toBeTruthy();
    expect(getByText('Upload documents and images to get started with OCR')).toBeTruthy();
  });

  test('should render files when available', () => {
    const mockFiles = [
      {
        id: 1,
        original_filename: 'test.pdf',
        file_type: 'document',
        category: 'Professional',
        ocr_status: 'completed',
        file_size_display: '1.2 MB',
        upload_date: '2023-01-01T00:00:00Z'
      }
    ];

    useOCR.mockReturnValue({
      ...mockOCRHook,
      files: mockFiles
    });

    const { getByText } = render(<FilesList />);
    
    expect(getByText('test.pdf')).toBeTruthy();
    expect(getByText('Professional')).toBeTruthy();
  });

  test('should handle search input', () => {
    const { getByPlaceholderText } = render(<FilesList />);
    
    const searchInput = getByPlaceholderText('Search files...');
    fireEvent.changeText(searchInput, 'test query');

    expect(mockOCRHook.searchFiles).toHaveBeenCalledWith('test query');
  });

  test('should handle category filter', () => {
    const mockCategories = [
      { id: 1, name: 'Professional', count: 5 }
    ];

    useOCR.mockReturnValue({
      ...mockOCRHook,
      categories: mockCategories
    });

    const { getByText } = render(<FilesList />);
    
    // Open category filter and select category
    fireEvent.press(getByText('All ▼'));
    fireEvent.press(getByText('Professional'));

    expect(mockOCRHook.filterByCategory).toHaveBeenCalledWith('Professional');
  });
});
```

## Best Practices

### 1. State Structure Guidelines

```javascript
// ✅ Good: Normalized state structure
const goodState = {
  files: {
    byId: {
      1: { id: 1, name: 'doc1.pdf', categoryId: 'prof' },
      2: { id: 2, name: 'doc2.pdf', categoryId: 'bank' }
    },
    allIds: [1, 2]
  },
  categories: {
    byId: {
      prof: { id: 'prof', name: 'Professional' },
      bank: { id: 'bank', name: 'Banking' }
    },
    allIds: ['prof', 'bank']
  }
};

// ❌ Bad: Nested, denormalized state
const badState = {
  files: [
    {
      id: 1,
      name: 'doc1.pdf',
      category: { id: 'prof', name: 'Professional' } // Duplication
    }
  ]
};
```

### 2. Action Design Patterns

```javascript
// ✅ Good: Specific, granular actions
const goodActions = {
  startFileUpload: (file) => ({ type: 'START_FILE_UPLOAD', payload: file }),
  fileUploadProgress: (fileId, progress) => ({ 
    type: 'FILE_UPLOAD_PROGRESS', 
    payload: { fileId, progress } 
  }),
  fileUploadSuccess: (file) => ({ type: 'FILE_UPLOAD_SUCCESS', payload: file }),
  fileUploadFailure: (fileId, error) => ({ 
    type: 'FILE_UPLOAD_FAILURE', 
    payload: { fileId, error } 
  }),
};

// ❌ Bad: Generic, unclear actions
const badActions = {
  updateFile: (data) => ({ type: 'UPDATE_FILE', payload: data }),
  setStatus: (status) => ({ type: 'SET_STATUS', payload: status }),
};
```

### 3. Performance Best Practices

```javascript
// ✅ Good: Memoized selectors
const useFileSelectors = () => {
  const { state } = useOCRContext();
  
  return useMemo(() => ({
    completedFiles: state.files.filter(f => f.ocr_status === 'completed'),
    processingFiles: state.files.filter(f => f.ocr_status === 'processing'),
    filesByCategory: groupBy(state.files, 'category'),
  }), [state.files]);
};

// ❌ Bad: Computing in render
const BadComponent = () => {
  const { files } = useOCR();
  
  // This runs on every render!
  const completedFiles = files.filter(f => f.ocr_status === 'completed');
  
  return <FileList files={completedFiles} />;
};
```

### 4. Error Handling Patterns

```javascript
// ✅ Good: Comprehensive error handling
const useOCRWithErrorHandling = () => {
  const ocrHook = useOCR();
  
  const uploadFileWithErrorHandling = useCallback(async (fileData, fileType) => {
    try {
      return await ocrHook.uploadFile(fileData, fileType);
    } catch (error) {
      // Log error
      console.error('Upload failed:', error);
      
      // Show user-friendly message
      if (error.code === 'NETWORK_ERROR') {
        Alert.alert('Network Error', 'Please check your internet connection');
      } else if (error.code === 'FILE_TOO_LARGE') {
        Alert.alert('File Too Large', 'Please select a smaller file');
      } else {
        Alert.alert('Upload Failed', 'An unexpected error occurred');
      }
      
      throw error;
    }
  }, [ocrHook.uploadFile]);
  
  return {
    ...ocrHook,
    uploadFile: uploadFileWithErrorHandling,
  };
};
```

### 5. Testing Best Practices

```javascript
// ✅ Good: Testing with proper mocks and async handling
describe('OCR Upload Flow', () => {
  test('should handle complete upload flow', async () => {
    const mockFile = { uri: 'test.pdf', type: 'application/pdf' };
    const mockResponse = { 
      success: true, 
      file: { id: 1, name: 'test.pdf' },
      ocr_result: { status: 'processing' }
    };
    
    OCRService.uploadFile.mockResolvedValue(mockResponse);
    OCRService.getOCRStatus.mockResolvedValue({
      success: true,
      ocr_status: 'completed',
      ocr_text: 'Sample text'
    });
    
    const { result } = renderHook(() => useOCR(), { wrapper });
    
    // Test upload
    await act(async () => {
      await result.current.uploadFile(mockFile, 'document');
    });
    
    expect(result.current.files).toHaveLength(1);
    expect(result.current.processingFiles.has(1)).toBe(true);
    
    // Test polling completion
    await waitFor(() => {
      expect(result.current.processingFiles.has(1)).toBe(false);
    });
    
    const uploadedFile = result.current.files[0];
    expect(uploadedFile.ocr_status).toBe('completed');
    expect(uploadedFile.ocr_text).toBe('Sample text');
  });
});
```

## Conclusion

This state management architecture provides:

- **Scalable Structure**: Easy to extend with new features
- **Performance Optimization**: Memoization and virtualization
- **Error Resilience**: Comprehensive error handling and retry logic
- **Developer Experience**: Clear patterns and extensive testing
- **User Experience**: Smooth interactions and real-time updates

### Next Steps

1. **Implement Core Context**: Start with OCRContext and basic actions
2. **Add Custom Hooks**: Build useOCR hook with essential operations
3. **Create Components**: Integrate hooks into your components
4. **Add Error Handling**: Implement error boundaries and retry logic
5. **Optimize Performance**: Add memoization and virtualization
6. **Write Tests**: Ensure reliability with comprehensive testing
7. **Monitor Performance**: Use React DevTools and performance profiling

This guide provides a solid foundation for managing complex OCR application state in React Native while maintaining performance and user experience.