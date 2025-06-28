# Password Management - React Native Integration Guide

## Overview

This guide explains how to integrate the password management system with your React Native frontend application. The password management system provides secure storage, organization, and retrieval of passwords, including features like encryption, categorization, and security checks.

### Key Features

- **Secure Password Storage**: All passwords are encrypted using AES-256 encryption
- **Password Organization**: Categorize and tag passwords for easy management
- **Password Sharing**: Securely share passwords with other users (optional)
- **Security Analysis**: Check for weak, reused, or compromised passwords
- **Password Generation**: Create strong, unique passwords with customizable options
- **Biometric Authentication**: Support for Face ID/Touch ID for accessing passwords
- **Autofill Integration**: (Optional) Integration with mobile autofill functionality
- **Offline Access**: Access to passwords even without internet connection

### System Requirements

- React Native 0.64+
- Node.js 14+
- Authentication system that supports JWT tokens
- Appropriate secure storage libraries (react-native-keychain or expo-secure-store recommended)

## API Compatibility

### CSRF Protection

All API endpoints in this password management system are now **CSRF exempt** to ensure full compatibility with React Native and other mobile clients. This includes:

1. All class-based API views using `@method_decorator(csrf_exempt, name='dispatch')`
2. All function-based API endpoints using direct `@csrf_exempt` decorator
3. All web views protected with `@login_required` are also CSRF exempt for testing

This configuration allows:
- Seamless integration with React Native clients
- Compatibility with the template-based web interface for testing/admin purposes
- Secure API calls from mobile clients without CSRF token requirements

## Authentication

### Setting Up Authentication

To use the password management system, you need to implement user authentication in your React Native app. The API uses JWT (JSON Web Tokens) for authentication.

#### Step 1: Install Required Packages

```bash
# For secure token storage
npm install react-native-keychain
# For HTTP requests
npm install axios
```

#### Step 2: User Login Flow

Here's a complete implementation of the login process:

```javascript
// src/services/authService.js
import axios from 'axios';
import * as Keychain from 'react-native-keychain';

const API_URL = 'https://your-api-url.com';

// Login to get authentication token
export const loginUser = async (username, password) => {
  try {
    const response = await axios.post(`${API_URL}/auth/api/mobile/login/`, {
      username,
      password,
    });
    
    const data = response.data;
    
    if (data.success) {
      // Store tokens securely using keychain
      await Keychain.setGenericPassword(
        'auth_tokens',
        JSON.stringify({
          accessToken: data.tokens.access,
          refreshToken: data.tokens.refresh,
          expiresAt: Date.now() + (3600 * 1000), // 1 hour expiry
        })
      );
      return data.tokens;
    } else {
      throw new Error(data.error || 'Login failed');
    }
  } catch (error) {
    console.error('Login error:', error.response?.data || error.message);
    throw error;
  }
};

// Get saved tokens
export const getTokens = async () => {
  try {
    const credentials = await Keychain.getGenericPassword();
    if (credentials) {
      return JSON.parse(credentials.password);
    }
    return null;
  } catch (error) {
    console.error('Error getting tokens:', error);
    return null;
  }
};

// Logout user
export const logoutUser = async () => {
  try {
    await Keychain.resetGenericPassword();
    return true;
  } catch (error) {
    console.error('Logout error:', error);
    return false;
  }
};
```

#### Step 3: Create Authentication Context

```javascript
// src/contexts/AuthContext.js
import React, { createContext, useState, useEffect, useContext } from 'react';
import { loginUser, getTokens, logoutUser } from '../services/authService';

const AuthContext = createContext();

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [tokens, setTokens] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check for existing auth on startup
    const loadStoredAuth = async () => {
      const storedTokens = await getTokens();
      if (storedTokens) {
        setTokens(storedTokens);
        // Optional: validate token on server or decode JWT to get user info
      }
      setLoading(false);
    };
    
    loadStoredAuth();
  }, []);

  const login = async (username, password) => {
    try {
      const newTokens = await loginUser(username, password);
      setTokens(newTokens);
      // You could extract user info from JWT or make additional call
      setUser({
        id: newTokens.user_id,
        username: username
      });
      return true;
    } catch (error) {
      return false;
    }
  };

  const logout = async () => {
    await logoutUser();
    setTokens(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        tokens,
        isAuthenticated: !!tokens,
        login,
        logout,
        loading
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => useContext(AuthContext);
```

#### Step 4: Setup Axios with Authentication Interceptors

