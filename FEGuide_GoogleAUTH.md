# Google Authentication Implementation Guide for React Native

This guide explains how to implement Google Sign-in in your React Native application to work with the Sparkle AI backend.

## Prerequisites

1. Make sure you have React Native environment set up
2. Access to Google Cloud Console
3. Backend API endpoint is properly configured and running

## Installation

1. Install the required package:
```bash
npm install @react-native-google-signin/google-signin
# or
yarn add @react-native-google-signin/google-signin
```

## Platform-Specific Setup

### Android Setup

1. In your Google Cloud Console:
   - Create/select your project
   - Enable Google Sign-In API
   - Create OAuth 2.0 client ID for Android
   - Add your SHA-1 and SHA-256 signing certificates

2. In `android/app/build.gradle`, add:
```gradle
dependencies {
    implementation 'com.google.android.gms:play-services-auth:20.7.0'
}
```

3. In `android/app/src/main/AndroidManifest.xml`, add:
```xml
<uses-permission android:name="android.permission.INTERNET" />
```

4. Create/update `android/app/src/main/res/values/strings.xml`:
```xml
<resources>
    <string name="app_name">YourAppName</string>
    <string name="server_client_id">YOUR_WEB_CLIENT_ID</string>
</resources>
```

### iOS Setup

1. In Google Cloud Console:
   - Create OAuth 2.0 client ID for iOS
   - Download `GoogleService-Info.plist`

2. Add `GoogleService-Info.plist` to your Xcode project:
   - Drag the file into your project in Xcode
   - Make sure "Copy items if needed" is checked
   - Add to your main target

3. Update `ios/Podfile`:
```ruby
target 'YourApp' do
  # ... other configurations
  pod 'GoogleSignIn'
end
```

4. Run:
```bash
cd ios && pod install
```

5. In `Info.plist`, add:
```xml
<key>CFBundleURLTypes</key>
<array>
    <dict>
        <key>CFBundleURLSchemes</key>
        <array>
            <string>YOUR_REVERSED_CLIENT_ID</string>
        </array>
    </dict>
</array>
```

## Implementation

### 1. Create Authentication Context

Create a new file `src/contexts/AuthContext.js`:

```javascript
import React, { createContext, useState, useContext } from 'react';
import { GoogleSignin } from '@react-native-google-signin/google-signin';
import AsyncStorage from '@react-native-async-storage/async-storage';

const AuthContext = createContext(null);

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  // Initialize Google Sign-In
  GoogleSignin.configure({
    // Get this from your Google Cloud Console
    webClientId: 'YOUR_WEB_CLIENT_ID',
    // Optional for iOS
    iosClientId: 'YOUR_IOS_CLIENT_ID',
    // Make sure offline access is enabled
    offlineAccess: true,
  });

  const signInWithGoogle = async () => {
    try {
      setLoading(true);
      setError(null);

      // Check if Play Services are available (Android only)
      await GoogleSignin.hasPlayServices();

      // Perform Google Sign-In
      const userInfo = await GoogleSignin.signIn();
      
      // Get tokens
      const { accessToken, idToken } = await GoogleSignin.getTokens();

      // Send to backend
      const response = await fetch('YOUR_API_URL/auth/api/mobile/google/', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          id_token: idToken,
          device_type: Platform.OS,
        }),
      });

      const data = await response.json();

      if (data.success) {
        // Store tokens
        await AsyncStorage.setItem('accessToken', data.tokens.access);
        await AsyncStorage.setItem('refreshToken', data.tokens.refresh);
        
        // Update user state
        setUser(data.user);
        return data;
      } else {
        throw new Error(data.error || 'Authentication failed');
      }
    } catch (error) {
      setError(error.message);
      throw error;
    } finally {
      setLoading(false);
    }
  };

  const signOut = async () => {
    try {
      // Sign out from Google
      await GoogleSignin.signOut();
      
      // Clear local storage
      await AsyncStorage.multiRemove(['accessToken', 'refreshToken']);
      
      // Reset state
      setUser(null);
    } catch (error) {
      setError(error.message);
      throw error;
    }
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        loading,
        error,
        signInWithGoogle,
        signOut,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};
```

### 2. Create a Google Sign-In Button Component

Create `src/components/GoogleSignInButton.js`:

```javascript
import React from 'react';
import { TouchableOpacity, Text, StyleSheet, ActivityIndicator } from 'react-native';
import { useAuth } from '../contexts/AuthContext';

export const GoogleSignInButton = () => {
  const { signInWithGoogle, loading } = useAuth();

  const handleSignIn = async () => {
    try {
      await signInWithGoogle();
      // Handle successful sign-in (e.g., navigation)
    } catch (error) {
      // Handle error (e.g., show error message)
      console.error('Google Sign-In Error:', error);
    }
  };

  return (
    <TouchableOpacity
      style={styles.button}
      onPress={handleSignIn}
      disabled={loading}
    >
      {loading ? (
        <ActivityIndicator color="#FFFFFF" />
      ) : (
        <Text style={styles.buttonText}>Sign in with Google</Text>
      )}
    </TouchableOpacity>
  );
};

const styles = StyleSheet.create({
  button: {
    backgroundColor: '#4285F4',
    padding: 12,
    borderRadius: 4,
    alignItems: 'center',
    marginVertical: 10,
  },
  buttonText: {
    color: '#FFFFFF',
    fontSize: 16,
    fontWeight: '600',
  },
});
```

### 3. Wrap Your App with AuthProvider

In your `App.js`:

```javascript
import React from 'react';
import { AuthProvider } from './src/contexts/AuthContext';

export default function App() {
  return (
    <AuthProvider>
      {/* Your app components */}
    </AuthProvider>
  );
}
```

### 4. Using the Authentication in Your Screens

Example usage in a login screen:

```javascript
import React from 'react';
import { View, StyleSheet } from 'react-native';
import { GoogleSignInButton } from '../components/GoogleSignInButton';
import { useAuth } from '../contexts/AuthContext';

export const LoginScreen = ({ navigation }) => {
  const { user } = useAuth();

  React.useEffect(() => {
    if (user) {
      // Navigate to home screen when user is authenticated
      navigation.replace('Home');
    }
  }, [user, navigation]);

  return (
    <View style={styles.container}>
      <GoogleSignInButton />
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
});
```

## Error Handling

The implementation includes basic error handling, but you should handle these specific cases:

1. Network errors
2. Invalid tokens
3. User cancellation
4. Play Services not available (Android)
5. Device-specific issues

Example error handling:

```javascript
import { statusCodes } from '@react-native-google-signin/google-signin';

try {
  await signInWithGoogle();
} catch (error) {
  switch (error.code) {
    case statusCodes.SIGN_IN_CANCELLED:
      // User cancelled the sign-in flow
      break;
    case statusCodes.IN_PROGRESS:
      // Operation in progress already
      break;
    case statusCodes.PLAY_SERVICES_NOT_AVAILABLE:
      // Play services not available or outdated
      break;
    default:
      // Other error
      break;
  }
}
```

## Token Refresh

Implement token refresh logic in your API service:

```javascript
const refreshTokens = async () => {
  try {
    const refreshToken = await AsyncStorage.getItem('refreshToken');
    
    const response = await fetch('YOUR_API_URL/auth/api/mobile/token/refresh/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        refresh_token: refreshToken,
      }),
    });

    const data = await response.json();
    
    if (data.success) {
      await AsyncStorage.setItem('accessToken', data.tokens.access);
      await AsyncStorage.setItem('refreshToken', data.tokens.refresh);
      return data.tokens.access;
    }
    
    throw new Error('Token refresh failed');
  } catch (error) {
    // Handle refresh token failure
    // Usually means we need to re-authenticate
    throw error;
  }
};
```

## Security Considerations

1. Never store sensitive information in plain text
2. Use secure storage for tokens
3. Implement proper token refresh mechanism
4. Handle token revocation
5. Implement proper logout flow
6. Use HTTPS for all API calls
7. Validate all responses from the backend

## Testing

1. Test on both Android and iOS devices
2. Test with different Google accounts
3. Test error scenarios
4. Test token refresh flow
5. Test offline behavior
6. Test sign-out flow

## Troubleshooting

Common issues and solutions:

1. **SHA-1/SHA-256 Mismatch**
   - Verify your signing certificates in Google Cloud Console
   - Make sure you're using the correct keystore

2. **iOS URL Scheme Issues**
   - Double-check your `GoogleService-Info.plist`
   - Verify URL schemes in `Info.plist`

3. **Android Play Services**
   - Make sure Google Play Services are up to date
   - Test on a device with Google Play Services installed

4. **Token Refresh Issues**
   - Implement proper error handling
   - Check token expiration times
   - Verify refresh token is stored correctly

## Additional Resources

- [Official Google Sign-In Documentation](https://developers.google.com/identity/sign-in/android/start-integrating)
- [React Native Google Sign-In Package](https://github.com/react-native-google-signin/google-signin)
- [Google Cloud Console](https://console.cloud.google.com/) 