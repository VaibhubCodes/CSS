// src/screens/password/PasswordDashboardScreen.js
import React, { useEffect, useState, useContext, useCallback } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, FlatList,
  TextInput, Dimensions, Alert, ActivityIndicator, RefreshControl
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { useNavigation, useFocusEffect } from '@react-navigation/native';
import AsyncStorage from '@react-native-async-storage/async-storage';

import { ThemeContext } from '../../context/ThemeContext'; // Adjusted path
import PasswordNeumorphicView from '../../components/PasswordNeumorphicView'; // Adjusted path
import { getPasswordEntries, fetchPasswordCategories, checkMasterPasswordStatus } from '../../services/passwordService'; // Adjusted path
import { useMasterPassword } from '../../context/MasterPasswordContext'; // Adjusted path
// Removed apiClient import as specific service functions are preferred

const screenWidth = Dimensions.get('window').width;
const CARD_MARGIN = 12;
const NUM_COLUMNS = 2;
const CARD_WIDTH = '48%';

const PasswordDashboardScreen = () => {
  const navigation = useNavigation();
  const { theme } = useContext(ThemeContext);
  const { isMasterPasswordVerified, isLoadingMasterPasswordContext, setMasterPasswordSession } = useMasterPassword();

  const [allEntries, setAllEntries] = useState([]);
  const [passwordCategories, setPasswordCategories] = useState([]); // Renamed for clarity
  const [loadingData, setLoadingData] = useState(false);
  const [initialLoading, setInitialLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [refreshing, setRefreshing] = useState(false);


  const coreCategories = [ // These are entry_type filters
    { key: 'all', label: 'All Items', icon: 'key-variant', color: theme.accent || '#007BFF' },
    { key: 'password', label: 'Passwords', icon: 'lock-outline', color: theme.primary || '#FF3B30' },
    { key: 'passkey', label: 'Passkeys', icon: 'fingerprint', color: theme.green || '#34C759' },
    { key: 'wifi', label: 'Wi-Fi', icon: 'wifi', color: theme.blue || '#0A84FF' },
    { key: 'card', label: 'Cards', icon: 'credit-card-outline', color: theme.yellow || '#FFD60A' },
    { key: 'note', label: 'Notes', icon: 'note-text-outline', color: theme.orange || '#FF9F0A' },
    { key: 'identity', label: 'Identities', icon: 'account-box-outline', color: theme.purple || '#BF5AF2' },
  ];

  const loadPasswordData = useCallback(async () => {
    if (!isMasterPasswordVerified) {
      console.log("Master password not verified, skipping data load.");
      setAllEntries([]); // Clear data if not verified
      setPasswordCategories([]);
      return;
    }
    console.log("Master password verified, loading password data...");
    setLoadingData(true);
    try {
      // Fetch entries and categories in parallel
      const [entriesData, categoriesData] = await Promise.all([
        getPasswordEntries({ search: searchQuery }), // Pass search query
        fetchPasswordCategories()
      ]);
      setAllEntries(entriesData || []); // API returns array directly now
      setPasswordCategories(categoriesData || []);
    } catch (error) {
      Alert.alert('Error', 'Could not load password data.');
      console.error('Error loading password data:', error);
    } finally {
      setLoadingData(false);
      setRefreshing(false);
    }
  }, [isMasterPasswordVerified, searchQuery]); // Add searchQuery as dependency

  // Initial check and data loading logic
  const initialize = useCallback(async () => {
    setInitialLoading(true);
    try {
      const statusData = await checkMasterPasswordStatus();
      if (!statusData.is_set) {
        navigation.replace('MasterPasswordSetup');
        return;
      }

      // Check local session for master password
      const validUntilStr = await AsyncStorage.getItem('masterPasswordValidUntil');
      const validUntil = Number(validUntilStr);

      if (validUntil && Date.now() < validUntil) {
        console.log("Master password session is valid.");
        // Simulate setting it in context if not already (e.g., on app cold start)
        // This ensures `isMasterPasswordVerified` is true for loadPasswordData
        if (!isMasterPasswordVerified) {
            await setMasterPasswordSession(validUntil); // This will trigger context update
        }
        // loadPasswordData will be called by the useEffect watching isMasterPasswordVerified
      } else {
        console.log("Master password session expired or not found. Navigating to Verify screen.");
        navigation.replace('VerifyMasterPassword');
      }
    } catch (error) {
      console.error('Initialization error in PasswordDashboard:', error);
      Alert.alert('Error', 'Could not verify master password status. Please try again.');
      // Potentially navigate to a general error screen or back to HomeScreen
      navigation.navigate('HomeScreen');
    } finally {
      setInitialLoading(false);
    }
  }, [navigation, isMasterPasswordVerified, setMasterPasswordSession]); // Added dependencies


  // This effect runs when the screen comes into focus or when `initialize` changes
  useFocusEffect(initialize);

  // This effect runs when `isMasterPasswordVerified` changes (e.g., after successful verification)
  useEffect(() => {
    if (isMasterPasswordVerified && !initialLoading) { // Only load if verified and initial checks done
      loadPasswordData();
    }
  }, [isMasterPasswordVerified, loadPasswordData, initialLoading]);

  const onRefresh = useCallback(() => {
    setRefreshing(true);
    loadPasswordData(); // Reload data
  }, [loadPasswordData]);


  const getCountByCategory = (key) => {
    if (!allEntries || allEntries.length === 0) return 0;
    if (key === 'all') return allEntries.filter(entry => !entry.is_deleted).length; // Assuming is_deleted flag
    return allEntries.filter(entry => entry.entry_type === key && !entry.is_deleted).length;
  };

  const renderCategoryCard = ({ item }) => (
    <TouchableOpacity
      onPress={() => navigation.navigate('PasswordList', { filterType: item.key, filterLabel: item.label })}
      style={styles.cardWrapper}
    >
      <PasswordNeumorphicView theme={theme} style={styles.card}>
        <View style={styles.iconRow}>
          <Icon name={item.icon} size={26} color={item.color} />
          <Text style={[styles.count, { color: theme.textPrimary }]}>
            {getCountByCategory(item.key)}
          </Text>
        </View>
        <Text style={[styles.label, { color: theme.textPrimary }]}>{item.label}</Text>
      </PasswordNeumorphicView>
    </TouchableOpacity>
  );

  if (initialLoading || isLoadingMasterPasswordContext) {
    return (
      <View style={[styles.container, { justifyContent: 'center', alignItems: 'center', backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
        <Text style={{color: theme.textSecondary, marginTop: 10}}>Loading security status...</Text>
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Text style={[styles.title, { color: theme.textPrimary }]}>Passwords</Text>

      <View style={[styles.searchBox, { backgroundColor: theme.cardBackground, borderColor: theme.border, borderWidth: 1 }]}>
        <Icon name="magnify" size={20} color={theme.textTertiary} />
        <TextInput
          placeholder="Search all items..."
          placeholderTextColor={theme.textTertiary}
          style={[styles.searchInput, { color: theme.textPrimary }]}
          value={searchQuery}
          onChangeText={setSearchQuery}
          onSubmitEditing={loadPasswordData} // Trigger search on submit
          returnKeyType="search"
        />
      </View>

      <FlatList
        data={coreCategories}
        renderItem={renderCategoryCard}
        keyExtractor={(item) => item.key}
        numColumns={NUM_COLUMNS}
        contentContainerStyle={styles.grid}
        columnWrapperStyle={styles.row}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} colors={[theme.primary]} tintColor={theme.primary} />
        }
        ListEmptyComponent={loadingData ? <ActivityIndicator size="small" color={theme.primary} /> : <Text style={{color: theme.textSecondary, textAlign: 'center'}}>No categories to display.</Text>}
      />

      <PasswordNeumorphicView theme={theme} style={styles.fabOuter}>
        <TouchableOpacity
          onPress={() => navigation.navigate('AddPassword')}
          style={[styles.fabInner, {backgroundColor: theme.primary}]}
        >
          <Icon name="plus" size={28} color="#fff" />
        </TouchableOpacity>
      </PasswordNeumorphicView>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: CARD_MARGIN,
    paddingTop: 20,
  },
  title: {
    fontSize: 28,
    // fontFamily: 'Poppins-Bold', // Ensure this font is linked
    fontWeight: 'bold',
    marginBottom: 16,
  },
  searchBox: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 12,
    paddingVertical: 8,
    borderRadius: 12,
    marginBottom: 20,
    // elevation: 2, // Android shadow
    // shadowColor: '#000', // iOS shadow
    // shadowOffset: { width: 0, height: 1 },
    // shadowOpacity: 0.05,
    // shadowRadius: 2,
  },
  searchInput: {
    flex: 1,
    fontSize: 14,
    marginLeft: 10,
    // fontFamily: 'Poppins-Regular', // Ensure this font is linked
  },
  grid: {
    paddingBottom: 120, // Space for FAB
  },
  row: {
    justifyContent: 'space-between',
    marginBottom: CARD_MARGIN,
  },
  cardWrapper: {
    width: CARD_WIDTH,
  },
  card: { // Style for PasswordNeumorphicView content
    height: 100,
    padding: 16,
    borderRadius: 16, // Match NeumorphicView's expectation if any
    justifyContent: 'space-between',
  },
  iconRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  count: {
    fontSize: 16,
    // fontFamily: 'Poppins-Bold',
    fontWeight: 'bold',
  },
  label: {
    fontSize: 14,
    // fontFamily: 'Poppins-Regular',
    marginTop: 8,
  },
  fabOuter: { // Style for the outer NeumorphicView of FAB
    position: 'absolute',
    bottom: 30,
    right: 30,
    width: 70,
    height: 70,
    borderRadius: 35, // Half of width/height
    justifyContent: 'center',
    alignItems: 'center',
  },
  fabInner: { // Style for the actual TouchableOpacity inside
    width: 56,
    height: 56,
    borderRadius: 28,
    justifyContent: 'center',
    alignItems: 'center',
  },
});

export default PasswordDashboardScreen;