```javascript
// src/services/api.js
import axios from 'axios';
import { getTokens } from './authService';

const API_URL = 'https://your-api-url.com';

const apiClient = axios.create({
  baseURL: API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add a request interceptor to include the auth token
apiClient.interceptors.request.use(
  async (config) => {
    const tokenData = await getTokens();
    if (tokenData && tokenData.accessToken) {
      config.headers.Authorization = `Bearer ${tokenData.accessToken}`;
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add response interceptor to handle token refresh
apiClient.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;
    
    // If the error is 401 and not already retrying
    if (
      error.response?.status === 401 && 
      !originalRequest._retry && 
      originalRequest.url !== '/auth/api/mobile/token/refresh/'
    ) {
      originalRequest._retry = true;
      
      try {
        const tokenData = await getTokens();
        if (!tokenData || !tokenData.refreshToken) {
          throw new Error('No refresh token available');
        }
        
        const response = await axios.post(
          `${API_URL}/auth/api/mobile/token/refresh/`,
          { refresh_token: tokenData.refreshToken }
        );
        
        const { tokens } = response.data;
        
        // Save the new tokens securely
        await Keychain.setGenericPassword(
          'auth_tokens',
          JSON.stringify({
            accessToken: tokens.access,
            refreshToken: tokens.refresh,
            expiresAt: Date.now() + (3600 * 1000), // 1 hour expiry
          })
        );
        
        // Update the authorization header
        originalRequest.headers.Authorization = `Bearer ${tokens.access}`;
        return axios(originalRequest);
      } catch (refreshError) {
        // Handle refresh token failure - logout user
        await Keychain.resetGenericPassword();
        // You might want to redirect to login screen here
        return Promise.reject(refreshError);
      }
    }
    
    return Promise.reject(error);
  }
);

export default apiClient;
```

## API Endpoints

### Core Endpoints

#### 1. List Password Entries

- **Endpoint:** `GET /password_management/api/mobile/entries/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Retrieves all password entries for the authenticated user
- **Query Parameters:**
  - `category`: Filter by category ID
  - `type`: Filter by entry type ('password', 'app', 'wifi', 'card', 'note', 'passkey', 'identity')
  - `favorites`: Filter by favorites only ('true' or 'false')
  - `search`: Search term to filter entries by title, username, email, or URL
  - `sort`: Sort by 'title', 'last_used', or '-updated_at' (default)
- **Success Response:** `200 OK`
  ```json
  [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "entry_type": "password",
      "title": "Example Website",
      "username": "user@example.com",
      "email": "user@example.com",
      "website_url": "https://example.com",
      "notes": "My work login",
      "category": 1,
      "strength": "strong",
      "is_favorite": false,
      "created_at": "2023-01-15T12:00:00Z",
      "updated_at": "2023-01-15T12:00:00Z"
    }
  ]
  ```
- **Error Response:** `401 Unauthorized` if token is invalid or missing

#### 2. Create Password Entry

- **Endpoint:** `POST /password_management/api/mobile/entries/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Creates a new password entry for the authenticated user
- **Request Body:**
  ```json
  {
    "entry_type": "password",
    "title": "Example Website",
    "username": "user@example.com",
    "email": "user@example.com",
    "password": "SecurePassword123!",
    "website_url": "https://example.com",
    "notes": "Optional notes",
    "category": 1,
    "is_favorite": false
  }
  ```
- **Success Response:** `201 Created`
  ```json
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "entry_type": "password",
    "title": "Example Website",
    "username": "user@example.com",
    "email": "user@example.com",
    "website_url": "https://example.com",
    "notes": "Optional notes",
    "category": 1,
    "strength": "strong",
    "is_favorite": false,
    "created_at": "2023-01-15T12:00:00Z",
    "updated_at": "2023-01-15T12:00:00Z"
  }
  ```
- **Error Responses:**
  - `400 Bad Request` if validation fails
  - `401 Unauthorized` if token is invalid or missing

#### 3. Get Password Categories

- **Endpoint:** `GET /password_management/api/categories/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Retrieves all password categories for the authenticated user
- **Success Response:** `200 OK`
  ```json
  [
    {
      "id": 1,
      "name": "Website Logins",
      "icon": "globe",
      "color": "#007aff"
    },
    {
      "id": 2,
      "name": "Financial",
      "icon": "credit-card",
      "color": "#4cd964"
    }
  ]
  ```
- **Error Response:** `401 Unauthorized` if token is invalid or missing

#### 4. Create Password Category

- **Endpoint:** `POST /password_management/api/categories/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Creates a new password category
- **Request Body:**
  ```json
  {
    "name": "New Category",
    "icon": "lock",
    "color": "#ff9500"
  }
  ```
- **Success Response:** `201 Created`
  ```json
  {
    "id": 3,
    "name": "New Category",
    "icon": "lock",
    "color": "#ff9500"
  }
  ```
- **Error Responses:**
  - `400 Bad Request` if validation fails
  - `401 Unauthorized` if token is invalid or missing

#### 5. Get Single Password Entry

