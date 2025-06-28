
// components/OCRSettings.js
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Switch,
  Alert,
  ActivityIndicator,
} from 'react-native';
import OCRService from '../services/ocrService';

const OCRSettings = () => {
  const [preferences, setPreferences] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  useEffect(() => {
    loadPreferences();
  }, []);

  const loadPreferences = async () => {
    try {
      setLoading(true);
      const response = await OCRService.getOCRPreferences();
      if (response.success) {
        setPreferences(response);
      }
    } catch (error) {
      console.error('Failed to load OCR preferences:', error);
      Alert.alert('Error', 'Failed to load OCR preferences');
    } finally {
      setLoading(false);
    }
  };

  const updatePreference = async (newPreference) => {
    try {
      setSaving(true);
      const response = await OCRService.updateOCRPreferences(newPreference);
      
      if (response.success) {
        setPreferences(response);
        Alert.alert('Success', 'OCR preferences updated successfully');
      } else {
        Alert.alert('Error', response.error || 'Failed to update preferences');
      }
    } catch (error) {
      console.error('Failed to update OCR preferences:', error);
      Alert.alert('Error', 'Failed to update preferences');
    } finally {
      setSaving(false);
    }
  };

  const getPreferenceDescription = (preference) => {
    switch (preference) {
      case 'all':
        return 'OCR will be automatically processed for all uploaded documents and images';
      case 'selected':
        return 'OCR will only be processed when you manually trigger it';
      case 'none':
        return 'OCR processing is completely disabled';
      default:
        return '';
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading OCR settings...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.title}>OCR Settings</Text>
        <Text style={styles.subtitle}>
          Configure how text extraction works for your documents
        </Text>
      </View>

      {/* Current Setting */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>Current Setting</Text>
        <View style={styles.currentSettingCard}>
          <Text style={styles.currentSetting}>
            {preferences?.display || 'Unknown'}
          </Text>
          <Text style={styles.currentDescription}>
            {getPreferenceDescription(preferences?.preference)}
          </Text>
        </View>
      </View>

      {/* OCR Options */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>OCR Processing Options</Text>
        
        <TouchableOpacity
          style={[
            styles.optionCard,
            preferences?.preference === 'all' && styles.optionCardSelected
          ]}
          onPress={() => updatePreference('all')}
          disabled={saving}
        >
          <View style={styles.optionHeader}>
            <Text style={[
              styles.optionTitle,
              preferences?.preference === 'all' && styles.optionTitleSelected
            ]}>
              Automatic Processing
            </Text>
            <View style={[
              styles.radioButton,
              preferences?.preference === 'all' && styles.radioButtonSelected
            ]}>
              {preferences?.preference === 'all' && <View style={styles.radioButtonInner} />}
            </View>
          </View>
          <Text style={styles.optionDescription}>
            Process OCR automatically for all uploaded documents and images. 
            Includes automatic categorization based on content.
          </Text>
          <View style={styles.optionFeatures}>
            <Text style={styles.featureItem}>✓ Immediate text extraction</Text>
            <Text style={styles.featureItem}>✓ Smart categorization</Text>
            <Text style={styles.featureItem}>✓ Searchable content</Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.optionCard,
            preferences?.preference === 'selected' && styles.optionCardSelected
          ]}
          onPress={() => updatePreference('selected')}
          disabled={saving}
        >
          <View style={styles.optionHeader}>
            <Text style={[
              styles.optionTitle,
              preferences?.preference === 'selected' && styles.optionTitleSelected
            ]}>
              Manual Processing
            </Text>
            <View style={[
              styles.radioButton,
              preferences?.preference === 'selected' && styles.radioButtonSelected
            ]}>
              {preferences?.preference === 'selected' && <View style={styles.radioButtonInner} />}
            </View>
          </View>
          <Text style={styles.optionDescription}>
            Process OCR only when you manually trigger it. 
            Gives you control over which files get processed.
          </Text>
          <View style={styles.optionFeatures}>
            <Text style={styles.featureItem}>✓ User-controlled processing</Text>
            <Text style={styles.featureItem}>✓ Reduced processing costs</Text>
            <Text style={styles.featureItem}>✓ Manual categorization</Text>
          </View>
        </TouchableOpacity>

        <TouchableOpacity
          style={[
            styles.optionCard,
            preferences?.preference === 'none' && styles.optionCardSelected
          ]}
          onPress={() => updatePreference('none')}
          disabled={saving}
        >
          <View style={styles.optionHeader}>
            <Text style={[
              styles.optionTitle,
              preferences?.preference === 'none' && styles.optionTitleSelected
            ]}>
              Disabled
            </Text>
            <View style={[
              styles.radioButton,
              preferences?.preference === 'none' && styles.radioButtonSelected
            ]}>
              {preferences?.preference === 'none' && <View style={styles.radioButtonInner} />}
            </View>
          </View>
          <Text style={styles.optionDescription}>
            Completely disable OCR processing. Files will be stored without text extraction.
          </Text>
          <View style={styles.optionFeatures}>
            <Text style={styles.featureItem}>✓ No processing overhead</Text>
            <Text style={styles.featureItem}>✓ Simple file storage</Text>
            <Text style={styles.featureItem}>✓ Manual categorization only</Text>
          </View>
        </TouchableOpacity>
      </View>

      {/* OCR Info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>About OCR</Text>
        <View style={styles.infoCard}>
          <Text style={styles.infoText}>
            <Text style={styles.infoBold}>Optical Character Recognition (OCR)</Text> extracts 
            text from your documents and images, making them searchable and enabling 
            automatic categorization.
          </Text>
          
          <View style={styles.supportedFormats}>
            <Text style={styles.infoBold}>Supported Formats:</Text>
            <Text style={styles.formatItem}>📄 PDF documents</Text>
            <Text style={styles.formatItem}>📝 Word documents (.docx)</Text>
            <Text style={styles.formatItem}>📃 Text files (.txt)</Text>
            <Text style={styles.formatItem}>🖼️ Images (JPG, PNG)</Text>
          </View>

          <View style={styles.categories}>
            <Text style={styles.infoBold}>Auto-Categories:</Text>
            <Text style={styles.categoryItem}>💼 Professional</Text>
            <Text style={styles.categoryItem}>🏦 Banking</Text>
            <Text style={styles.categoryItem}>🏥 Medical</Text>
            <Text style={styles.categoryItem}>🎓 Education</Text>
            <Text style={styles.categoryItem}>👤 Personal</Text>
            <Text style={styles.categoryItem}>⚖️ Legal</Text>
          </View>
        </View>
      </View>

      {saving && (
        <View style={styles.savingOverlay}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.savingText}>Updating preferences...</Text>
        </View>
      )}
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f8f9fa',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
  header: {
    backgroundColor: 'white',
    padding: 20,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    color: '#333',
    marginBottom: 5,
  },
  subtitle: {
    fontSize: 16,
    color: '#666',
  },
  section: {
    margin: 15,
  },
  sectionTitle: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 10,
    color: '#333',
  },
  currentSettingCard: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  currentSetting: {
    fontSize: 18,
    fontWeight: '600',
    color: '#007AFF',
    marginBottom: 5,
  },
  currentDescription: {
    fontSize: 14,
    color: '#666',
  },
  optionCard: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 12,
    marginBottom: 10,
    borderWidth: 2,
    borderColor: '#e9ecef',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  optionCardSelected: {
    borderColor: '#007AFF',
    backgroundColor: '#f8fbff',
  },
  optionHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  optionTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  optionTitleSelected: {
    color: '#007AFF',
  },
  radioButton: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: '#dee2e6',
    justifyContent: 'center',
    alignItems: 'center',
  },
  radioButtonSelected: {
    borderColor: '#007AFF',
  },
  radioButtonInner: {
    width: 10,
    height: 10,
    borderRadius: 5,
    backgroundColor: '#007AFF',
  },
  optionDescription: {
    fontSize: 14,
    color: '#666',
    marginBottom: 10,
    lineHeight: 20,
  },
  optionFeatures: {
    paddingLeft: 10,
  },
  featureItem: {
    fontSize: 14,
    color: '#28a745',
    marginBottom: 2,
  },
  infoCard: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  infoText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
    marginBottom: 15,
  },
  infoBold: {
    fontWeight: '600',
    color: '#333',
  },
  supportedFormats: {
    marginBottom: 15,
  },
  formatItem: {
    fontSize: 14,
    color: '#666',
    marginLeft: 10,
    marginTop: 2,
  },
  categories: {
    marginBottom: 10,
  },
  categoryItem: {
    fontSize: 14,
    color: '#666',
    marginLeft: 10,
    marginTop: 2,
  },
  savingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  savingText: {
    marginTop: 10,
    fontSize: 16,
    color: '#666',
  },
});

export default OCRSettings;