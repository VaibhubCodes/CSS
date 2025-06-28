// src/screens/password/AddPasswordScreen.js
import React, { useState, useContext } from 'react';
import {
  View, Text, TextInput, TouchableOpacity, StyleSheet, Alert,
  ScrollView, Switch, ActivityIndicator
} from 'react-native';
import { useNavigation, useRoute } from '@react-navigation/native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { Picker } from '@react-native-picker/picker'; // Use a picker library
import { createPasswordEntry, fetchPasswordCategories, generatePasswordStandalone } from '../../services/passwordService';
import { ThemeContext } from '../../context/ThemeContext';
import { useMasterPassword } from '../../context/MasterPasswordContext'; // To ensure master pass is verified

const AddPasswordScreen = () => {
  const navigation = useNavigation();
  const route = useRoute();
  const { theme } = useContext(ThemeContext);
  const { isMasterPasswordVerified } = useMasterPassword();

  const initialType = route.params?.initialType || 'password';

  const [title, setTitle] = useState('');
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [websiteUrl, setWebsiteUrl] = useState('');
  const [notes, setNotes] = useState('');
  const [entryType, setEntryType] = useState(initialType);
  const [categoryId, setCategoryId] = useState(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState([]);
  const [error, setError] = useState('');


  const passwordTypeOptions = [
    { label: 'Website Password', value: 'password' },
    { label: 'App Password', value: 'app' },
    { label: 'Wi-Fi Password', value: 'wifi' },
    { label: 'Credit/Debit Card', value: 'card' },
    { label: 'Secure Note', value: 'note' },
    { label: 'Passkey', value: 'passkey' },
    { label: 'Identity', value: 'identity' },
  ];

  useEffect(() => {
    if (!isMasterPasswordVerified) {
      Alert.alert("Access Denied", "Master password not verified. Please verify to add passwords.");
      navigation.goBack(); // Or navigate to VerifyMasterPasswordScreen
      return;
    }

    const loadCategories = async () => {
      try {
        const fetchedCategories = await fetchPasswordCategories();
        setCategories(fetchedCategories || []);
      } catch (err) {
        console.error("Failed to load categories", err);
        Alert.alert("Error", "Could not load categories.");
      }
    };
    loadCategories();
  }, [isMasterPasswordVerified, navigation]);

  const handleGeneratePassword = async () => {
    setLoading(true);
    try {
      // Assuming generatePasswordStandalone doesn't require auth and is available
      const response = await generatePasswordStandalone({
        length: 16, uppercase: true, numbers: true, symbols: true
      });
      if (response.success && response.password) {
        setPassword(response.password);
        setShowPassword(true); // Show generated password
        setError('');
      } else {
        setError(response.error || 'Failed to generate password.');
      }
    } catch (err) {
      console.error("Generate password error:", err);
      setError('Could not generate password.');
    } finally {
      setLoading(false);
    }
  };

  const handleSavePassword = async () => {
    if (!title.trim() || (!password.trim() && entryType !== 'note' && entryType !== 'identity')) {
      setError('Title and Password (for most types) are required.');
      return;
    }
    setError('');
    setLoading(true);
    try {
      const entryData = {
        title, username, email, password,
        website_url: websiteUrl, notes, entry_type: entryType,
        category: categoryId, // Send ID
        is_favorite: isFavorite,
      };
      const response = await createPasswordEntry(entryData);
      if (response.id) { // Check for ID in response for success
        Alert.alert('Success', 'Password entry saved successfully!');
        navigation.goBack();
      } else {
        // Backend might return structured errors in response.error
        const errorMsg = typeof response.error === 'string' ? response.error : JSON.stringify(response.error);
        setError(errorMsg || 'Failed to save password entry.');
      }
    } catch (err) {
      console.error("Save password error:", err);
      const backendError = err.response?.data?.error || err.response?.data?.detail;
      setError(backendError || 'An unexpected error occurred while saving.');
    } finally {
      setLoading(false);
    }
  };


  return (
    <ScrollView style={[styles.container, { backgroundColor: theme.background }]} contentContainerStyle={styles.scrollContent}>
      <Text style={[styles.header, { color: theme.textPrimary }]}>Add New Item</Text>

      {error ? <Text style={styles.errorText}>{error}</Text> : null}

      <View style={styles.formGroup}>
        <Text style={[styles.label, { color: theme.textSecondary }]}>Title*</Text>
        <TextInput
          style={[styles.input, { backgroundColor: theme.cardBackground, color: theme.textPrimary, borderColor: theme.border }]}
          value={title} onChangeText={setTitle} placeholder="e.g., Google Account" placeholderTextColor={theme.textTertiary}
        />
      </View>

      <View style={styles.formGroup}>
        <Text style={[styles.label, { color: theme.textSecondary }]}>Type*</Text>
        <View style={[styles.pickerContainer, {borderColor: theme.border, backgroundColor: theme.cardBackground}]}>
            <Picker
            selectedValue={entryType}
            onValueChange={(itemValue) => setEntryType(itemValue)}
            style={[styles.picker, {color: theme.textPrimary}]}
            dropdownIconColor={theme.textPrimary}
            >
            {passwordTypeOptions.map(opt => <Picker.Item key={opt.value} label={opt.label} value={opt.value} />)}
            </Picker>
        </View>
      </View>

       {entryType !== 'note' && entryType !== 'identity' && ( // Hide for notes/identity
        <>
            <View style={styles.formGroup}>
                <Text style={[styles.label, { color: theme.textSecondary }]}>Username</Text>
                <TextInput style={[styles.input, { backgroundColor: theme.cardBackground, color: theme.textPrimary, borderColor: theme.border }]}
                value={username} onChangeText={setUsername} placeholder="Your username" placeholderTextColor={theme.textTertiary}/>
            </View>

            <View style={styles.formGroup}>
                <Text style={[styles.label, { color: theme.textSecondary }]}>Email</Text>
                <TextInput style={[styles.input, { backgroundColor: theme.cardBackground, color: theme.textPrimary, borderColor: theme.border }]}
                value={email} onChangeText={setEmail} placeholder="your.email@example.com" keyboardType="email-address" placeholderTextColor={theme.textTertiary}/>
            </View>

            <View style={styles.formGroup}>
                <Text style={[styles.label, { color: theme.textSecondary }]}>Password*</Text>
                <View style={[styles.passwordInputContainer, {borderColor: theme.border, backgroundColor: theme.cardBackground}]}>
                <TextInput
                    style={[styles.passwordInput, {color: theme.textPrimary}]}
                    value={password} onChangeText={setPassword} placeholder="Enter strong password"
                    secureTextEntry={!showPassword} placeholderTextColor={theme.textTertiary}
                />
                <TouchableOpacity onPress={() => setShowPassword(!showPassword)} style={styles.eyeIcon}>
                    <Icon name={showPassword ? "eye-off-outline" : "eye-outline"} size={24} color={theme.textTertiary} />
                </TouchableOpacity>
                </View>
                <TouchableOpacity onPress={handleGeneratePassword} style={[styles.generateButton, {backgroundColor: theme.secondary}]}>
                    <Text style={[styles.generateButtonText, {color: theme.textOnSecondary || '#fff'}]}>Generate Secure Password</Text>
                </TouchableOpacity>
            </View>

            <View style={styles.formGroup}>
                <Text style={[styles.label, { color: theme.textSecondary }]}>Website URL</Text>
                <TextInput style={[styles.input, { backgroundColor: theme.cardBackground, color: theme.textPrimary, borderColor: theme.border }]}
                value={websiteUrl} onChangeText={setWebsiteUrl} placeholder="https://example.com" keyboardType="url" placeholderTextColor={theme.textTertiary}/>
            </View>
         </>
       )}


      <View style={styles.formGroup}>
        <Text style={[styles.label, { color: theme.textSecondary }]}>Category</Text>
         <View style={[styles.pickerContainer, {borderColor: theme.border, backgroundColor: theme.cardBackground}]}>
            <Picker
                selectedValue={categoryId}
                onValueChange={(itemValue) => setCategoryId(itemValue)}
                style={[styles.picker, {color: theme.textPrimary}]}
                dropdownIconColor={theme.textPrimary}
            >
                <Picker.Item label="-- No Category --" value={null} />
                {categories.map(cat => <Picker.Item key={cat.id} label={cat.name} value={cat.id} />)}
            </Picker>
        </View>
      </View>

      <View style={styles.formGroup}>
        <Text style={[styles.label, { color: theme.textSecondary }]}>Notes</Text>
        <TextInput
          style={[styles.input, styles.notesInput, { backgroundColor: theme.cardBackground, color: theme.textPrimary, borderColor: theme.border }]}
          value={notes} onChangeText={setNotes} placeholder="Any additional information..."
          multiline numberOfLines={3} placeholderTextColor={theme.textTertiary}
        />
      </View>

      <View style={styles.switchRow}>
        <Text style={[styles.label, { color: theme.textSecondary }]}>Mark as Favorite</Text>
        <Switch
          trackColor={{ false: theme.grey, true: theme.primaryFaded }}
          thumbColor={isFavorite ? theme.primary : theme.thumbOff}
          ios_backgroundColor={theme.grey}
          onValueChange={setIsFavorite}
          value={isFavorite}
        />
      </View>

      <TouchableOpacity
        style={[styles.saveButton, { backgroundColor: theme.primary }]}
        onPress={handleSavePassword}
        disabled={loading}
      >
        {loading ? <ActivityIndicator color="#fff" /> : <Text style={styles.saveButtonText}>Save Item</Text>}
      </TouchableOpacity>
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
  header: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
  },
  formGroup: {
    marginBottom: 15,
  },
  label: {
    fontSize: 14,
    marginBottom: 5,
  },
  input: {
    height: 50,
    borderWidth: 1,
    borderRadius: 8,
    paddingHorizontal: 15,
    fontSize: 16,
  },
  notesInput: {
    height: 100,
    textAlignVertical: 'top',
    paddingTop: 15,
  },
  pickerContainer: {
    borderWidth: 1,
    borderRadius: 8,
    height: 50,
    justifyContent: 'center',
  },
  picker: {
    height: 50,
    width: '100%',
  },
  passwordInputContainer: {
    flexDirection: 'row',
    alignItems: 'center',
    borderWidth: 1,
    borderRadius: 8,
    height: 50,
  },
  passwordInput: {
    flex: 1,
    paddingHorizontal: 15,
    fontSize: 16,
    height: '100%',
  },
  eyeIcon: {
    padding: 10,
  },
  generateButton: {
    paddingVertical: 10,
    borderRadius: 5,
    alignItems: 'center',
    marginTop: 10,
  },
  generateButtonText: {
    fontSize: 14,
    fontWeight: '500',
  },
  switchRow: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 20,
  },
  saveButton: {
    height: 50,
    borderRadius: 8,
    justifyContent: 'center',
    alignItems: 'center',
  },
  saveButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: 'bold',
  },
  errorText: {
    color: 'red',
    textAlign: 'center',
    marginBottom: 10,
  },
});

export default AddPasswordScreen;