- **Endpoint:** `GET /password_management/api/entries/{uuid}/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Retrieves a specific password entry by its UUID
- **Path Parameters:**
  - `uuid`: The unique identifier of the password entry
- **Success Response:** `200 OK`
  ```json
  {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "entry_type": "password",
    "title": "Example Website",
    "username": "user@example.com",
    "email": "user@example.com",
    "website_url": "https://example.com",
    "notes": "Optional notes",
    "category": 1,
    "strength": "strong",
    "is_favorite": false,
    "created_at": "2023-01-15T12:00:00Z",
    "updated_at": "2023-01-15T12:00:00Z"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized` if token is invalid or missing
  - `404 Not Found` if the password entry doesn't exist

#### 6. Update Password Entry

- **Endpoint:** `PUT /password_management/api/entries/{uuid}/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Updates an existing password entry
- **Path Parameters:**
  - `uuid`: The unique identifier of the password entry
- **Request Body:** Same format as create, with fields to update
- **Success Response:** `200 OK` with updated entry data
- **Error Responses:**
  - `400 Bad Request` if validation fails
  - `401 Unauthorized` if token is invalid or missing
  - `404 Not Found` if the password entry doesn't exist

#### 7. Delete Password Entry

- **Endpoint:** `DELETE /password_management/api/entries/{uuid}/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Deletes a password entry
- **Path Parameters:**
  - `uuid`: The unique identifier of the password entry
- **Success Response:** `204 No Content`
- **Error Responses:**
  - `401 Unauthorized` if token is invalid or missing
  - `404 Not Found` if the password entry doesn't exist

#### 8. Copy Password

- **Endpoint:** `POST /password_management/api/entries/{uuid}/copy_password/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Retrieves the decrypted password for copying (requires verified master password)
- **Path Parameters:**
  - `uuid`: The unique identifier of the password entry
- **Success Response:** `200 OK`
  ```json
  {
    "password": "DecryptedPassword123!"
  }
  ```
- **Error Responses:**
  - `401 Unauthorized` if token is invalid or missing
  - `403 Forbidden` if master password not verified
  - `404 Not Found` if the password entry doesn't exist

#### 9. Generate Password

- **Endpoint:** `POST /password_management/api/entries/{uuid}/generate_password/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Generates a strong password for an existing entry
- **Path Parameters:**
  - `uuid`: The unique identifier of the password entry
- **Request Body:**
  ```json
  {
    "length": 16,
    "uppercase": true,
    "numbers": true,
    "symbols": true
  }
  ```
- **Success Response:** `200 OK`
  ```json
  {
    "password": "GeneratedPassword!2",
    "strength": "strong"
  }
  ```
- **Error Responses:**
  - `400 Bad Request` if validation fails
  - `401 Unauthorized` if token is invalid or missing
  - `404 Not Found` if the password entry doesn't exist

#### 10. Check Compromised Password

- **Endpoint:** `POST /password_management/api/entries/{uuid}/check_compromised/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Checks if a password has been compromised in data breaches
- **Path Parameters:**
  - `uuid`: The unique identifier of the password entry
- **Request Body:**
  ```json
  {
    "password": "PasswordToCheck123"
  }
  ```
- **Success Response:** `200 OK`
  ```json
  {
    "is_compromised": false,
    "message": "Your password appears to be secure."
  }
  ```
  or
  ```json
  {
    "is_compromised": true,
    "count": 35,
    "message": "This password has appeared in 35 data breaches. You should change it immediately."
  }
  ```
- **Error Responses:**
  - `400 Bad Request` if validation fails
  - `401 Unauthorized` if token is invalid or missing
  - `404 Not Found` if the password entry doesn't exist

#### 11. Security Settings

- **Endpoint:** `GET /password_management/api/security-settings/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Retrieves the user's security settings
- **Success Response:** `200 OK`
  ```json
  {
    "check_for_compromised": true,
    "suggest_strong_passwords": true,
    "min_password_length": 12,
    "password_require_uppercase": true,
    "password_require_numbers": true,
    "password_require_symbols": true,
    "auto_fill_enabled": true
  }
  ```
- **Error Response:** `401 Unauthorized` if token is invalid or missing

- **Update Endpoint:** `PUT /password_management/api/security-settings/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Updates the user's security settings
- **Request Body:** Same format as GET response, with fields to update
- **Success Response:** `200 OK` with updated settings
- **Error Responses:**
  - `400 Bad Request` if validation fails
  - `401 Unauthorized` if token is invalid or missing

#### 12. Master Password

- **Endpoint:** `POST /password_management/api/master-password/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Sets or changes the master password
- **Request Body:**
  ```json
  {
    "master_password": "YourSecureMasterPassword123!",
    "confirm_password": "YourSecureMasterPassword123!"
  }
  ```
- **Success Response:** `200 OK`
  ```json
  {
    "success": true,
    "created": true
  }
  ```
- **Error Responses:**
  - `400 Bad Request` if validation fails
  - `401 Unauthorized` if token is invalid or missing

#### 13. Verify Master Password

- **Endpoint:** `POST /password_management/api/verify-master-password/`
- **Authentication:** Required (JWT Bearer token)
- **Description:** Verifies the master password and enables access to sensitive operations
- **Request Body:**
  ```json
  {
    "master_password": "YourSecureMasterPassword123!"
  }
  ```
- **Success Response:** `200 OK`
  ```json
  {
    "success": true,
    "valid_until": 1673844000
  }
  ```
- **Error Responses:**
  - `400 Bad Request` if the password is incorrect
  - `401 Unauthorized` if token is invalid or missing

#### 14. Direct Password Creation (Development/Testing)

- **Endpoint:** `POST /password_management/api/mobile-create-password/` (NO AUTHENTICATION REQUIRED)
- **Description:** Creates a password entry without authentication (FOR DEVELOPMENT ONLY)
- **Request Body:** Same as regular password creation
- **Success Response:** `201 Created`
  ```json
  {
    "success": true,
    "message": "Password created successfully",
    "id": "550e8400-e29b-41d4-a716-446655440000"
  }
  ```
- **Error Response:** `400 Bad Request` if validation fails
- **⚠️ WARNING:** This endpoint is for development and testing only. It automatically creates entries for the first user in the system without authentication.

#### 15. Generate Password (Standalone)

- **Endpoint:** `POST /password_management/api/generate-password/`
- **Authentication:** Not required
- **Description:** Generates a secure password without authentication
- **Request Body:**
  ```json
  {
    "length": 16,
    "uppercase": true,
    "numbers": true,
    "symbols": true
  }
  ```
- **Success Response:** `200 OK`
  ```json
  {
    "success": true,
    "password": "GeneratedPassword123!",
    "strength": "strong"
  }
  ```
- **Error Response:** `400 Bad Request` if validation fails

## React Native Integration

### Setting Up the Password Service

Create a dedicated service for password management integration:

```javascript
// src/services/passwordService.js
import apiClient from './api'; // Your authenticated API client from above

// Password Entries
export const getPasswordEntries = (filters = {}) => {
  let queryString = '';
  
  if (filters.category) queryString += `category=${filters.category}&`;
  if (filters.type) queryString += `type=${filters.type}&`;
  if (filters.favorites) queryString += `favorites=${filters.favorites}&`;
  if (filters.search) queryString += `search=${encodeURIComponent(filters.search)}&`;
  if (filters.sort) queryString += `sort=${filters.sort}&`;
  
  return apiClient.get(`/password_management/api/mobile/entries/?${queryString}`);
};

export const getPasswordEntry = (entryId) => {
  return apiClient.get(`/password_management/api/entries/${entryId}/`);
};

export const createPasswordEntry = (entryData) => {
  return apiClient.post('/password_management/api/mobile/entries/', entryData);
};

export const updatePasswordEntry = (entryId, entryData) => {
  return apiClient.put(`/password_management/api/entries/${entryId}/`, entryData);
};

export const deletePasswordEntry = (entryId) => {
  return apiClient.delete(`/password_management/api/entries/${entryId}/`);
};

export const copyPassword = (entryId) => {
  return apiClient.post(`/password_management/api/entries/${entryId}/copy_password/`);
};

export const generatePassword = (entryId, options) => {
  return apiClient.post(`/password_management/api/entries/${entryId}/generate_password/`, options);
};

export const checkCompromised = (entryId, password) => {
  return apiClient.post(`/password_management/api/entries/${entryId}/check_compromised/`, { password });
};

// Development/Testing only - creates passwords without authentication
export const createPasswordDirect = (passwordData) => {
  return apiClient.post('/password_management/api/mobile-create-password/', passwordData);
};

// Generate password without authentication - can be used even on login screens
export const generatePasswordStandalone = (options) => {
  return apiClient.post('/password_management/api/generate-password/', options);
};

// Categories
export const getCategories = () => {
  return apiClient.get('/password_management/api/categories/');
};

export const createCategory = (categoryData) => {
  return apiClient.post('/password_management/api/categories/', categoryData);
};

export const updateCategory = (categoryId, categoryData) => {
  return apiClient.put(`/password_management/api/categories/${categoryId}/`, categoryData);
};

export const deleteCategory = (categoryId) => {
  return apiClient.delete(`/password_management/api/categories/${categoryId}/`);
};

// Security Settings
export const getSecuritySettings = () => {
  return apiClient.get('/password_management/api/security-settings/');
};

export const updateSecuritySettings = (settingsData) => {
  return apiClient.put('/password_management/api/security-settings/', settingsData);
};

// Master Password
export const setMasterPassword = (masterPassword, confirmPassword) => {
  return apiClient.post('/password_management/api/master-password/', { 
    master_password: masterPassword,
    confirm_password: confirmPassword 
  });
};

export const verifyMasterPassword = (masterPassword) => {
  return apiClient.post('/password_management/api/verify-master-password/', { 
    master_password: masterPassword 
  });
};
```

### Recommended Navigation Structure

```javascript
// src/navigation/PasswordStack.js
import React from 'react';
import { createStackNavigator } from '@react-navigation/stack';

import PasswordListScreen from '../screens/PasswordListScreen';
import PasswordDetailScreen from '../screens/PasswordDetailScreen';
import CreatePasswordScreen from '../screens/CreatePasswordScreen';
import EditPasswordScreen from '../screens/EditPasswordScreen';
import CategoryListScreen from '../screens/CategoryListScreen';
import SecuritySettingsScreen from '../screens/SecuritySettingsScreen';
import MasterPasswordScreen from '../screens/MasterPasswordScreen';

const Stack = createStackNavigator();

const PasswordStack = () => {
  return (
    <Stack.Navigator
      screenOptions={{
        headerStyle: {
          backgroundColor: '#007aff',
        },
        headerTintColor: '#fff',
        headerTitleStyle: {
          fontWeight: 'bold',
        },
      }}
    >
      <Stack.Screen 
        name="PasswordList" 
        component={PasswordListScreen} 
        options={{ title: 'Passwords' }}
      />
      <Stack.Screen 
        name="PasswordDetail" 
        component={PasswordDetailScreen} 
        options={{ title: 'Password Details' }}
      />
      <Stack.Screen 
        name="CreatePassword" 
        component={CreatePasswordScreen} 
        options={{ title: 'Add Password' }}
      />
      <Stack.Screen 
        name="EditPassword" 
        component={EditPasswordScreen} 
        options={{ title: 'Edit Password' }}
      />
      <Stack.Screen 
        name="Categories" 
        component={CategoryListScreen} 
        options={{ title: 'Categories' }}
      />
      <Stack.Screen 
        name="SecuritySettings" 
        component={SecuritySettingsScreen} 
        options={{ title: 'Security Settings' }}
      />
      <Stack.Screen 
        name="MasterPassword" 
        component={MasterPasswordScreen} 
        options={{ title: 'Master Password' }}
      />
    </Stack.Navigator>
  );
};

export default PasswordStack;
```

### Example Screens

#### 1. Password List Screen

This screen displays all the user's password entries with filtering and search capabilities:

```javascript
// src/screens/PasswordListScreen.js
import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, TextInput, Alert, RefreshControl } from 'react-native';
import { useFocusEffect } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/FontAwesome5';
import { getPasswordEntries, getCategories } from '../services/passwordService';
import EmptyState from '../components/EmptyState';
import LoadingSpinner from '../components/LoadingSpinner';

