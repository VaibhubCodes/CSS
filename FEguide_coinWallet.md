# Coin Wallet System - React Native Integration Guide

This guide explains how to integrate the Coin Wallet system with your React Native application. The system rewards users with coins (1 coin per MB) for file uploads, which can then be redeemed for benefits like increased storage space or premium features.

## Table of Contents

1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Integration Steps](#integration-steps)
4. [File Upload Integration](#file-upload-integration)
5. [Automatic Coin Awards System](#automatic-coin-awards-system)
6. [UI Components](#ui-components)
7. [Example Code](#example-code)
8. [Testing](#testing)

## Overview

The Coin Wallet system rewards users with coins based on the file size of their uploads. The conversion rate is 1 coin for every 1 MB uploaded (minimum 1 coin per file). Users can use these coins to:

- Increase storage space (10 coins = 1GB)
- Unlock premium features (cost varies)

## API Endpoints

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/coins/api/wallet/` | GET | Get current user's wallet info | JWT Token |
| `/coins/api/wallet/balance/` | GET | Get just the coin balance | JWT Token |
| `/coins/api/wallet/transactions/` | GET | Get transaction history | JWT Token |
| `/coins/api/wallet/redeem/` | POST | Redeem coins for benefits | JWT Token |
| `/coins/api/wallet/estimate/` | POST | Estimate coin earnings for a file | JWT Token |
| `/coins/api/award-coins/{file_id}/` | POST | Manually award coins for a file | JWT Token |
| `/coins/api/mobile-info/` | GET | Mobile-friendly wallet info | JWT Token |

## Integration Steps

### 1. Setup Authentication

Ensure all API requests include the JWT token in the Authorization header:

```javascript
const headers = {
  'Authorization': `Bearer ${jwtToken}`,
  'Content-Type': 'application/json'
};
```

### 2. Load Wallet Information

Add wallet info fetch to your app's initialization flow:

```javascript
// In a context provider or component
const fetchWalletInfo = async () => {
  try {
    const response = await fetch('https://your-api.com/coins/api/mobile-info/', {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${userToken}`,
      },
    });
    
    const result = await response.json();
    if (result.success) {
      setWalletInfo(result.data);
    } else {
      console.error('Failed to fetch wallet info:', result.error);
    }
  } catch (error) {
    console.error('Error fetching wallet info:', error);
  }
};
```

### 3. Display Coin Balance

Add a coin balance indicator to your app's navigation or profile screens:

```jsx
const CoinIndicator = ({ balance }) => (
  <View style={styles.coinContainer}>
    <Image source={require('./assets/coin-icon.png')} style={styles.coinIcon} />
    <Text style={styles.coinText}>{balance}</Text>
  </View>
);

// Styles
const styles = StyleSheet.create({
  coinContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#F8F1E0',
    borderRadius: 15,
    paddingHorizontal: 10,
    paddingVertical: 5,
    marginRight: 10,
  },
  coinIcon: {
    width: 20,
    height: 20,
    marginRight: 5,
  },
  coinText: {
    fontWeight: 'bold',
    color: '#DAA520',
  },
});
```

## File Upload Integration

The file upload process automatically awards coins. Your existing file upload function should be updated to handle and display the coin reward information.

### Updating File Upload

Modify your file upload functions to handle the coin reward response:

```javascript
const uploadFile = async (fileUri, fileType, categoryId = null) => {
  const formData = new FormData();
  
  // Get file name from URI
  const fileName = fileUri.split('/').pop();
  
  // Get file size for display
  const fileInfo = await FileSystem.getInfoAsync(fileUri);
  const fileSize = fileInfo.size;
  
  // Prepare form data
  formData.append('file', {
    uri: fileUri,
    type: getMimeType(fileUri),
    name: fileName,
  });
  formData.append('file_type', fileType);
  
  if (categoryId) {
    formData.append('category_id', categoryId);
  }
  
  try {
    const response = await fetch('https://your-api.com/file_management/mobile-upload/', {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${userToken}`,
        'Content-Type': 'multipart/form-data',
      },
      body: formData,
    });
    
    const result = await response.json();
    
    if (result.success) {
      // Handle file upload success
      
      // Process coin reward info if available
      if (result.coins && result.coins.success) {
        // Show coin earned notification
        showCoinRewardNotification(result.coins.coins_awarded, result.coins.wallet_balance);
        
        // Update wallet balance in app state
        updateWalletBalance(result.coins.wallet_balance);
      }
      
      return {
        success: true,
        fileId: result.file.id,
        fileUrl: result.file.file_url,
        ...result,
      };
    } else {
      throw new Error(result.error || 'Upload failed');
    }
  } catch (error) {
    console.error('Error uploading file:', error);
    return {
      success: false,
      error: error.message,
    };
  }
};
```

### Displaying Coin Rewards

After a successful upload, show a notification about earned coins:

```jsx
const showCoinRewardNotification = (coinsEarned, newBalance) => {
  // You can use your preferred notification library
  // Example with react-native-toast-message
  Toast.show({
    type: 'success',
    text1: '🎉 Coins Earned!',
    text2: `You earned ${coinsEarned} coins. New balance: ${newBalance}`,
    visibilityTime: 4000,
    autoHide: true,
  });
};
```

## Automatic Coin Awards System

The backend now features an automated coin award system that ensures coins are awarded immediately upon file upload. This eliminates the need for explicit API calls to award coins.

### How It Works

1. **Automatic Awarding**: When a file is uploaded, the system automatically:
   - Calculates coins based on file size (1 coin per MB, minimum 1 coin)
   - Awards the coins to the user's wallet
   - Creates a transaction record
   - Marks the file as having had coins awarded

2. **Handling Partial Megabytes**: The system uses `math.ceil()` to round up to the nearest MB, ensuring users get at least 1 coin per file and partial megabytes are counted as full coins.

3. **Preventing Duplicate Awards**: Each file tracks whether coins have been awarded with a `coins_awarded` flag, ensuring coins are only awarded once per file.

### Frontend Considerations

As a frontend developer, you should be aware of these changes:

1. **Response Format**: The file upload response now directly includes coin information in `result.coins`:
   ```javascript
   {
     success: true,
     file: { /* file details */ },
     coins: {
       success: true,
       message: "Successfully awarded 2 coins for file upload",
       coins_awarded: 2,
       current_balance: 24
     }
   }
   ```

2. **UI Updates**: Make sure your UI updates immediately after upload to reflect:
   - The new file being added to the list
   - The updated coin balance
   - A notification showing coins earned

3. **Error Handling**: If the coin award process fails, the file will still be uploaded, but `result.coins` might contain an error message. Consider how to handle this case in your UI.

## UI Components

### Coin Wallet Screen

Create a dedicated screen to display wallet info and transaction history:

```jsx
const CoinWalletScreen = () => {
  const [walletData, setWalletData] = useState(null);
  const [loading, setLoading] = useState(true);
  
  useEffect(() => {
    fetchWalletInfo();
  }, []);
  
  const fetchWalletInfo = async () => {
    setLoading(true);
    try {
      const response = await fetch('https://your-api.com/coins/api/mobile-info/', {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
      });
      
      const result = await response.json();
      if (result.success) {
        setWalletData(result.data);
      } else {
        Alert.alert('Error', result.error || 'Failed to load wallet information');
      }
    } catch (error) {
      console.error('Error fetching wallet info:', error);
      Alert.alert('Error', 'Network error. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  if (loading) {
    return <ActivityIndicator size="large" color="#DAA520" style={{ flex: 1, justifyContent: 'center' }} />;
  }
  
  if (!walletData) {
    return (
      <View style={styles.errorContainer}>
        <Text>Failed to load wallet information.</Text>
        <Button title="Retry" onPress={fetchWalletInfo} />
      </View>
    );
  }
  
  return (
    <View style={styles.container}>
      <View style={styles.balanceCard}>
        <Text style={styles.balanceLabel}>Coin Balance</Text>
        <Text style={styles.balanceAmount}>{walletData.balance}</Text>
        <Text style={styles.balanceInfo}>1 coin = 1MB uploaded</Text>
      </View>
      
      <View style={styles.statsContainer}>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>Total Earned</Text>
          <Text style={styles.statValue}>{walletData.stats.earned}</Text>
        </View>
        <View style={styles.statCard}>
          <Text style={styles.statLabel}>Total Spent</Text>
          <Text style={styles.statValue}>{walletData.stats.spent}</Text>
        </View>
      </View>
      
      <Text style={styles.sectionTitle}>Recent Transactions</Text>
      <FlatList
        data={walletData.recent_transactions}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <View style={styles.transactionItem}>
            <View>
              <Text style={styles.transactionType}>{item.transaction_type}</Text>
              <Text style={styles.transactionDate}>{formatDate(item.created_at)}</Text>
            </View>
            <Text 
              style={[
                styles.transactionAmount, 
                item.amount > 0 ? styles.positiveAmount : styles.negativeAmount
              ]}
            >
              {item.amount > 0 ? '+' : ''}{item.amount}
            </Text>
          </View>
        )}
        ListEmptyComponent={
          <Text style={styles.emptyList}>No transactions yet</Text>
        }
      />
      
      <TouchableOpacity 
        style={styles.redeemButton}
        onPress={() => navigation.navigate('RedeemCoins')}
      >
        <Text style={styles.redeemButtonText}>Redeem Coins</Text>
      </TouchableOpacity>
    </View>
  );
};
```

### Coin Redemption Screen

Create a screen for redeeming coins:

```jsx
const RedeemCoinsScreen = () => {
  const [walletBalance, setWalletBalance] = useState(0);
  const [storageAmount, setStorageAmount] = useState(10);
  const [premiumAmount, setPremiumAmount] = useState(20);
  const [loading, setLoading] = useState(false);
  
  useEffect(() => {
    fetchWalletBalance();
  }, []);
  
  const fetchWalletBalance = async () => {
    try {
      const response = await fetch('https://your-api.com/coins/api/wallet/balance/', {
        headers: {
          'Authorization': `Bearer ${userToken}`,
        },
      });
      
      const result = await response.json();
      setWalletBalance(result.balance);
    } catch (error) {
      console.error('Error fetching balance:', error);
      Alert.alert('Error', 'Failed to load your coin balance');
    }
  };
  
  const handleRedeem = async (type, amount) => {
    if (amount > walletBalance) {
      Alert.alert('Insufficient Coins', 'You don\'t have enough coins for this redemption.');
      return;
    }
    
    setLoading(true);
    try {
      const response = await fetch('https://your-api.com/coins/api/wallet/redeem/', {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${userToken}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount,
          redemption_type: type,
        }),
      });
      
      const result = await response.json();
      if (result.success) {
        Alert.alert('Success', result.message);
        setWalletBalance(result.remaining_balance);
      } else {
        Alert.alert('Error', result.error || 'Redemption failed');
      }
    } catch (error) {
      console.error('Error redeeming coins:', error);
      Alert.alert('Error', 'Network error. Please try again later.');
    } finally {
      setLoading(false);
    }
  };
  
  return (
    <View style={styles.container}>
      <Text style={styles.balanceText}>Current Balance: {walletBalance} coins</Text>
      
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Storage Increase</Text>
        <Text style={styles.cardDescription}>
          Exchange coins for additional storage space.{'\n'}
          10 coins = 1GB of storage
        </Text>
        
        <View style={styles.sliderContainer}>
          <Slider
            style={styles.slider}
            minimumValue={10}
            maximumValue={Math.max(10, walletBalance - (walletBalance % 10))}
            step={10}
            value={storageAmount}
            onValueChange={setStorageAmount}
            minimumTrackTintColor="#DAA520"
            maximumTrackTintColor="#d3d3d3"
            thumbTintColor="#DAA520"
          />
          <Text style={styles.sliderValue}>{storageAmount} coins = {storageAmount / 10} GB</Text>
        </View>
        
        <TouchableOpacity
          style={[
            styles.redeemButton,
            (storageAmount > walletBalance || walletBalance < 10) && styles.disabledButton
          ]}
          disabled={storageAmount > walletBalance || walletBalance < 10 || loading}
          onPress={() => handleRedeem('storage', storageAmount)}
        >
          <Text style={styles.redeemButtonText}>
            {loading ? 'Processing...' : 'Redeem for Storage'}
          </Text>
        </TouchableOpacity>
      </View>
      
      <View style={styles.card}>
        <Text style={styles.cardTitle}>Premium Features</Text>
        <Text style={styles.cardDescription}>
          Exchange coins for premium features like advanced OCR and priority processing.
        </Text>
        
        <View style={styles.sliderContainer}>
          <Slider
            style={styles.slider}
            minimumValue={20}
            maximumValue={Math.max(20, walletBalance)}
            step={1}
            value={premiumAmount}
            onValueChange={setPremiumAmount}
            minimumTrackTintColor="#DAA520"
            maximumTrackTintColor="#d3d3d3"
            thumbTintColor="#DAA520"
          />
          <Text style={styles.sliderValue}>{premiumAmount} coins</Text>
        </View>
        
        <TouchableOpacity
          style={[
            styles.redeemButton,
            (premiumAmount > walletBalance || walletBalance < 20) && styles.disabledButton
          ]}
          disabled={premiumAmount > walletBalance || walletBalance < 20 || loading}
          onPress={() => handleRedeem('premium', premiumAmount)}
        >
          <Text style={styles.redeemButtonText}>
            {loading ? 'Processing...' : 'Redeem for Premium'}
          </Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};
```

## Example Code

### Navigation Setup

Update your navigation to include the coin wallet screens:

```jsx
import { createStackNavigator } from '@react-navigation/stack';

const Stack = createStackNavigator();

function AppNavigator() {
  return (
    <Stack.Navigator>
      {/* Your existing screens */}
      <Stack.Screen 
        name="CoinWallet" 
        component={CoinWalletScreen} 
        options={{ title: 'Coin Wallet' }} 
      />
      <Stack.Screen 
        name="RedeemCoins" 
        component={RedeemCoinsScreen} 
        options={{ title: 'Redeem Coins' }} 
      />
    </Stack.Navigator>
  );
}
```

### API Client

Create a dedicated API client for the coin wallet system:

```javascript
// api/coinWallet.js
const API_BASE_URL = 'https://your-api.com';

export const CoinWalletAPI = {
  // Get wallet info with detailed stats and transactions
  getWalletInfo: async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/coins/api/mobile-info/`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return await response.json();
    } catch (error) {
      console.error('Error fetching wallet info:', error);
      throw error;
    }
  },
  
  // Get just the balance (lightweight call)
  getBalance: async (token) => {
    try {
      const response = await fetch(`${API_BASE_URL}/coins/api/wallet/balance/`, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return await response.json();
    } catch (error) {
      console.error('Error fetching balance:', error);
      throw error;
    }
  },
  
  // Get transaction history with pagination
  getTransactions: async (token, page = 1, pageSize = 20, type = null) => {
    try {
      let url = `${API_BASE_URL}/coins/api/wallet/transactions/?page=${page}&page_size=${pageSize}`;
      if (type) {
        url += `&type=${type}`;
      }
      
      const response = await fetch(url, {
        method: 'GET',
        headers: {
          'Authorization': `Bearer ${token}`,
        },
      });
      return await response.json();
    } catch (error) {
      console.error('Error fetching transactions:', error);
      throw error;
    }
  },
  
  // Redeem coins for benefits
  redeemCoins: async (token, amount, redemptionType) => {
    try {
      const response = await fetch(`${API_BASE_URL}/coins/api/wallet/redeem/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          amount,
          redemption_type: redemptionType,
        }),
      });
      return await response.json();
    } catch (error) {
      console.error('Error redeeming coins:', error);
      throw error;
    }
  },
  
  // Estimate coins to be earned for a file upload
  estimateCoins: async (token, fileSizeBytes) => {
    try {
      const response = await fetch(`${API_BASE_URL}/coins/api/wallet/estimate/`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          file_size_bytes: fileSizeBytes,
        }),
      });
      return await response.json();
    } catch (error) {
      console.error('Error estimating coins:', error);
      throw error;
    }
  },
};
```

### Context Provider

Create a context to manage coin wallet state globally:

```jsx
// context/CoinWalletContext.js
import React, { createContext, useState, useContext, useEffect } from 'react';
import { CoinWalletAPI } from '../api/coinWallet';
import { useAuth } from './AuthContext'; // Assuming you have an auth context

