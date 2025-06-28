// src/screens/password/PasswordListScreen.js
import React, { useEffect, useState, useCallback, useContext } from 'react';
import { View, Text, FlatList, TouchableOpacity, StyleSheet, ActivityIndicator, Alert, TextInput } from 'react-native';
import { useNavigation, useRoute, useFocusEffect } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { getPasswordEntries } from '../../services/passwordService';
import { ThemeContext } from '../../context/ThemeContext';
import { useMasterPassword } from '../../context/MasterPasswordContext';

const PasswordListScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { theme } = useContext(ThemeContext);
  const { isMasterPasswordVerified } = useMasterPassword();

  const filterTypeFromRoute = route.params?.filterType; // e.g., 'password', 'wifi', 'all'
  const filterLabelFromRoute = route.params?.filterLabel || 'Items';

  const [entries, setEntries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredEntries, setFilteredEntries] = useState([]);

  const fetchEntries = useCallback(async () => {
    if (!isMasterPasswordVerified) {
        Alert.alert("Access Denied", "Master password not verified.");
        navigation.navigate('PasswordDashboard'); // Or VerifyMasterPassword
        return;
    }
    setLoading(true);
    try {
      const params = {};
      if (filterTypeFromRoute && filterTypeFromRoute !== 'all') {
        params.type = filterTypeFromRoute;
      }
      // Add other filters (category, favorites, etc.) if needed
      const data = await getPasswordEntries(params);
      setEntries(data || []); // API returns array directly
      setFilteredEntries(data || []);
    } catch (error) {
      Alert.alert('Error', 'Could not load password entries.');
      console.error("Fetch entries error:", error);
    } finally {
      setLoading(false);
    }
  }, [isMasterPasswordVerified, filterTypeFromRoute, navigation]);

  useFocusEffect(fetchEntries); // Reload when screen is focused

  useEffect(() => {
    // Filter entries based on search query
    if (searchQuery.trim() === '') {
      setFilteredEntries(entries);
    } else {
      const lowercasedQuery = searchQuery.toLowerCase();
      // src/screens/password/PasswordListScreen.js (continued)
      const filtered = entries.filter(entry =>
        (entry.title?.toLowerCase().includes(lowercasedQuery)) ||
        (entry.username?.toLowerCase().includes(lowercasedQuery)) ||
        (entry.email?.toLowerCase().includes(lowercasedQuery)) ||
        (entry.website_url?.toLowerCase().includes(lowercasedQuery))
      );
      setFilteredEntries(filtered);
    }
  }, [searchQuery, entries]);


  const renderItem = ({ item }) => {
    const entryIcon = item.entry_type === 'password' ? 'lock-outline' :
                      item.entry_type === 'passkey' ? 'fingerprint' :
                      item.entry_type === 'wifi' ? 'wifi' :
                      item.entry_type === 'card' ? 'credit-card-outline' :
                      item.entry_type === 'note' ? 'note-text-outline' :
                      item.entry_type === 'identity' ? 'account-box-outline' : 'key-variant';

    return (
        <TouchableOpacity
            style={[styles.itemContainer, { backgroundColor: theme.cardBackground }]}
            onPress={() => navigation.navigate('PasswordDetail', { passwordId: item.id })}
        >
            <Icon name={entryIcon} size={24} color={theme.primary} style={styles.itemIcon} />
            <View style={styles.itemTextContainer}>
                <Text style={[styles.itemTitle, { color: theme.textPrimary }]} numberOfLines={1}>{item.title}</Text>
                <Text style={[styles.itemSubtitle, { color: theme.textSecondary }]} numberOfLines={1}>
                    {item.username || item.email || item.website_url || 'No secondary info'}
                </Text>
            </View>
            {item.is_favorite && <Icon name="star" size={20} color={theme.yellow || '#FFD700'} />}
            <Icon name="chevron-right" size={24} color={theme.textTertiary} />
        </TouchableOpacity>
    );
  }


  if (loading) {
    return (
      <View style={[styles.fullScreenLoader, { backgroundColor: theme.background }]}>
        <ActivityIndicator size="large" color={theme.primary} />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
       <View style={[styles.searchBarContainer, { backgroundColor: theme.cardBackground, borderColor: theme.border }]}>
            <Icon name="magnify" size={22} color={theme.textTertiary} style={styles.searchIcon} />
            <TextInput
                style={[styles.searchInput, { color: theme.textPrimary }]}
                placeholder={`Search in ${filterLabelFromRoute}...`}
                placeholderTextColor={theme.textTertiary}
                value={searchQuery}
                onChangeText={setSearchQuery}
                returnKeyType="search"
            />
            {searchQuery.length > 0 && (
                <TouchableOpacity onPress={() => setSearchQuery('')}>
                    <Icon name="close-circle" size={20} color={theme.textTertiary} />
                </TouchableOpacity>
            )}
        </View>

      {filteredEntries.length === 0 ? (
        <View style={styles.emptyContainer}>
          <Icon name="alert-circle-outline" size={60} color={theme.textTertiary} />
          <Text style={[styles.emptyText, { color: theme.textSecondary }]}>No entries found.</Text>
          <Text style={[styles.emptySubText, { color: theme.textTertiary }]}>
            Try adjusting your search or add a new item.
          </Text>
        </View>
      ) : (
        <FlatList
          data={filteredEntries}
          renderItem={renderItem}
          keyExtractor={(item) => item.id.toString()}
          contentContainerStyle={styles.listContent}
        />
      )}
       <TouchableOpacity
        style={[styles.fab, { backgroundColor: theme.primary }]}
        onPress={() => navigation.navigate('AddPassword', { initialType: filterTypeFromRoute !== 'all' ? filterTypeFromRoute : 'password' })}
      >
        <Icon name="plus" size={30} color="#fff" />
      </TouchableOpacity>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  fullScreenLoader: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  searchBarContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    paddingHorizontal: 15,
    margin: 15,
    borderRadius: 12,
    borderWidth: 1,
    height: 50,
  },
  searchIcon: {
    marginRight: 10,
  },
  searchInput: {
    flex: 1,
    fontSize: 16,
  },
  listContent: {
    paddingHorizontal: 15,
    paddingBottom: 80, // For FAB
  },
  itemContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 15,
    borderRadius: 10,
    marginBottom: 10,
    // Shadow/elevation can be added via NeumorphicView or platform-specific styles
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 1 },
    shadowOpacity: 0.05,
    shadowRadius: 2,
    elevation: 2,
  },
  itemIcon: {
    marginRight: 15,
  },
  itemTextContainer: {
    flex: 1,
    marginRight: 10,
  },
  itemTitle: {
    fontSize: 16,
    fontWeight: '600',
  },
  itemSubtitle: {
    fontSize: 13,
    marginTop: 2,
  },
  emptyContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '500',
    marginTop: 10,
    textAlign: 'center',
  },
  emptySubText: {
    fontSize: 14,
    marginTop: 5,
    textAlign: 'center',
  },
  fab: {
    position: 'absolute',
    right: 25,
    bottom: 25,
    width: 60,
    height: 60,
    borderRadius: 30,
    justifyContent: 'center',
    alignItems: 'center',
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.3,
    shadowRadius: 3,
  },
});

export default PasswordListScreen;