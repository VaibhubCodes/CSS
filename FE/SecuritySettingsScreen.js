// src/screens/password/SecuritySettingsScreen.js
import React, { useState, useEffect, useContext, useCallback } from 'react';
import {
  View, Text, StyleSheet, ScrollView, Switch, TouchableOpacity,
  ActivityIndicator, Alert, TextInput
} from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';

import { ThemeContext } from '../../context/ThemeContext';
import { useMasterPassword } from '../../context/MasterPasswordContext';
import {
  getSecuritySettings as fetchSecuritySettings,
  updateSecuritySettings as saveSecuritySettings,
  changeMasterPassword, // Assuming you'll add/use this from passwordService
} from '../../services/passwordService'; // Assuming you have this
import apiClient from '../../services/apiClient'; // For direct API calls if needed

const SecuritySettingsScreen = () => {
  const navigation = useNavigation();
  const { theme } = useContext(ThemeContext);
  const { isMasterPasswordVerified, clearMasterPasswordSession } = useMasterPassword();

  const [settings, setSettings] = useState({
    check_for_compromised: true,
    suggest_strong_passwords: true,
    min_password_length: 12,
    password_require_uppercase: true,
    password_require_numbers: true,
    password_require_symbols: true,
    auto_fill_enabled: true, // This might be more of a device/OS level setting
  });
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  // State for changing master password modal (if you implement it here)
  const [showMasterPasswordModal, setShowMasterPasswordModal] = useState(false);
  const [currentMasterPassword, setCurrentMasterPassword] = useState('');
  const [newMasterPassword, setNewMasterPassword] = useState('');
  const [confirmNewMasterPassword, setConfirmNewMasterPassword] = useState('');
  const [masterPasswordError, setMasterPasswordError] = useState('');

  const loadSettings = useCallback(async () => {
    if (!isMasterPasswordVerified) {
      Alert.alert("Access Denied", "Please verify your master password to access security settings.");
      navigation.goBack();
      return;
    }
    setLoading(true);
    try {
      const response = await fetchSecuritySettings();
      if (response) { // Assuming API returns the settings object directly
        setSettings(prev => ({ ...prev, ...response })); // Merge with defaults
      }
    } catch (error) {
      console.error("Failed to load security settings:", error);
      Alert.alert("Error", "Could not load security settings.");
    } finally {
      setLoading(false);
    }
  }, [isMasterPasswordVerified, navigation]);

  useFocusEffect(loadSettings);

  const handleSettingChange = (key, value) => {
    setSettings(prev => ({ ...prev, [key]: value }));
  };

  const handleSaveSettings = async () => {
    setSaving(true);
    try {
      const response = await saveSecuritySettings(settings);
      if (response) { // Assuming API returns updated settings or success message
        Alert.alert("Success", "Security settings updated successfully.");
      } else {
        Alert.alert("Error", "Failed to update settings.");
      }
    } catch (error) {
      console.error("Failed to save security settings:", error);
      Alert.alert("Error", error.response?.data?.error || "Could not save security settings.");
    } finally {
      setSaving(false);
    }
  };

  const handleChangeMasterPassword = async () => {
    if (newMasterPassword.length < 8) {
        setMasterPasswordError("New password must be at least 8 characters.");
        return;
    }
    if (newMasterPassword !== confirmNewMasterPassword) {
        setMasterPasswordError("New passwords do not match.");
        return;
    }
    setMasterPasswordError('');
    setSaving(true);
    try {
        const response = await changeMasterPassword(currentMasterPassword, newMasterPassword, confirmNewMasterPassword);
        if (response.success) {
            Alert.alert("Success", response.message || "Master password changed successfully. Please re-verify.");
            setShowMasterPasswordModal(false);
            await clearMasterPasswordSession(); // Force re-verification
            navigation.replace('VerifyMasterPassword'); // Navigate to verify screen
        } else {
            setMasterPasswordError(response.error || response.current_password || response.new_password || "Failed to change master password.");
        }
    } catch (err) {
        console.error("Change master password error:", err);
        setMasterPasswordError(err.response?.data?.error || err.response?.data?.current_password || "An error occurred.");
    } finally {
        setSaving(false);
        setCurrentMasterPassword('');
        setNewMasterPassword('');
        setConfirmNewMasterPassword('');
    }
  };


  if (loading) {
    return (
      <View style={[styles.fullScreenLoader, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

  const renderSwitchSetting = (key, label, description) => (
    <View style={styles.settingRow}>
      <View style={styles.settingTextContainer}>
        <Text style={[styles.settingLabel, { color: theme.textPrimary }]}>{label}</Text>
        {description && <Text style={[styles.settingDescription, { color: theme.textSecondary }]}>{description}</Text>}
      </View>
      <Switch
        trackColor={{ false: theme.grey, true: theme.primaryFaded }}
        thumbColor={settings[key] ? theme.primary : theme.thumbOff}
        ios_backgroundColor={theme.grey}
        onValueChange={(value) => handleSettingChange(key, value)}
        value={settings[key]}
      />
    </View>
  );

  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.background }]} contentContainerStyle={styles.scrollContent}>
      <Text style={[styles.header, { color: theme.textPrimary }]}>Security Settings</Text>

      <View style={[styles.section, { backgroundColor: theme.cardBackground, borderColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.textPrimary }]}>Password Checks</Text>
        {renderSwitchSetting('check_for_compromised', 'Check for Compromised Passwords', 'Warn if your passwords appear in known data breaches.')}
        {renderSwitchSetting('suggest_strong_passwords', 'Suggest Strong Passwords', 'Offer strong password suggestions during creation.')}
      </View>

      <View style={[styles.section, { backgroundColor: theme.cardBackground, borderColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.textPrimary }]}>Password Policy</Text>
        <View style={styles.settingRow}>
            <Text style={[styles.settingLabel, { color: theme.textPrimary }]}>Minimum Password Length</Text>
            <TextInput
                style={[styles.numericInput, {color: theme.textPrimary, borderColor: theme.border}]}
                value={String(settings.min_password_length)}
                onChangeText={(text) => handleSettingChange('min_password_length', parseInt(text, 10) || 8)}
                keyboardType="number-pad"
                maxLength={2}
            />
        </View>
        {renderSwitchSetting('password_require_uppercase', 'Require Uppercase Letters')}
        {renderSwitchSetting('password_require_numbers', 'Require Numbers')}
        {renderSwitchSetting('password_require_symbols', 'Require Special Characters')}
      </View>

      <View style={[styles.section, { backgroundColor: theme.cardBackground, borderColor: theme.border }]}>
        <Text style={[styles.sectionTitle, { color: theme.textPrimary }]}>Device & App</Text>
        {renderSwitchSetting('auto_fill_enabled', 'Enable Auto-fill (Conceptual)', 'Note: Actual auto-fill relies on OS capabilities and may need further platform-specific setup.')}
        
        <TouchableOpacity
            style={[styles.button, styles.changeMasterPasswordButton, { borderColor: theme.primary, marginTop: 15 }]}
            onPress={() => {
                // For simplicity, we'll navigate to a dedicated screen or implement a modal here.
                // Let's assume we'll use a modal embedded in this screen for now.
                setShowMasterPasswordModal(true);
            }}
        >
            <Icon name="shield-key-outline" size={20} color={theme.primary} style={{marginRight: 5}}/>
            <Text style={[styles.buttonText, { color: theme.primary }]}>Change Master Password</Text>
        </TouchableOpacity>
      </View>


      <TouchableOpacity
        style={[styles.button, { backgroundColor: theme.primary, marginTop: 30 }]}
        onPress={handleSaveSettings}
        disabled={saving || loading}
      >
        {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.buttonText}>Save Settings</Text>}
      </TouchableOpacity>

      {/* Change Master Password Modal */}
      {/* You would typically use a proper Modal component from React Native or a library */}
      {showMasterPasswordModal && (
        <View style={styles.modalOverlay}>
            <View style={[styles.modalContainer, {backgroundColor: theme.cardBackground}]}>
                <Text style={[styles.modalTitle, {color: theme.textPrimary}]}>Change Master Password</Text>
                {masterPasswordError ? <Text style={styles.errorTextModal}>{masterPasswordError}</Text> : null}
                <TextInput
                    style={[styles.modalInput, {backgroundColor: theme.inputBackground, color: theme.textPrimary, borderColor: theme.border}]}
                    placeholder="Current Master Password"
                    placeholderTextColor={theme.textSecondary}
                    secureTextEntry
                    value={currentMasterPassword}
                    onChangeText={setCurrentMasterPassword}
                />
                <TextInput
                    style={[styles.modalInput, {backgroundColor: theme.inputBackground, color: theme.textPrimary, borderColor: theme.border}]}
                    placeholder="New Master Password"
                    placeholderTextColor={theme.textSecondary}
                    secureTextEntry
                    value={newMasterPassword}
                    onChangeText={setNewMasterPassword}
                />
                <TextInput
                    style={[styles.modalInput, {backgroundColor: theme.inputBackground, color: theme.textPrimary, borderColor: theme.border}]}
                    placeholder="Confirm New Master Password"
                    placeholderTextColor={theme.textSecondary}
                    secureTextEntry
                    value={confirmNewMasterPassword}
                    onChangeText={setConfirmNewMasterPassword}
                />
                <View style={styles.modalButtonRow}>
                    <TouchableOpacity
                        style={[styles.modalButton, {backgroundColor: theme.grey}]}
                        onPress={() => {
                            setShowMasterPasswordModal(false);
                            setMasterPasswordError('');
                            setCurrentMasterPassword(''); setNewMasterPassword(''); setConfirmNewMasterPassword('');
                        }}
                        disabled={saving}
                    >
                        <Text style={[styles.modalButtonText, {color: theme.textPrimary}]}>Cancel</Text>
                    </TouchableOpacity>
                    <TouchableOpacity
                        style={[styles.modalButton, {backgroundColor: theme.primary}]}
                        onPress={handleChangeMasterPassword}
                        disabled={saving}
                    >
                        {saving ? <ActivityIndicator color="#fff" /> : <Text style={styles.modalButtonText}>Change</Text>}
                    </TouchableOpacity>
                </View>
            </View>
        </View>
      )}

    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  scrollContent: {
    padding: 20,
  },
  fullScreenLoader: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  header: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  section: {
    marginBottom: 25,
    padding: 15,
    borderRadius: 12,
    borderWidth: 1,
    // shadowColor: '#000',
    // shadowOffset: { width: 0, height: 1 },
    // shadowOpacity: 0.05,
    // shadowRadius: 2,
    // elevation: 1,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 15,
    paddingBottom: 10,
    borderBottomWidth: 1,
    borderBottomColor: '#eee', // Use theme.border
  },
  settingRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0', // Use theme.borderLighter
  },
  settingTextContainer: {
    flex: 1,
    marginRight: 10,
  },
  settingLabel: {
    fontSize: 16,
  },
  settingDescription: {
    fontSize: 12,
    marginTop: 3,
  },
  numericInput: {
    width: 50,
    textAlign: 'center',
    borderWidth: 1,
    borderRadius: 5,
    paddingVertical: 5,
    fontSize: 16,
  },
  button: {
    height: 50,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    flexDirection: 'row',
  },
  buttonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '600',
  },
  changeMasterPasswordButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
  },
  // Modal Styles
  modalOverlay: {
    position: 'absolute',
    top: 0, left: 0, right: 0, bottom: 0,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
    zIndex: 1000, // Ensure it's on top
  },
  modalContainer: {
    width: '90%',
    maxWidth: 400,
    borderRadius: 12,
    padding: 20,
    // elevation: 10,
    // shadowColor: '#000',
    // shadowOffset: { width: 0, height: 2 },
    // shadowOpacity: 0.25,
    // shadowRadius: 4,
  },
  modalTitle: {
    fontSize: 20,
    fontWeight: 'bold',
    marginBottom: 15,
    textAlign: 'center',
  },
  modalInput: {
    height: 45,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 12,
    marginBottom: 12,
    fontSize: 15,
  },
  modalButtonRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    marginTop: 10,
  },
  modalButton: {
    flex: 1,
    height: 45,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginHorizontal: 5,
  },
  modalButtonText: {
    fontSize: 16,
    fontWeight: '600',
  },
  errorTextModal: {
    color: 'red',
    textAlign: 'center',
    marginBottom: 10,
    fontSize: 14,
  }
});

export default SecuritySettingsScreen;