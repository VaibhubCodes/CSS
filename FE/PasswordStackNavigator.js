// src/navigation/PasswordStackNavigator.js
import React, { useEffect, useState, useContext } from 'react';
import { createStackNavigator } from '@react-navigation/stack';
import { ActivityIndicator, View, Text, Alert } from 'react-native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import MasterPasswordSetupScreen from '../screens/password/MasterPasswordSetupScreen';
import VerifyMasterPasswordScreen from '../screens/password/VerifyMasterPasswordScreen';
import PasswordDashboardScreen from '../screens/password/PasswordDashboardScreen';
import PasswordListScreen from '../screens/password/PasswordListScreen';
import AddPasswordScreen from '../screens/password/AddPasswordScreen';
import PasswordDetailScreen from '../screens/password/PasswordDetailScreen'; // Create this if needed
// import SecuritySettingsScreen from '../screens/password/SecuritySettingsScreen'; // Placeholder

import { checkMasterPasswordStatus } from '../services/passwordService';
import { useMasterPassword } from '../context/MasterPasswordContext';
import { ThemeContext } from '../context/ThemeContext'; // Assuming you have this

const Stack = createStackNavigator();

// A simple Loading screen
const LoadingScreen = () => {
    const { theme } = useContext(ThemeContext);
    return (
        <View style={{ flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: theme.background }}>
            <ActivityIndicator size="large" color={theme.primary} />
            <Text style={{ marginTop: 10, color: theme.textSecondary }}>Checking security...</Text>
        </View>
    );
};


const PasswordStackNavigator = () => {
  const { theme } = useContext(ThemeContext);
  const { isMasterPasswordVerified, isLoadingMasterPasswordContext } = useMasterPassword();
  const [initialRouteName, setInitialRouteName] = useState(null); // null means loading
  const [masterPasswordIsSet, setMasterPasswordIsSet] = useState(null); // null means unknown

  useEffect(() => {
    const determineInitialRoute = async () => {
      try {
        const token = await AsyncStorage.getItem('accessToken'); // Ensure user is logged in
        if (!token) {
            Alert.alert("Authentication Error", "Please log in to access the password manager.");
            // Potentially navigate to LoginScreen if navigation is available here
            // For now, might be handled by a higher-level navigator
            setInitialRouteName('AuthErrorScreen'); // A placeholder, ideally handled by main app navigator
            return;
        }

        const statusData = await checkMasterPasswordStatus();
        setMasterPasswordIsSet(statusData.is_set);

        if (!statusData.is_set) {
          setInitialRouteName('MasterPasswordSetup');
        } else {
          // Master password is set, check if session is verified
          const validUntilStr = await AsyncStorage.getItem('masterPasswordValidUntil');
          const validUntil = Number(validUntilStr);
          if (validUntil && Date.now() < validUntil) {
            // Session is valid (or MasterPasswordContext will update it)
             setInitialRouteName('PasswordDashboard');
          } else {
            setInitialRouteName('VerifyMasterPassword');
          }
        }
      } catch (error) {
        console.error("Error determining initial password route:", error);
        Alert.alert("Error", "Could not determine password manager status. Please try again.");
        // Fallback or navigate out, e.g., to HomeScreen
        setInitialRouteName('PasswordDashboard'); // Fallback to dashboard, it will re-check
      }
    };

    // Only run if context is not loading and initial route hasn't been set
    if (!isLoadingMasterPasswordContext && initialRouteName === null) {
        determineInitialRoute();
    } else if (!isLoadingMasterPasswordContext && initialRouteName && masterPasswordIsSet !== null){
        // This condition ensures that if the context loads and tells us we are verified,
        // but initial check thought we need to verify, we can correct
        if(isMasterPasswordVerified && initialRouteName === 'VerifyMasterPassword'){
            console.log("Context says verified, overriding initial route to Dashboard");
            setInitialRouteName('PasswordDashboard');
        }
    }

  }, [isLoadingMasterPasswordContext, isMasterPasswordVerified, initialRouteName, masterPasswordIsSet]); // Re-run if context or status changes

  if (initialRouteName === null || isLoadingMasterPasswordContext) {
    return <LoadingScreen />;
  }

  return (
    <Stack.Navigator
      initialRouteName={initialRouteName}
      screenOptions={{
        headerStyle: { backgroundColor: theme.headerBackground || '#007AFF' },
        headerTintColor: theme.headerText || '#fff',
        headerTitleStyle: { fontWeight: 'bold' },
      }}
    >
      <Stack.Screen name="MasterPasswordSetup" component={MasterPasswordSetupScreen} options={{ title: 'Set Up Master Password', headerLeft: () => null }} />
      <Stack.Screen name="VerifyMasterPassword" component={VerifyMasterPasswordScreen} options={{ title: 'Verify Access', headerLeft: () => null }} />
      <Stack.Screen name="PasswordDashboard" component={PasswordDashboardScreen} options={{ title: 'Password Safe' }} />
      <Stack.Screen name="PasswordList" component={PasswordListScreen} options={({ route }) => ({ title: route.params?.filterLabel || 'Passwords' })} />
      <Stack.Screen name="AddPassword" component={AddPasswordScreen} options={{ title: 'Add New Item' }} />
      {/* <Stack.Screen name="PasswordDetail" component={PasswordDetailScreen} options={{ title: 'Item Details' }} /> */}
      {/* <Stack.Screen name="SecuritySettings" component={SecuritySettingsScreen} options={{ title: 'Security Settings' }} /> */}
    </Stack.Navigator>
  );
};

export default PasswordStackNavigator;