const PasswordListScreen = ({ navigation }) => {
  const [passwords, setPasswords] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [search, setSearch] = useState('');
  const [filters, setFilters] = useState({
    category: null,
    type: null,
    favorites: false,
    sort: '-updated_at'
  });

  const loadData = useCallback(async () => {
    try {
      setLoading(true);
      
      // Load categories and passwords in parallel
      const [entriesResponse, categoriesResponse] = await Promise.all([
        getPasswordEntries({
          ...filters,
          search: search
        }),
        getCategories()
      ]);
      
      setPasswords(entriesResponse.data);
      setCategories(categoriesResponse.data);
    } catch (error) {
      console.error('Error loading data:', error);
      Alert.alert(
        'Error',
        'Could not load your passwords. Please try again later.'
      );
    } finally {
      setLoading(false);
      setRefreshing(false);
    }
  }, [filters, search]);

  // Load data when screen comes into focus
  useFocusEffect(
    useCallback(() => {
      loadData();
    }, [loadData])
  );

  const onRefresh = () => {
    setRefreshing(true);
    loadData();
  };

  const handleSearch = (text) => {
    setSearch(text);
  };

  const applySearchFilter = () => {
    loadData();
  };

  const clearSearch = () => {
    setSearch('');
    loadData();
  };

  const toggleFavoriteFilter = () => {
    setFilters({
      ...filters,
      favorites: !filters.favorites
    });
  };

  const setCategoryFilter = (categoryId) => {
    setFilters({
      ...filters,
      category: categoryId
    });
  };
  
  const setTypeFilter = (type) => {
    setFilters({
      ...filters,
      type: type
    });
  };
  
  const setSortOrder = (sort) => {
    setFilters({
      ...filters,
      sort: sort
    });
  };

  const renderItem = ({ item }) => (
    <TouchableOpacity 
      style={styles.item}
      onPress={() => navigation.navigate('PasswordDetail', { passwordId: item.id })}
    >
      <View style={[styles.iconContainer, getCategoryColor(item.category)]}>
        <Icon 
          name={getIconForType(item.entry_type)} 
          size={24} 
          color="#fff" 
        />
      </View>
      <View style={styles.contentContainer}>
        <Text style={styles.title}>{item.title}</Text>
        <Text style={styles.subtitle}>{item.username || item.email || 'No username'}</Text>
      </View>
      {item.is_favorite && (
        <Icon name="star" size={18} color="#ffcc00" style={styles.favoriteIcon} />
      )}
      <Icon name="chevron-right" size={16} color="#999" />
    </TouchableOpacity>
  );
  
  const getCategoryColor = (categoryId) => {
    if (!categoryId) return { backgroundColor: '#007aff' };
    
    const category = categories.find(c => c.id === categoryId);
    if (category) {
      return { backgroundColor: category.color };
    }
    return { backgroundColor: '#007aff' };
  };

  const getIconForType = (type) => {
    switch (type) {
      case 'password': return 'globe';
      case 'app': return 'mobile-alt';
      case 'wifi': return 'wifi';
      case 'card': return 'credit-card';
      case 'note': return 'sticky-note';
      case 'passkey': return 'key';
      case 'identity': return 'id-card';
      default: return 'lock';
    }
  };
  
  const renderFilterChips = () => (
    <View style={styles.filterContainer}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false}>
        <TouchableOpacity 
          style={[styles.filterChip, filters.favorites && styles.activeChip]}
          onPress={toggleFavoriteFilter}
        >
          <Icon name="star" size={16} color={filters.favorites ? "#fff" : "#007aff"} />
          <Text style={[styles.chipText, filters.favorites && styles.activeChipText]}>Favorites</Text>
        </TouchableOpacity>
        
        {categories.map(category => (
          <TouchableOpacity 
            key={category.id}
            style={[
              styles.filterChip, 
              filters.category === category.id && styles.activeChip,
              filters.category === category.id && { backgroundColor: category.color }
            ]}
            onPress={() => setCategoryFilter(filters.category === category.id ? null : category.id)}
          >
            <Icon 
              name={category.icon} 
              size={16} 
              color={filters.category === category.id ? "#fff" : "#007aff"} 
            />
            <Text style={[styles.chipText, filters.category === category.id && styles.activeChipText]}>
              {category.name}
            </Text>
          </TouchableOpacity>
        ))}
      </ScrollView>
    </View>
  );

  if (loading && !refreshing) {
    return <LoadingSpinner />;
  }

  return (
    <View style={styles.container}>
      <View style={styles.searchContainer}>
        <Icon name="search" size={20} color="#999" style={styles.searchIcon} />
        <TextInput
          style={styles.searchInput}
          placeholder="Search passwords..."
          value={search}
          onChangeText={handleSearch}
          onSubmitEditing={applySearchFilter}
          returnKeyType="search"
        />
        {search.length > 0 && (
          <TouchableOpacity onPress={clearSearch}>
            <Icon name="times-circle" size={20} color="#999" />
          </TouchableOpacity>
        )}
      </View>
      
      {renderFilterChips()}
      
      <FlatList
        data={passwords}
        renderItem={renderItem}
        keyExtractor={item => item.id}
        contentContainerStyle={[
          styles.list,
          passwords.length === 0 && styles.emptyList
        ]}
        refreshControl={
          <RefreshControl
            refreshing={refreshing}
            onRefresh={onRefresh}
            colors={['#007aff']}
          />
        }
        ListEmptyComponent={
          <EmptyState
            icon="lock"
            title="No passwords yet"
            message="Add your first password by tapping the + button below"
          />
        }
      />
      
      <View style={styles.fabContainer}>
        <TouchableOpacity 
          style={[styles.fab, styles.settingsFab]}
          onPress={() => navigation.navigate('SecuritySettings')}
        >
          <Icon name="cog" size={24} color="#fff" />
        </TouchableOpacity>
        
        <TouchableOpacity 
          style={styles.fab}
          onPress={() => navigation.navigate('CreatePassword')}
        >
          <Icon name="plus" size={24} color="#fff" />
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f8f8',
  },
  searchContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    borderRadius: 8,
    margin: 16,
    paddingHorizontal: 12,
    elevation: 2,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 2,
  },
  searchIcon: {
    marginRight: 8,
  },
  searchInput: {
    flex: 1,
    height: 44,
    fontSize: 16,
  },
  filterContainer: {
    marginBottom: 8,
    paddingHorizontal: 16,
  },
  filterChip: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#f0f0f0',
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 16,
    marginRight: 8,
    marginBottom: 8,
  },
  activeChip: {
    backgroundColor: '#007aff',
  },
  chipText: {
    fontSize: 14,
    marginLeft: 4,
    color: '#007aff',
  },
  activeChipText: {
    color: '#fff',
  },
  list: {
    paddingBottom: 100,
  },
  emptyList: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  item: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#fff',
    padding: 16,
    marginHorizontal: 16,
    marginBottom: 8,
    borderRadius: 8,
    elevation: 1,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.1,
    shadowRadius: 1,
  },
  iconContainer: {
    width: 40,
    height: 40,
    borderRadius: 20,
    backgroundColor: '#007aff',
    justifyContent: 'center',
    alignItems: 'center',
    marginRight: 12,
  },
  contentContainer: {
    flex: 1,
  },
  title: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
  },
  subtitle: {
    fontSize: 14,
    color: '#666',
    marginTop: 2,
  },
  favoriteIcon: {
    marginRight: 8,
  },
  fabContainer: {
    position: 'absolute',
    right: 20,
    bottom: 20,
    flexDirection: 'row',
  },
  fab: {
    width: 56,
    height: 56,
    borderRadius: 28,
    backgroundColor: '#007aff',
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 5,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 3 },
    shadowOpacity: 0.2,
    shadowRadius: 4,
  },
  settingsFab: {
    backgroundColor: '#4cd964',
    marginRight: 16,
  },
});

