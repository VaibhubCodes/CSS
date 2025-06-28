import React, { useCallback, useEffect, useState, useContext } from 'react';
import {
  View,
  Text,
  TextInput,
  StyleSheet,
  TouchableOpacity,
  SafeAreaView,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import AsyncStorage from '@react-native-async-storage/async-storage';
import DraggableFlatList from 'react-native-draggable-flatlist';
import ReactNativeHapticFeedback from 'react-native-haptic-feedback';
import { ThemeContext } from '../context/ThemeContext';
import NeumorphicView from '../components/NeumorphicView';

import Personal from '../../src/orangeicons/Personal.svg';
import Banking from '../../src/orangeicons/Banking.svg';
import Professional from '../../src/orangeicons/Professional.svg';
import Education from '../../src/orangeicons/Education.svg';
import MedicalFiles from '../../src/orangeicons/Medical-files.svg';
import VisitingCards from '../../src/orangeicons/Visiting-cards.svg';
import Investments from '../../src/orangeicons/Investments.svg';
import Miscellaneous from '../../src/orangeicons/Miscellaneous.svg';
import Folder from '../../src/orangeicons/Folder.svg';

const iconMap = {
  personal: Personal,
  banking: Banking,
  professional: Professional,
  education: Education,
  medical: MedicalFiles,
  visiting: VisitingCards,
  investment: Investments,
  miscellaneous: Miscellaneous,
  folder: Folder,
};

const DEFAULT_CATEGORIES = [
  { id: '1', iconKey: 'personal', title: 'Personal', categoryId: 1 },
  { id: '2', iconKey: 'banking', title: 'Banking', categoryId: 2 },
  { id: '3', iconKey: 'professional', title: 'Professional', categoryId: 3 },
  { id: '4', iconKey: 'education', title: 'Education', categoryId: 4 },
  { id: '5', iconKey: 'medical', title: 'Medical', categoryId: 5 },
  { id: '6', iconKey: 'visiting', title: 'Visiting Card', categoryId: 6 },
  { id: '7', iconKey: 'investment', title: 'Investment', categoryId: 7 },
  { id: '8', iconKey: 'miscellaneous', title: 'Miscellaneous', categoryId: 8 },
  { id: '9', iconKey: 'folder', title: 'New Folder', categoryId: 9 },
];

const STORAGE_KEY = 'user_category_order';

const Section2Screen = ({ navigation }) => {
  const { theme } = useContext(ThemeContext);
  const [categories, setCategories] = useState(DEFAULT_CATEGORIES);

  useEffect(() => {
    const loadStoredOrder = async () => {
      try {
        const stored = await AsyncStorage.getItem(STORAGE_KEY);
        if (stored) {
          const storedIds = JSON.parse(stored);
          const ordered = storedIds.map(id => DEFAULT_CATEGORIES.find(c => c.id === id)).filter(Boolean);
          setCategories(ordered);
        }
      } catch (err) {
        console.error('Failed to load category order:', err);
      }
    };
    loadStoredOrder();
  }, []);

  const handleDragEnd = useCallback(async ({ data }) => {
    setCategories(data);
    try {
      await AsyncStorage.setItem(STORAGE_KEY, JSON.stringify(data.map(c => c.id)));
    } catch (err) {
      console.error('Failed to save category order:', err);
    }
  }, []);

  return (
    <SafeAreaView style={[styles.container, { backgroundColor: theme.background }]}>
      {/* Header */}
      <View style={[styles.header, { backgroundColor: theme.cardBackground }]}>
        <TouchableOpacity onPress={() => navigation.goBack()} style={styles.backButton}>
          <Icon name="arrow-left" size={24} color={theme.textPrimary} />
        </TouchableOpacity>
        <Text style={[styles.headerTitle, { color: theme.textPrimary }]}>My Stuff</Text>
        <Text style={styles.points}>
          Total Points: <Text style={styles.basicText}>Basic</Text>
        </Text>
      </View>

      {/* New Category Button */}
      <View style={styles.addCategory}>
        <TouchableOpacity style={[styles.newCategoryButton, { backgroundColor: theme.background, borderColor: theme.buttonBackground }]}>
          <Icon name="folder-plus-outline" size={20} color={theme.buttonBackground} />
          <Text style={[styles.newCategoryText, { color: theme.buttonBackground }]}>New Category</Text>
        </TouchableOpacity>
      </View>

      {/* Search Bar */}
      <View style={[styles.searchBar, { backgroundColor: theme.cardBackground }]}>
        <Icon name="magnify" size={20} color={theme.textTertiary} />
        <TextInput
          placeholder="Search for categories..."
          placeholderTextColor={theme.textTertiary}
          style={[styles.searchInput, { color: theme.textPrimary }]}
        />
      </View>

      {/* Draggable List */}
      <DraggableFlatList
        data={categories}
        onDragEnd={handleDragEnd}
        keyExtractor={item => item.id}
        contentContainerStyle={{ paddingBottom: 270 }}
        renderItem={({ item, drag, isActive }) => {
          const IconComponent = iconMap[item.iconKey];
          return (
            <TouchableOpacity
              onLongPress={() => {
                ReactNativeHapticFeedback.trigger('impactMedium', {
                  enableVibrateFallback: true,
                  ignoreAndroidSystemSettings: false,
                });
                drag();
              }}
              delayLongPress={200}
              onPress={() => navigation.navigate('DocumentsScreen', {
                categoryName: item.title,
                categoryId: item.categoryId,
              })}
            >
              <NeumorphicView theme={theme} style={isActive && { opacity: 0.9 }}>
                <IconComponent width={28} height={28} />
                <Text style={[styles.cardText, { color: theme.textPrimary }]}>{item.title}</Text>
              </NeumorphicView>
            </TouchableOpacity>
          );
        }}
      />

      {/* Bottom Navigation */}
      <View style={[styles.bottomNavigation, { backgroundColor: theme.cardBackground, borderTopColor: theme.border }]}>
        {[
          { icon: 'home-outline', route: 'HomeScreen' },
          { icon: 'upload-outline', route: 'UploadingScreen' },
          { icon: 'tag-outline', route: 'OffersScreen' },
          { icon: 'heart-outline', route: 'FavoriteScreen' },
          { icon: 'account-outline', route: 'Settings' },
        ].map(({ icon, route }) => (
          <TouchableOpacity key={icon} onPress={() => navigation.navigate(route)}>
            <Icon name={icon} size={24} color={theme.textTertiary} />
            <Text style={[styles.navText, { color: theme.textTertiary }]}>
              {route.replace('Screen', '')}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1 },
  header: {
    flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center',
    paddingHorizontal: 15, paddingVertical: 15, elevation: 2,
  },
  backButton: { paddingLeft: 20, paddingRight: 10 },
  headerTitle: { fontSize: 18, fontFamily: 'Poppins-Bold', flex: 1 },
  points: { fontSize: 14, fontFamily: 'Poppins-Regular', color: '#888' },
  basicText: { color: '#426BB6', fontFamily: 'Poppins-Bold' },
  addCategory: { marginHorizontal: 15, marginVertical: 10 },
  newCategoryButton: {
    flexDirection: 'row', alignItems: 'center', borderRadius: 10,
    paddingHorizontal: 12, paddingVertical: 6, alignSelf: 'flex-start', borderWidth: 1,
  },
  newCategoryText: { fontSize: 14, fontFamily: 'Poppins-Regular', marginLeft: 10 },
  searchBar: {
    flexDirection: 'row', alignItems: 'center',
    borderRadius: 8, marginHorizontal: 15, marginVertical: 10,
    paddingHorizontal: 10, height: 50, elevation: 1,
  },
  searchInput: { flex: 1, marginLeft: 10, fontSize: 14, fontFamily: 'Poppins-Regular' },
  cardText: {
    fontSize: 18,
    fontFamily: 'Poppins-Regular',
    marginLeft: 15,
  },
  bottomNavigation: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    paddingVertical: 10,
    paddingHorizontal: 20,
    position: 'absolute',
    bottom: 0,
    width: '100%',
    borderTopWidth: 1,
  },
  navText: {
    fontSize: 12,
    fontFamily: 'Poppins-Regular',
    marginTop: 5,
  },
});

export default Section2Screen;