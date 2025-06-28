// src/services/passwordService.js
import apiClient from './apiClient';

// --- Master Password ---
export const checkMasterPasswordStatus = async () => {
  try {
    const response = await apiClient.get('/password_management/api/master-password/status/');
    return response.data; // Expected: { is_set: true/false }
  } catch (error) {
    console.error("Error checking master password status:", error.response?.data || error.message);
    throw error;
  }
};

export const setupMasterPassword = async (newPassword, confirmPassword) => {
  try {
    const response = await apiClient.post('/password_management/api/master-password/', {
      new_password: newPassword,
      confirm_password: confirmPassword,
    });
    return response.data; // Expected: { success: true, message: "...", created: true }
  } catch (error) {
    console.error("Error setting up master password:", error.response?.data || error.message);
    throw error;
  }
};

export const changeMasterPassword = async (currentPassword, newPassword, confirmPassword) => {
    try {
      const response = await apiClient.post('/password_management/api/master-password/', {
        current_password: currentPassword,
        new_password: newPassword,
        confirm_password: confirmPassword,
      });
      return response.data; // Expected: { success: true, message: "...", created: false }
    } catch (error) {
      console.error("Error changing master password:", error.response?.data || error.message);
      throw error;
    }
  };

export const verifyMasterPasswordApiCall = async (masterPassword) => {
  try {
    const response = await apiClient.post('/password_management/api/master-password/verify/', {
      master_password: masterPassword,
    });
    return response.data; // Expected: { success: true, message: "...", valid_until: timestamp }
  } catch (error) {
    console.error("Error verifying master password:", error.response?.data || error.message);
    throw error;
  }
};


// --- Password Entries & Categories (from your dashboard code) ---
export const getPasswordEntries = async (filters = {}) => {
  try {
    const params = new URLSearchParams();
    if (filters.category) params.append('category', filters.category);
    if (filters.type) params.append('type', filters.type);
    // Add other filters (search, favorites, sort) as needed based on API
    const response = await apiClient.get(`/password_management/api/mobile/entries/?${params.toString()}`);
    return response.data; // Backend returns array directly for mobile/entries
  } catch (error) {
    console.error("Error fetching password entries:", error.response?.data || error.message);
    throw error;
  }
};

export const fetchPasswordCategories = async () => {
  try {
    const response = await apiClient.get('/password_management/api/categories/');
    return response.data; // Backend returns array of categories
  } catch (error) {
    console.error("Error fetching password categories:", error.response?.data || error.message);
    throw error;
  }
};

export const createPasswordEntry = async (entryData) => {
  try {
    // Uses the authenticated endpoint that checks for master password existence
    const response = await apiClient.post('/password_management/api/create-password-entry/', entryData);
    return response.data;
  } catch (error) {
    console.error("Error creating password entry:", error.response?.data || error.message);
    throw error;
  }
};

// Add other password entry/category service functions as needed (getById, update, delete)