export default PasswordListScreen;
```

### Create Password Screen

```javascript
// src/screens/CreatePasswordScreen.js
import React, { useState } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, Switch } from 'react-native';
import { createPasswordDirect, generatePasswordStandalone } from '../services/passwordService';

const CreatePasswordScreen = ({ navigation }) => {
  const [formData, setFormData] = useState({
    title: '',
    username: '',
    email: '',
    password: '',
    website_url: '',
    notes: '',
    entry_type: 'password',
    category: null,
    is_favorite: false
  });
  
  const [showPassword, setShowPassword] = useState(false);
  
  const handleChange = (field, value) => {
    setFormData({
      ...formData,
      [field]: value
    });
  };
  
  const generatePassword = async () => {
    try {
      const response = await generatePasswordStandalone({
        length: 16,
        uppercase: true,
        numbers: true, 
        symbols: true
      });
      
      if (response.data && response.data.password) {
        handleChange('password', response.data.password);
        setShowPassword(true);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to generate password');
    }
  };
  
  const savePassword = async () => {
    // Validate required fields
    if (!formData.title) {
      Alert.alert('Error', 'Title is required');
      return;
    }
    
    if (!formData.password) {
      Alert.alert('Error', 'Password is required');
      return;
    }
    
    try {
      const response = await createPasswordDirect(formData);
      Alert.alert('Success', 'Password saved successfully');
      navigation.goBack();
    } catch (error) {
      console.error('Error saving password:', error);
      // Check if it's an authentication error
      if (error.response && error.response.status === 401) {
        Alert.alert('Authentication Error', 'Please log in to create passwords');
      } else {
        Alert.alert('Error', 'Failed to save password');
      }
    }
  };
  
  return (
    <View style={styles.container}>
      <View style={styles.formGroup}>
        <Text style={styles.label}>Title</Text>
        <TextInput
          style={styles.input}
          value={formData.title}
          onChangeText={(text) => handleChange('title', text)}
          placeholder="Enter title"
        />
      </View>
      
      <View style={styles.formGroup}>
        <Text style={styles.label}>Username</Text>
        <TextInput
          style={styles.input}
          value={formData.username}
          onChangeText={(text) => handleChange('username', text)}
          placeholder="Enter username"
        />
      </View>
      
      <View style={styles.formGroup}>
        <Text style={styles.label}>Email</Text>
        <TextInput
          style={styles.input}
          value={formData.email}
          onChangeText={(text) => handleChange('email', text)}
          placeholder="Enter email"
          keyboardType="email-address"
        />
      </View>
      
      <View style={styles.formGroup}>
        <Text style={styles.label}>Password</Text>
        <View style={styles.passwordContainer}>
          <TextInput
            style={styles.passwordInput}
            value={formData.password}
            onChangeText={(text) => handleChange('password', text)}
            placeholder="Enter password"
            secureTextEntry={!showPassword}
          />
          <TouchableOpacity 
            style={styles.passwordAction}
            onPress={() => setShowPassword(!showPassword)}
          >
            <Text>{showPassword ? 'Hide' : 'Show'}</Text>
          </TouchableOpacity>
          <TouchableOpacity 
            style={styles.passwordAction}
            onPress={generatePassword}
          >
            <Text>Generate</Text>
          </TouchableOpacity>
        </View>
      </View>
      
      <View style={styles.formGroup}>
        <Text style={styles.label}>Website URL</Text>
        <TextInput
          style={styles.input}
          value={formData.website_url}
          onChangeText={(text) => handleChange('website_url', text)}
          placeholder="Enter website URL"
          keyboardType="url"
        />
      </View>
      
      <View style={styles.formGroup}>
        <Text style={styles.label}>Notes</Text>
        <TextInput
          style={[styles.input, styles.textArea]}
          value={formData.notes}
          onChangeText={(text) => handleChange('notes', text)}
          placeholder="Enter notes"
          multiline
          numberOfLines={4}
        />
      </View>
      
      <View style={styles.formGroup}>
        <View style={styles.switchContainer}>
          <Text style={styles.label}>Mark as favorite</Text>
          <Switch
            value={formData.is_favorite}
            onValueChange={(value) => handleChange('is_favorite', value)}
          />
        </View>
      </View>
      
      <View style={styles.buttonContainer}>
        <TouchableOpacity 
          style={styles.cancelButton}
          onPress={() => navigation.goBack()}
        >
          <Text style={styles.cancelButtonText}>Cancel</Text>
        </TouchableOpacity>
        <TouchableOpacity 
          style={styles.saveButton}
          onPress={savePassword}
        >
          <Text style={styles.saveButtonText}>Save Password</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 16,
    backgroundColor: '#f8f8f8',
  },
  formGroup: {
    marginBottom: 16,
  },
  label: {
    fontSize: 16,
    fontWeight: '500',
    marginBottom: 8,
    color: '#333',
  },
  input: {
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  textArea: {
    height: 100,
    textAlignVertical: 'top',
  },
  passwordContainer: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  passwordInput: {
    flex: 1,
    backgroundColor: '#fff',
    borderWidth: 1,
    borderColor: '#ddd',
    borderRadius: 8,
    padding: 12,
    fontSize: 16,
  },
  passwordAction: {
    marginLeft: 8,
    paddingVertical: 8,
    paddingHorizontal: 12,
    backgroundColor: '#f0f0f0',
    borderRadius: 4,
  },
  switchContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 24,
  },
  cancelButton: {
    flex: 1,
    backgroundColor: '#f0f0f0',
    padding: 16,
    borderRadius: 8,
    marginRight: 8,
    alignItems: 'center',
  },
  cancelButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#666',
  },
  saveButton: {
    flex: 2,
    backgroundColor: '#007aff',
    padding: 16,
    borderRadius: 8,
    marginLeft: 8,
    alignItems: 'center',
  },
  saveButtonText: {
    fontSize: 16,
    fontWeight: '600',
    color: '#fff',
  },
});