const CoinWalletContext = createContext();

export const CoinWalletProvider = ({ children }) => {
  const { token } = useAuth();
  const [balance, setBalance] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  const fetchBalance = async () => {
    if (!token) return;
    
    setLoading(true);
    try {
      const result = await CoinWalletAPI.getBalance(token);
      setBalance(result.balance);
      setError(null);
    } catch (err) {
      setError('Failed to load coin balance');
      console.error(err);
    } finally {
      setLoading(false);
    }
  };
  
  // Update balance when token changes
  useEffect(() => {
    if (token) {
      fetchBalance();
    }
  }, [token]);
  
  // Update balance after file upload
  const updateBalanceAfterUpload = (newBalance) => {
    setBalance(newBalance);
  };
  
  const value = {
    balance,
    loading,
    error,
    refreshBalance: fetchBalance,
    updateBalanceAfterUpload,
  };
  
  return (
    <CoinWalletContext.Provider value={value}>
      {children}
    </CoinWalletContext.Provider>
  );
};

export const useCoinWallet = () => {
  const context = useContext(CoinWalletContext);
  if (context === undefined) {
    throw new Error('useCoinWallet must be used within a CoinWalletProvider');
  }
  return context;
};
```

## Testing

To ensure proper integration, test the following scenarios:

1. **Balance Display**: Verify the coin balance displays correctly in the UI
2. **File Upload**: Test uploading files of various sizes and confirm coins are awarded correctly
3. **Transaction History**: Check that the transaction history displays properly
4. **Redemption**: Test redeeming coins for both storage and premium features
5. **Error Handling**: Validate error handling for insufficient balance, network issues, etc.

## Common Issues and Solutions

### Issue: Coins not awarded after file upload

**Solution**: 
- Ensure the backend is properly integrated with the coin wallet system
- Check that the response from the upload API includes the coin information
- Verify the JWT token is being passed correctly

### Issue: Balance not updating after redemption

**Solution**:
- Make sure to update the local state with the new balance returned from the redemption API
- Add a refresh mechanism to fetch the latest balance after redemption completes

### Issue: Redemption button disabled when it shouldn't be

**Solution**:
- Double-check the comparison logic for wallet balance vs. redemption amount
- Ensure wallet balance is being parsed as a number, not a string

## Conclusion

This coin wallet system provides a gamified experience that rewards users for file uploads and encourages them to use the platform more. The integration involves both UI components to display coin information and API calls to interact with the backend.

For further assistance, contact the backend team or refer to the API documentation. 