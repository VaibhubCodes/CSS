// src/screens/password/MasterPasswordSetupScreen.js
import React, { useState, useContext } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator } from 'react-native';
import { useNavigation } from '@react-navigation/native';
import { setupMasterPassword, verifyMasterPasswordApiCall } from '../../services/passwordService';
import { useMasterPassword } from '../../context/MasterPasswordContext';
import { ThemeContext } from '../../context/ThemeContext'; // Assuming you have this

const MasterPasswordSetupScreen = () => {
  const navigation = useNavigation();
  const { theme } = useContext(ThemeContext); // Assuming you use a theme
  const { setMasterPasswordSession } = useMasterPassword();
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleSetup = async () => {
    if (newPassword.length < 8) {
      setError('Password must be at least 8 characters long.');
      return;
    }
    if (newPassword !== confirmPassword) {
      setError('Passwords do not match.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const setupResponse = await setupMasterPassword(newPassword, confirmPassword);
      if (setupResponse.success) {
        Alert.alert('Success', 'Master password set successfully!');
        // Immediately verify to establish the session
        const verifyResponse = await verifyMasterPasswordApiCall(newPassword);
        if (verifyResponse.success && verifyResponse.valid_until) {
          await setMasterPasswordSession(verifyResponse.valid_until);
          navigation.replace('PasswordDashboard'); // Navigate to dashboard
        } else {
           Alert.alert('Error', 'Could not verify new master password. Please try logging in to the password manager again.');
           navigation.navigate('HomeScreen'); // Or back to a main app screen
        }
      } else {
        setError(setupResponse.error || setupResponse.new_password || 'Failed to set master password.');
      }
    } catch (err) {
      console.error("Master password setup error:", err);
      setError(err.response?.data?.error || err.response?.data?.new_password || 'An unexpected error occurred.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Text style={[styles.title, { color: theme.textPrimary }]}>Set Up Master Password</Text>
      <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
        This password will protect all your stored credentials. Choose a strong, unique password.
      </Text>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <TextInput
        style={[styles.input, { backgroundColor: theme.cardBackground, color: theme.textPrimary, borderColor: theme.border }]}
        placeholder="New Master Password"
        placeholderTextColor={theme.textSecondary}
        secureTextEntry
        value={newPassword}
        onChangeText={setNewPassword}
        autoCapitalize="none"
      />
      <TextInput
        style={[styles.input, { backgroundColor: theme.cardBackground, color: theme.textPrimary, borderColor: theme.border }]}
        placeholder="Confirm Master Password"
        placeholderTextColor={theme.textSecondary}
        secureTextEntry
        value={confirmPassword}
        onChangeText={setConfirmPassword}
        autoCapitalize="none"
      />

      <TouchableOpacity
        style={[styles.button, { backgroundColor: theme.primary }]}
        onPress={handleSetup}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Set Master Password</Text>
        )}
      </TouchableOpacity>
      <TouchableOpacity
        style={[styles.button, styles.cancelButton, {borderColor: theme.primary}]}
        onPress={() => navigation.navigate('HomeScreen')} // Or appropriate back navigation
        disabled={loading}
      >
          <Text style={[styles.buttonText, styles.cancelButtonText, {color: theme.primary}]}>Cancel & Go Home</Text>
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 10,
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    marginBottom: 30,
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 15,
    marginBottom: 20,
    fontSize: 16,
  },
  button: {
    height: 50,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
    marginBottom: 15,
  },
  buttonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  cancelButton: {
    backgroundColor: 'transparent',
    borderWidth: 1,
  },
  cancelButtonText: {
    // color will be set by theme
  },
  errorText: {
    color: 'red',
    textAlign: 'center',
    marginBottom: 15,
  },
});

export default MasterPasswordSetupScreen;