export default CreatePasswordScreen;
```

## Security Considerations

1. **Token Storage**: Store JWT tokens securely using `react-native-keychain` or `expo-secure-store` rather than AsyncStorage for sensitive data.

2. **Encryption**: All sensitive data is encrypted server-side before storing in the database.

3. **Biometric Authentication**: Implement biometric authentication (fingerprint, face ID) for additional security:

```javascript
import * as LocalAuthentication from 'expo-local-authentication';

const authenticateWithBiometrics = async () => {
  const compatible = await LocalAuthentication.hasHardwareAsync();
  if (!compatible) {
    Alert.alert('Biometric authentication is not supported on this device');
    return false;
  }
  
  const enrolled = await LocalAuthentication.isEnrolledAsync();
  if (!enrolled) {
    Alert.alert('No biometrics enrolled on this device');
    return false;
  }
  
  const result = await LocalAuthentication.authenticateAsync({
    promptMessage: 'Authenticate to access your passwords',
    fallbackLabel: 'Use PIN'
  });
  
  return result.success;
};
```

4. **Clipboard Security**: Implement auto-clearing of clipboard:

```javascript
import Clipboard from '@react-native-clipboard/clipboard';

const copyToClipboard = (text) => {
  Clipboard.setString(text);
  
  // Set a timer to clear clipboard after 60 seconds
  setTimeout(() => {
    Clipboard.setString('');
  }, 60000);
  
  Alert.alert('Copied', 'Password copied to clipboard. Will clear in 60 seconds.');
};
```

5. **Session Timeout**: Implement automatic logout after inactivity:

```javascript
import { AppState } from 'react-native';

