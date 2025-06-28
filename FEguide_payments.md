# Payments & Subscription System - React Native Integration Guide

This guide explains how to integrate the Payments and Subscription system with your React Native application. The system allows users to subscribe to different storage plans with Razorpay payment integration and provides premium features.

## Table of Contents

1. [Overview](#overview)
2. [API Endpoints](#api-endpoints)
3. [Installation & Setup](#installation--setup)
4. [Data Models](#data-models)
5. [Integration Steps](#integration-steps)
6. [UI Components](#ui-components)
7. [Payment Flow](#payment-flow)
8. [Example Code](#example-code)
9. [Error Handling](#error-handling)
10. [Testing](#testing)

## Overview

The Payment & Subscription system provides:

- **Multiple Subscription Plans**: Basic and Premium plans with different storage limits
- **Razorpay Integration**: Secure payment processing with Razorpay
- **Storage Management**: Automatic storage limit updates based on subscription
- **Premium Features**: Sparkle features for premium subscribers
- **Subscription Tracking**: Track active subscriptions and payment history

### Key Features

- 🔒 **Secure Payments**: Razorpay integration with signature verification
- 📊 **Flexible Plans**: Admin-configurable subscription plans
- 💾 **Storage Tiers**: Different storage limits per plan
- ⭐ **Premium Features**: Sparkle features for premium users
- 📱 **Mobile Optimized**: Dedicated mobile API endpoints
- 📈 **Analytics**: Payment transaction tracking

## API Endpoints

### Subscription Plans

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/payments/api/mobile/plans/` | GET | Get all active subscription plans | JWT Token |
| `/payments/api/plans/` | GET | Get subscription plans (DRF ViewSet) | JWT Token |
| `/payments/api/plans/active/` | GET | Get only active plans | JWT Token |

### Subscriptions

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/payments/api/subscriptions/` | GET | Get user's subscriptions | JWT Token |
| `/payments/api/subscriptions/current/` | GET | Get current active subscription | JWT Token |
| `/payments/api/subscriptions/create_order/` | POST | Create Razorpay order | JWT Token |
| `/payments/api/mobile/subscribe/` | POST | Mobile subscription creation | JWT Token |
| `/payments/api/user/subscription-info/` | GET | Get user subscription info | JWT Token |

### Payments

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/payments/api/verify-payment/` | POST | Verify payment signature | JWT Token |
| `/payments/api/transactions/` | GET | Get payment transactions | JWT Token |

## Installation & Setup

### 1. Install Dependencies

```bash
npm install react-native-razorpay
# For iOS
cd ios && pod install
```

### 2. Configure Razorpay

Add your Razorpay configuration to your app:

```javascript
// config/razorpay.js
export const RAZORPAY_CONFIG = {
  // Use test keys for development
  KEY_ID: 'rzp_test_your_key_id', // Replace with your actual key
  // Production keys should be stored securely
  PRODUCTION_KEY_ID: 'rzp_live_your_key_id',
};

export const getRazorpayKey = () => {
  return __DEV__ ? RAZORPAY_CONFIG.KEY_ID : RAZORPAY_CONFIG.PRODUCTION_KEY_ID;
};
```

### 3. Setup API Configuration

```javascript
// config/api.js
export const API_BASE_URL = 'https://your-api-domain.com';
export const PAYMENTS_API = {
  PLANS: '/payments/api/mobile/plans/',
  SUBSCRIBE: '/payments/api/mobile/subscribe/',
  VERIFY_PAYMENT: '/payments/api/verify-payment/',
  CURRENT_SUBSCRIPTION: '/payments/api/subscriptions/current/',
  USER_INFO: '/payments/api/user/subscription-info/',
};
```

## Data Models

### Subscription Plan Structure

```javascript
const subscriptionPlan = {
  id: 1,
  name: "Premium Plan",
  plan_code: "premium",
  description: "Premium features with 50GB storage",
  price: 299.00,
  storage_gb: 50,
  storage_bytes: 53687091200,
  is_sparkle: true,
  features: [
    "50GB Storage",
    "Premium OCR",
    "Voice Assistant",
    "Advanced Analytics"
  ],
  duration_days: 30,
  price_paise: 29900
};
```

### Subscription Structure

```javascript
const subscription = {
  id: 1,
  plan: 1,
  plan_details: {
    name: "Premium Plan",
    price: 299.00,
    storage_gb: 50,
    is_sparkle: true
  },
  status: "active",
  created_at: "2025-01-20T10:00:00Z",
  activated_at: "2025-01-20T10:05:00Z",
  valid_till: "2025-02-20T10:05:00Z",
  paid_amount: 299.00,
  is_sparkle_subscription: true
};
```

## Integration Steps

### 1. Create Payment Service

```javascript
// services/paymentService.js
import AsyncStorage from '@react-native-async-storage/async-storage';
import { API_BASE_URL, PAYMENTS_API } from '../config/api';

class PaymentService {
  async getAuthHeaders() {
    const token = await AsyncStorage.getItem('accessToken');
    return {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
    };
  }

  async getSubscriptionPlans() {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}${PAYMENTS_API.PLANS}`, {
        method: 'GET',
        headers,
      });

      const result = await response.json();
      if (result.success) {
        return {
          success: true,
          plans: result.plans
        };
      } else {
        throw new Error(result.error || 'Failed to fetch plans');
      }
    } catch (error) {
      console.error('Error fetching subscription plans:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  async createSubscription(planId) {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}${PAYMENTS_API.SUBSCRIBE}`, {
        method: 'POST',
        headers,
        body: JSON.stringify({ plan_id: planId }),
      });

      const result = await response.json();
      if (result.success) {
        return {
          success: true,
          orderData: result.order_data
        };
      } else {
        throw new Error(result.error || 'Failed to create subscription');
      }
    } catch (error) {
      console.error('Error creating subscription:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  async verifyPayment(paymentData) {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}${PAYMENTS_API.VERIFY_PAYMENT}`, {
        method: 'POST',
        headers,
        body: JSON.stringify(paymentData),
      });

      const result = await response.json();
      return result;
    } catch (error) {
      console.error('Error verifying payment:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  async getCurrentSubscription() {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}${PAYMENTS_API.CURRENT_SUBSCRIPTION}`, {
        method: 'GET',
        headers,
      });

      if (response.status === 404) {
        return {
          success: true,
          subscription: null
        };
      }

      const result = await response.json();
      return {
        success: true,
        subscription: result
      };
    } catch (error) {
      console.error('Error fetching current subscription:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }

  async getUserSubscriptionInfo() {
    try {
      const headers = await this.getAuthHeaders();
      const response = await fetch(`${API_BASE_URL}${PAYMENTS_API.USER_INFO}`, {
        method: 'GET',
        headers,
      });

      const result = await response.json();
      if (result.success) {
        return {
          success: true,
          info: result.data
        };
      } else {
        throw new Error(result.error || 'Failed to fetch user info');
      }
    } catch (error) {
      console.error('Error fetching user subscription info:', error);
      return {
        success: false,
        error: error.message
      };
    }
  }
}

export default new PaymentService();
```

### 2. Create Subscription Context

```javascript
// contexts/SubscriptionContext.js
import React, { createContext, useContext, useState, useEffect } from 'react';
import PaymentService from '../services/paymentService';

const SubscriptionContext = createContext();

export const useSubscription = () => {
  const context = useContext(SubscriptionContext);
  if (!context) {
    throw new Error('useSubscription must be used within a SubscriptionProvider');
  }
  return context;
};

export const SubscriptionProvider = ({ children }) => {
  const [currentSubscription, setCurrentSubscription] = useState(null);
  const [subscriptionPlans, setSubscriptionPlans] = useState([]);
  const [loading, setLoading] = useState(true);
  const [userInfo, setUserInfo] = useState(null);

  useEffect(() => {
    loadSubscriptionData();
  }, []);

  const loadSubscriptionData = async () => {
    setLoading(true);
    try {
      // Load subscription plans
      const plansResult = await PaymentService.getSubscriptionPlans();
      if (plansResult.success) {
        setSubscriptionPlans(plansResult.plans);
      }

      // Load current subscription
      const currentResult = await PaymentService.getCurrentSubscription();
      if (currentResult.success) {
        setCurrentSubscription(currentResult.subscription);
      }

      // Load user subscription info
      const userResult = await PaymentService.getUserSubscriptionInfo();
      if (userResult.success) {
        setUserInfo(userResult.info);
      }
    } catch (error) {
      console.error('Error loading subscription data:', error);
    } finally {
      setLoading(false);
    }
  };

  const refreshSubscription = async () => {
    const result = await PaymentService.getCurrentSubscription();
    if (result.success) {
      setCurrentSubscription(result.subscription);
    }
    
    const userResult = await PaymentService.getUserSubscriptionInfo();
    if (userResult.success) {
      setUserInfo(userResult.info);
    }
  };

  const isSparkleUser = () => {
    return currentSubscription?.is_sparkle_subscription || false;
  };

  const hasActiveSubscription = () => {
    return currentSubscription?.status === 'active';
  };

  const getStorageLimit = () => {
    return currentSubscription?.plan_details?.storage_gb || 5; // Default 5GB
  };

  const value = {
    currentSubscription,
    subscriptionPlans,
    userInfo,
    loading,
    refreshSubscription,
    isSparkleUser,
    hasActiveSubscription,
    getStorageLimit,
    loadSubscriptionData,
  };

  return (
    <SubscriptionContext.Provider value={value}>
      {children}
    </SubscriptionContext.Provider>
  );
};
```

## UI Components

### 1. Subscription Plans Screen

```javascript
// screens/SubscriptionPlansScreen.js
import React, { useState } from 'react';
import {
  View,
  Text,
  StyleSheet,
  ScrollView,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
} from 'react-native';
import RazorpayCheckout from 'react-native-razorpay';
import { useSubscription } from '../contexts/SubscriptionContext';
import PaymentService from '../services/paymentService';
import { getRazorpayKey } from '../config/razorpay';

const SubscriptionPlansScreen = ({ navigation }) => {
  const { subscriptionPlans, currentSubscription, refreshSubscription } = useSubscription();
  const [loading, setLoading] = useState(false);
  const [selectedPlan, setSelectedPlan] = useState(null);

  const handleSubscribe = async (plan) => {
    if (loading) return;
    
    setLoading(true);
    setSelectedPlan(plan);

    try {
      // Create subscription order
      const result = await PaymentService.createSubscription(plan.id);
      
      if (!result.success) {
        Alert.alert('Error', result.error);
        return;
      }

      // Prepare Razorpay options
      const options = {
        description: `Subscription to ${plan.name}`,
        image: 'https://your-logo-url.com/logo.png',
        currency: 'INR',
        key: getRazorpayKey(),
        amount: result.orderData.amount,
        order_id: result.orderData.order_id,
        name: 'Sparkle AI',
        prefill: {
          email: 'user@example.com',
          contact: '9999999999',
          name: 'User Name'
        },
        theme: { color: '#007AFF' }
      };

      // Open Razorpay checkout
      const paymentResult = await RazorpayCheckout.open(options);
      
      // Verify payment
      const verificationResult = await PaymentService.verifyPayment({
        razorpay_payment_id: paymentResult.razorpay_payment_id,
        razorpay_order_id: paymentResult.razorpay_order_id,
        razorpay_signature: paymentResult.razorpay_signature,
      });

      if (verificationResult.success) {
        Alert.alert(
          'Success!',
          'Your subscription has been activated successfully!',
          [
            {
              text: 'OK',
              onPress: () => {
                refreshSubscription();
                navigation.goBack();
              }
            }
          ]
        );
      } else {
        Alert.alert('Payment Verification Failed', verificationResult.error);
      }

    } catch (error) {
      console.error('Payment error:', error);
      Alert.alert('Payment Failed', error.description || 'Something went wrong');
    } finally {
      setLoading(false);
      setSelectedPlan(null);
    }
  };

  const PlanCard = ({ plan }) => {
    const isCurrentPlan = currentSubscription?.plan_details?.id === plan.id;
    const isLoading = loading && selectedPlan?.id === plan.id;

    return (
      <View style={[styles.planCard, isCurrentPlan && styles.currentPlanCard]}>
        <View style={styles.planHeader}>
          <Text style={styles.planName}>{plan.name}</Text>
          {plan.is_sparkle && (
            <View style={styles.sparkleTag}>
              <Text style={styles.sparkleText}>⭐ PREMIUM</Text>
            </View>
          )}
        </View>
        
        <Text style={styles.planPrice}>₹{plan.price}/month</Text>
        <Text style={styles.planDescription}>{plan.description}</Text>
        
        <View style={styles.featuresContainer}>
          <Text style={styles.featuresTitle}>Features:</Text>
          {plan.features.map((feature, index) => (
            <Text key={index} style={styles.featureItem}>• {feature}</Text>
          ))}
        </View>
        
        <TouchableOpacity
          style={[
            styles.subscribeButton,
            isCurrentPlan && styles.currentPlanButton,
            isLoading && styles.loadingButton
          ]}
          onPress={() => handleSubscribe(plan)}
          disabled={isCurrentPlan || isLoading}
        >
          {isLoading ? (
            <ActivityIndicator color="white" />
          ) : (
            <Text style={styles.subscribeButtonText}>
              {isCurrentPlan ? 'Current Plan' : 'Subscribe Now'}
            </Text>
          )}
        </TouchableOpacity>
      </View>
    );
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Choose Your Plan</Text>
      <Text style={styles.subtitle}>
        Upgrade your storage and unlock premium features
      </Text>
      
      {subscriptionPlans.map((plan) => (
        <PlanCard key={plan.id} plan={plan} />
      ))}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
    padding: 20,
  },
  title: {
    fontSize: 28,
    fontWeight: 'bold',
    textAlign: 'center',
    marginBottom: 8,
    color: '#333',
  },
  subtitle: {
    fontSize: 16,
    textAlign: 'center',
    color: '#666',
    marginBottom: 30,
  },
  planCard: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 20,
    marginBottom: 20,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  currentPlanCard: {
    borderWidth: 2,
    borderColor: '#007AFF',
  },
  planHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  planName: {
    fontSize: 22,
    fontWeight: 'bold',
    color: '#333',
  },
  sparkleTag: {
    backgroundColor: '#FFD700',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
  },
  sparkleText: {
    fontSize: 10,
    fontWeight: 'bold',
    color: '#333',
  },
  planPrice: {
    fontSize: 32,
    fontWeight: 'bold',
    color: '#007AFF',
    marginBottom: 8,
  },
  planDescription: {
    fontSize: 16,
    color: '#666',
    marginBottom: 20,
  },
  featuresContainer: {
    marginBottom: 20,
  },
  featuresTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  featureItem: {
    fontSize: 14,
    color: '#666',
    marginBottom: 4,
  },
  subscribeButton: {
    backgroundColor: '#007AFF',
    paddingVertical: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  currentPlanButton: {
    backgroundColor: '#28a745',
  },
  loadingButton: {
    backgroundColor: '#007AFF',
    opacity: 0.7,
  },
  subscribeButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default SubscriptionPlansScreen;
```

### 2. Subscription Status Component

```javascript
// components/SubscriptionStatus.js
import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity } from 'react-native';
import { useSubscription } from '../contexts/SubscriptionContext';

const SubscriptionStatus = ({ onUpgrade }) => {
  const { 
    currentSubscription, 
    hasActiveSubscription, 
    isSparkleUser, 
    getStorageLimit 
  } = useSubscription();

  if (!hasActiveSubscription()) {
    return (
      <View style={styles.container}>
        <View style={styles.freeUserContainer}>
          <Text style={styles.statusText}>Free Plan</Text>
          <Text style={styles.storageText}>5GB Storage</Text>
          <TouchableOpacity style={styles.upgradeButton} onPress={onUpgrade}>
            <Text style={styles.upgradeButtonText}>Upgrade Now</Text>
          </TouchableOpacity>
        </View>
      </View>
    );
  }

  const formatDate = (dateString) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    });
  };

  return (
    <View style={styles.container}>
      <View style={[
        styles.subscriptionContainer,
        isSparkleUser() && styles.premiumContainer
      ]}>
        <View style={styles.headerRow}>
          <Text style={styles.planName}>
            {currentSubscription.plan_details.name}
          </Text>
          {isSparkleUser() && (
            <Text style={styles.premiumBadge}>⭐ PREMIUM</Text>
          )}
        </View>
        
        <Text style={styles.storageText}>
          {getStorageLimit()}GB Storage
        </Text>
        
        <Text style={styles.validTill}>
          Valid till: {formatDate(currentSubscription.valid_till)}
        </Text>
        
        <TouchableOpacity style={styles.manageButton} onPress={onUpgrade}>
          <Text style={styles.manageButtonText}>Manage Subscription</Text>
        </TouchableOpacity>
      </View>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    margin: 20,
  },
  freeUserContainer: {
    backgroundColor: '#f8f9fa',
    padding: 20,
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#e9ecef',
    alignItems: 'center',
  },
  subscriptionContainer: {
    backgroundColor: '#007AFF',
    padding: 20,
    borderRadius: 12,
  },
  premiumContainer: {
    backgroundColor: '#FFD700',
  },
  headerRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  statusText: {
    fontSize: 18,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5,
  },
  planName: {
    fontSize: 20,
    fontWeight: 'bold',
    color: 'white',
  },
  premiumBadge: {
    fontSize: 12,
    fontWeight: 'bold',
    color: '#333',
  },
  storageText: {
    fontSize: 16,
    color: 'white',
    marginBottom: 10,
  },
  validTill: {
    fontSize: 14,
    color: 'rgba(255, 255, 255, 0.8)',
    marginBottom: 15,
  },
  upgradeButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
  },
  upgradeButtonText: {
    color: 'white',
    fontWeight: '600',
  },
  manageButton: {
    backgroundColor: 'rgba(255, 255, 255, 0.2)',
    paddingHorizontal: 20,
    paddingVertical: 10,
    borderRadius: 8,
    alignItems: 'center',
  },
  manageButtonText: {
    color: 'white',
    fontWeight: '600',
  },
});

export default SubscriptionStatus;
```

## Payment Flow

### Complete Payment Flow Implementation

```javascript
// hooks/usePaymentFlow.js
import { useState } from 'react';
import { Alert } from 'react-native';
import RazorpayCheckout from 'react-native-razorpay';
import PaymentService from '../services/paymentService';
import { getRazorpayKey } from '../config/razorpay';

export const usePaymentFlow = () => {
  const [loading, setLoading] = useState(false);

  const initiatePayment = async (plan, userInfo = {}) => {
    setLoading(true);
    
    try {
      // Step 1: Create subscription order
      const orderResult = await PaymentService.createSubscription(plan.id);
      
      if (!orderResult.success) {
        throw new Error(orderResult.error);
      }

      // Step 2: Prepare Razorpay options
      const options = {
        description: `Subscription to ${plan.name}`,
        image: 'https://your-logo-url.com/logo.png',
        currency: 'INR',
        key: getRazorpayKey(),
        amount: orderResult.orderData.amount,
        order_id: orderResult.orderData.order_id,
        name: 'Sparkle AI',
        prefill: {
          email: userInfo.email || 'user@example.com',
          contact: userInfo.phone || '9999999999',
          name: userInfo.name || 'User'
        },
        theme: { color: '#007AFF' },
        modal: {
          ondismiss: () => {
            console.log('Razorpay modal dismissed');
          }
        }
      };

      // Step 3: Open Razorpay checkout
      const paymentResult = await RazorpayCheckout.open(options);
      
      // Step 4: Verify payment
      const verificationResult = await PaymentService.verifyPayment({
        razorpay_payment_id: paymentResult.razorpay_payment_id,
        razorpay_order_id: paymentResult.razorpay_order_id,
        razorpay_signature: paymentResult.razorpay_signature,
      });

      if (verificationResult.success) {
        return {
          success: true,
          message: 'Subscription activated successfully!'
        };
      } else {
        throw new Error(verificationResult.error || 'Payment verification failed');
      }

    } catch (error) {
      console.error('Payment flow error:', error);
      
      // Handle different error types
      if (error.code === 'PAYMENT_CANCELLED') {
        return {
          success: false,
          cancelled: true,
          error: 'Payment was cancelled'
        };
      }
      
      return {
        success: false,
        error: error.description || error.message || 'Payment failed'
      };
    } finally {
      setLoading(false);
    }
  };

  return {
    initiatePayment,
    loading
  };
};
```

## Error Handling

### Common Error Scenarios

```javascript
// utils/paymentErrorHandler.js
export const handlePaymentError = (error) => {
  console.error('Payment error:', error);
  
  // Razorpay specific errors
  if (error.code) {
    switch (error.code) {
      case 'PAYMENT_CANCELLED':
        return 'Payment was cancelled by user';
      case 'NETWORK_ERROR':
        return 'Network error. Please check your internet connection';
      case 'INVALID_CREDENTIALS':
        return 'Invalid payment credentials';
      case 'PAYMENT_TIMEOUT':
        return 'Payment timed out. Please try again';
      default:
        return error.description || 'Payment failed';
    }
  }
  
  // API errors
  if (error.response) {
    const status = error.response.status;
    switch (status) {
      case 400:
        return 'Invalid request. Please check your details';
      case 401:
        return 'Authentication failed. Please login again';
      case 403:
        return 'Access denied';
      case 404:
        return 'Plan not found';
      case 500:
        return 'Server error. Please try again later';
      default:
        return 'Something went wrong. Please try again';
    }
  }
  
  return error.message || 'An unexpected error occurred';
};
```

## Testing

### Manual Testing Checklist

- [ ] Plans load correctly
- [ ] Payment modal opens
- [ ] Payment success flow works
- [ ] Payment failure is handled
- [ ] Subscription status updates
- [ ] Storage limit increases
- [ ] Premium features unlock
- [ ] Error messages are user-friendly

## Best Practices

### 1. Security

```javascript
// Never store sensitive data in AsyncStorage
// Use secure storage for sensitive data
import { Keychain } from 'react-native-keychain';

const storeSecureData = async (key, value) => {
  await Keychain.setInternetCredentials(key, 'user', value);
};
```

### 2. User Experience

```javascript
// Show loading states
const [paymentLoading, setPaymentLoading] = useState(false);

// Provide clear feedback
const showPaymentSuccess = () => {
  Alert.alert(
    '🎉 Success!',
    'Your subscription has been activated. Enjoy your premium features!',
    [{ text: 'Continue', onPress: () => navigation.goBack() }]
  );
};
```

### 3. Performance

```javascript
// Cache subscription data
const [cachedPlans, setCachedPlans] = useState(null);
const [lastFetch, setLastFetch] = useState(null);

const shouldRefreshPlans = () => {
  if (!lastFetch) return true;
  const timeDiff = Date.now() - lastFetch;
  return timeDiff > 5 * 60 * 1000; // 5 minutes
};
```

This guide provides a comprehensive integration approach for the payments and subscription system in your React Native application. Follow the examples and adapt them to your specific app structure and requirements. 