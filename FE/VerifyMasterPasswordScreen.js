// src/screens/password/VerifyMasterPasswordScreen.js
import React, { useState, useContext, useEffect } from 'react';
import { View, Text, TextInput, TouchableOpacity, StyleSheet, Alert, ActivityIndicator, BackHandler } from 'react-native';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import { verifyMasterPasswordApiCall } from '../../services/passwordService';
import { useMasterPassword } from '../../context/MasterPasswordContext';
import { ThemeContext } from '../../context/ThemeContext';

const VerifyMasterPasswordScreen = () => {
  const navigation = useNavigation();
  const { theme } = useContext(ThemeContext);
  const { setMasterPasswordSession } = useMasterPassword();
  const [masterPassword, setMasterPassword] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');

  const handleVerify = async () => {
    if (!masterPassword) {
      setError('Please enter your master password.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const response = await verifyMasterPasswordApiCall(masterPassword);
      if (response.success && response.valid_until) {
        await setMasterPasswordSession(response.valid_until);
        navigation.replace('PasswordDashboard'); // Go to dashboard on success
      } else {
        setError(response.error || response.master_password || 'Incorrect master password.');
      }
    } catch (err) {
      console.error("Master password verification error:", err);
      setError(err.response?.data?.error || err.response?.data?.master_password || 'Verification failed. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  // Handle Android back press to go to HomeScreen
  useFocusEffect(
    React.useCallback(() => {
      const onBackPress = () => {
        Alert.alert(
          "Exit Password Manager?",
          "You'll need to verify your master password again to access.",
          [
            { text: "Cancel", style: "cancel", onPress: () => {} },
            {
              text: "Exit to Home",
              style: "destructive",
              onPress: () => navigation.navigate('HomeScreen'), // Navigate to your main app home
            },
          ]
        );
        return true; // Prevent default back action
      };

      BackHandler.addEventListener('hardwareBackPress', onBackPress);
      return () => BackHandler.removeEventListener('hardwareBackPress', onBackPress);
    }, [navigation])
  );


  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Text style={[styles.title, { color: theme.textPrimary }]}>Verify Master Password</Text>
      <Text style={[styles.subtitle, { color: theme.textSecondary }]}>
        Enter your master password to continue.
      </Text>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <TextInput
        style={[styles.input, { backgroundColor: theme.cardBackground, color: theme.textPrimary, borderColor: theme.border }]}
        placeholder="Master Password"
        placeholderTextColor={theme.textSecondary}
        secureTextEntry
        value={masterPassword}
        onChangeText={setMasterPassword}
        onSubmitEditing={handleVerify}
        autoCapitalize="none"
      />

      <TouchableOpacity
        style={[styles.button, { backgroundColor: theme.primary }]}
        onPress={handleVerify}
        disabled={loading}
      >
        {loading ? (
          <ActivityIndicator color="#fff" />
        ) : (
          <Text style={styles.buttonText}>Unlock</Text>
        )}
      </TouchableOpacity>

       <TouchableOpacity
        style={[styles.button, styles.cancelButton, {borderColor: theme.primary}]}
        onPress={() => {
            Alert.alert(
                "Exit Confirmation",
                "Are you sure you want to exit? You will be returned to the home screen.",
                [
                    { text: "Stay", style: "cancel" },
                    { text: "Exit to Home", onPress: () => navigation.navigate('HomeScreen') } // Or your main app's home
                ]
            );
        }}
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

export default VerifyMasterPasswordScreen;