// In your App.js or authentication context
const [appState, setAppState] = useState(AppState.currentState);
const [lastActive, setLastActive] = useState(Date.now());
const TIMEOUT_DURATION = 5 * 60 * 1000; // 5 minutes

useEffect(() => {
  const subscription = AppState.addEventListener('change', nextAppState => {
    if (appState.match(/inactive|background/) && nextAppState === 'active') {
      const now = Date.now();
      if (now - lastActive > TIMEOUT_DURATION) {
        // Timeout exceeded, log the user out
        logout();
      }
    }
    setAppState(nextAppState);
    setLastActive(Date.now());
  });

  return () => {
    subscription.remove();
  };
}, [appState, lastActive]);
```

## Troubleshooting

1. **Authentication Issues**: If you get 401 Unauthorized errors:
   - Ensure the JWT token is included in all requests
   - Verify that the token isn't expired
   - Check if you're using the correct URLs for authentication
   - For development/testing only, you can use the `/password_management/api/mobile-create-password/` endpoint which doesn't require authentication

2. **CSRF Errors**: All password management API endpoints should be CSRF exempt. If you encounter CSRF errors, check that the endpoint is properly decorated with `@csrf_exempt` or the class with `@method_decorator(csrf_exempt, name='dispatch')`.

3. **Master Password Issues**: Some operations require a verified master password. If you get "Master password verification required" errors, call the verify master password endpoint first.

4. **Network Errors**: Ensure your React Native app has proper network permissions in the manifest files.

## Conclusion

This guide provides the foundation for integrating the password management system with your React Native application. Following these guidelines will help you create a secure and user-friendly password management experience for your users while maintaining compatibility with the web-based interface for testing and administration. 