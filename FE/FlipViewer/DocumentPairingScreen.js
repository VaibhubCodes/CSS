// DocumentPairingScreen.js - Screen to create document pairs
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  TouchableOpacity,
  Image,
  Alert,
  ActivityIndicator,
  TextInput,
  Modal,
  FlatList,
  StyleSheet,
  SafeAreaView,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as ImagePicker from 'expo-image-picker';
import { useNavigation } from '@react-navigation/native';
import { apiService } from '../services/apiService';

const DOCUMENT_TYPES = [
  'Aadhar Card',
  'PAN Card',
  'Driving License',
  'Passport',
  'Voter ID',
  'Bank Passbook',
  'Insurance Card',
  'Other',
];

const DocumentPairingScreen = () => {
  const navigation = useNavigation();
  
  // State management
  const [selectedFiles, setSelectedFiles] = useState([]);
  const [documentType, setDocumentType] = useState('');
  const [customDocumentType, setCustomDocumentType] = useState('');
  const [showDocumentTypeModal, setShowDocumentTypeModal] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  const [isPairing, setIsPairing] = useState(false);
  
  // Selected documents for pairing
  const [frontDocument, setFrontDocument] = useState(null);
  const [backDocument, setBackDocument] = useState(null);

  useEffect(() => {
    loadUserFiles();
  }, []);

  const loadUserFiles = async () => {
    try {
      setIsLoading(true);
      const response = await apiService.getUserFiles();
      
      // Filter to show only single documents (not already paired) and images/documents
      const eligibleFiles = response.files.filter(file => 
        file.document_side === 'single' && 
        (file.file_type === 'document' || file.file_type === 'image')
      );
      
      setSelectedFiles(eligibleFiles);
    } catch (error) {
      Alert.alert('Error', 'Failed to load files: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const selectImage = async (side) => {
    try {
      const permissionResult = await ImagePicker.requestMediaLibraryPermissionsAsync();
      
      if (!permissionResult.granted) {
        Alert.alert('Permission Required', 'Please allow access to your photo library.');
        return;
      }

      const result = await ImagePicker.launchImageLibraryAsync({
        mediaTypes: ImagePicker.MediaTypeOptions.Images,
        allowsEditing: true,
        aspect: [16, 10],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        await uploadImage(result.assets[0], side);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to select image: ' + error.message);
    }
  };

  const takePhoto = async (side) => {
    try {
      const permissionResult = await ImagePicker.requestCameraPermissionsAsync();
      
      if (!permissionResult.granted) {
        Alert.alert('Permission Required', 'Please allow camera access.');
        return;
      }

      const result = await ImagePicker.launchCameraAsync({
        allowsEditing: true,
        aspect: [16, 10],
        quality: 0.8,
      });

      if (!result.canceled && result.assets[0]) {
        await uploadImage(result.assets[0], side);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to take photo: ' + error.message);
    }
  };

  const uploadImage = async (imageAsset, side) => {
    try {
      setIsLoading(true);
      
      const formData = new FormData();
      formData.append('file', {
        uri: imageAsset.uri,
        type: 'image/jpeg',
        name: `${side}_${Date.now()}.jpg`,
      });
      formData.append('file_type', 'image');

      const response = await apiService.uploadFile(formData);
      
      if (response.success) {
        const uploadedFile = response.file;
        
        if (side === 'front') {
          setFrontDocument(uploadedFile);
        } else {
          setBackDocument(uploadedFile);
        }
        
        // Refresh the file list
        loadUserFiles();
        
        Alert.alert('Success', `${side} side uploaded successfully`);
      }
    } catch (error) {
      Alert.alert('Error', `Failed to upload ${side} image: ` + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const selectFromExisting = (file, side) => {
    if (side === 'front') {
      setFrontDocument(file);
    } else {
      setBackDocument(file);
    }
  };

  const createDocumentPair = async () => {
    if (!frontDocument || !backDocument) {
      Alert.alert('Error', 'Please select both front and back documents');
      return;
    }

    if (!documentType && !customDocumentType) {
      Alert.alert('Error', 'Please select or enter a document type');
      return;
    }

    const finalDocumentType = documentType === 'Other' ? customDocumentType : documentType;

    try {
      setIsPairing(true);
      
      const response = await apiService.createDocumentPair({
        front_file_id: frontDocument.id,
        back_file_id: backDocument.id,
        document_type_name: finalDocumentType,
      });

      if (response.success) {
        Alert.alert(
          'Success',
          'Document pair created successfully!',
          [
            {
              text: 'View Document',
              onPress: () => {
                navigation.navigate('DocumentFlipViewer', {
                  documentPair: {
                    front: response.front_file,
                    back: response.back_file,
                  },
                  documentType: finalDocumentType,
                });
              },
            },
            {
              text: 'Create Another',
              onPress: () => {
                setFrontDocument(null);
                setBackDocument(null);
                setDocumentType('');
                setCustomDocumentType('');
                loadUserFiles();
              },
            },
          ]
        );
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to create document pair: ' + error.message);
    } finally {
      setIsPairing(false);
    }
  };

  const showImageOptions = (side) => {
    Alert.alert(
      `Select ${side} Side`,
      'Choose how to add the document',
      [
        { text: 'Take Photo', onPress: () => takePhoto(side) },
        { text: 'Choose from Gallery', onPress: () => selectImage(side) },
        { text: 'Select from Files', onPress: () => {} }, // Will show existing files
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const renderDocumentTypeModal = () => (
    <Modal
      visible={showDocumentTypeModal}
      animationType="slide"
      presentationStyle="pageSheet"
      onRequestClose={() => setShowDocumentTypeModal(false)}
    >
      <SafeAreaView style={styles.modalContainer}>
        <View style={styles.modalHeader}>
          <Text style={styles.modalTitle}>Select Document Type</Text>
          <TouchableOpacity onPress={() => setShowDocumentTypeModal(false)}>
            <Ionicons name="close" size={24} color="#333" />
          </TouchableOpacity>
        </View>
        
        <FlatList
          data={DOCUMENT_TYPES}
          keyExtractor={(item) => item}
          renderItem={({ item }) => (
            <TouchableOpacity
              style={[
                styles.documentTypeItem,
                documentType === item && styles.selectedDocumentType,
              ]}
              onPress={() => {
                setDocumentType(item);
                setShowDocumentTypeModal(false);
              }}
            >
              <Text
                style={[
                  styles.documentTypeText,
                  documentType === item && styles.selectedDocumentTypeText,
                ]}
              >
                {item}
              </Text>
              {documentType === item && (
                <Ionicons name="checkmark" size={20} color="#007AFF" />
              )}
            </TouchableOpacity>
          )}
        />
      </SafeAreaView>
    </Modal>
  );

  const renderFileGrid = (side) => (
    <View style={styles.fileGridContainer}>
      <Text style={styles.fileGridTitle}>Select from existing files:</Text>
      <FlatList
        data={selectedFiles}
        numColumns={2}
        keyExtractor={(item) => item.id.toString()}
        renderItem={({ item }) => (
          <TouchableOpacity
            style={[
              styles.fileGridItem,
              (side === 'front' ? frontDocument?.id : backDocument?.id) === item.id &&
                styles.selectedFileItem,
            ]}
            onPress={() => selectFromExisting(item, side)}
          >
            <Image source={{ uri: item.file_url }} style={styles.fileGridImage} />
            <Text style={styles.fileGridText} numberOfLines={1}>
              {item.original_filename}
            </Text>
            {(side === 'front' ? frontDocument?.id : backDocument?.id) === item.id && (
              <View style={styles.selectedIndicator}>
                <Ionicons name="checkmark-circle" size={24} color="#007AFF" />
              </View>
            )}
          </TouchableOpacity>
        )}
        contentContainerStyle={styles.fileGrid}
      />
    </View>
  );

  if (isLoading) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.loadingContainer}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.loadingText}>Loading files...</Text>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color="#333" />
        </TouchableOpacity>
        <Text style={styles.headerTitle}>Create Document Pair</Text>
        <View style={{ width: 24 }} />
      </View>

      <ScrollView style={styles.scrollView}>
        {/* Document Type Selection */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Document Type</Text>
          <TouchableOpacity
            style={styles.documentTypeSelector}
            onPress={() => setShowDocumentTypeModal(true)}
          >
            <Text style={styles.documentTypeSelectorText}>
              {documentType || 'Select document type'}
            </Text>
            <Ionicons name="chevron-down" size={20} color="#666" />
          </TouchableOpacity>
          
          {documentType === 'Other' && (
            <TextInput
              style={styles.customTypeInput}
              placeholder="Enter custom document type"
              value={customDocumentType}
              onChangeText={setCustomDocumentType}
            />
          )}
        </View>

        {/* Front Document */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Front Side</Text>
          
          {frontDocument ? (
            <View style={styles.selectedDocument}>
              <Image source={{ uri: frontDocument.file_url }} style={styles.selectedDocumentImage} />
              <View style={styles.selectedDocumentInfo}>
                <Text style={styles.selectedDocumentName}>{frontDocument.original_filename}</Text>
                <TouchableOpacity
                  style={styles.changeButton}
                  onPress={() => setFrontDocument(null)}
                >
                  <Text style={styles.changeButtonText}>Change</Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : (
            <View style={styles.documentSlot}>
              <TouchableOpacity
                style={styles.addDocumentButton}
                onPress={() => showImageOptions('front')}
              >
                <Ionicons name="camera" size={32} color="#007AFF" />
                <Text style={styles.addDocumentText}>Add Front Side</Text>
              </TouchableOpacity>
              
              {selectedFiles.length > 0 && renderFileGrid('front')}
            </View>
          )}
        </View>

        {/* Back Document */}
        <View style={styles.section}>
          <Text style={styles.sectionTitle}>Back Side</Text>
          
          {backDocument ? (
            <View style={styles.selectedDocument}>
              <Image source={{ uri: backDocument.file_url }} style={styles.selectedDocumentImage} />
              <View style={styles.selectedDocumentInfo}>
                <Text style={styles.selectedDocumentName}>{backDocument.original_filename}</Text>
                <TouchableOpacity
                  style={styles.changeButton}
                  onPress={() => setBackDocument(null)}
                >
                  <Text style={styles.changeButtonText}>Change</Text>
                </TouchableOpacity>
              </View>
            </View>
          ) : (
            <View style={styles.documentSlot}>
              <TouchableOpacity
                style={styles.addDocumentButton}
                onPress={() => showImageOptions('back')}
              >
                <Ionicons name="camera" size={32} color="#007AFF" />
                <Text style={styles.addDocumentText}>Add Back Side</Text>
              </TouchableOpacity>
              
              {selectedFiles.length > 0 && renderFileGrid('back')}
            </View>
          )}
        </View>

        {/* Create Pair Button */}
        <TouchableOpacity
          style={[
            styles.createPairButton,
            (!frontDocument || !backDocument || isPairing) && styles.disabledButton,
          ]}
          onPress={createDocumentPair}
          disabled={!frontDocument || !backDocument || isPairing}
        >
          {isPairing ? (
            <ActivityIndicator size="small" color="#fff" />
          ) : (
            <Text style={styles.createPairButtonText}>Create Document Pair</Text>
          )}
        </TouchableOpacity>
      </ScrollView>

      {renderDocumentTypeModal()}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#f5f5f5',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: '#fff',
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  headerTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  scrollView: {
    flex: 1,
  },
  section: {
    backgroundColor: '#fff',
    marginVertical: 8,
    marginHorizontal: 16,
    padding: 16,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 12,
  },
  documentTypeSelector: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 12,
    paddingVertical: 16,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    backgroundColor: '#f9f9f9',
  },
  documentTypeSelectorText: {
    fontSize: 16,
    color: '#333',
  },
  customTypeInput: {
    marginTop: 12,
    paddingHorizontal: 12,
    paddingVertical: 16,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    borderRadius: 8,
    fontSize: 16,
  },
  documentSlot: {
    minHeight: 200,
  },
  addDocumentButton: {
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 32,
    borderWidth: 2,
    borderColor: '#007AFF',
    borderStyle: 'dashed',
    borderRadius: 12,
    backgroundColor: '#f8f9ff',
  },
  addDocumentText: {
    marginTop: 8,
    fontSize: 16,
    color: '#007AFF',
    fontWeight: '500',
  },
  selectedDocument: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    backgroundColor: '#f0f8ff',
    borderRadius: 12,
    borderWidth: 1,
    borderColor: '#007AFF',
  },
  selectedDocumentImage: {
    width: 60,
    height: 60,
    borderRadius: 8,
    backgroundColor: '#f0f0f0',
  },
  selectedDocumentInfo: {
    flex: 1,
    marginLeft: 12,
  },
  selectedDocumentName: {
    fontSize: 14,
    fontWeight: '500',
    color: '#333',
    marginBottom: 4,
  },
  changeButton: {
    alignSelf: 'flex-start',
    paddingHorizontal: 12,
    paddingVertical: 6,
    backgroundColor: '#007AFF',
    borderRadius: 6,
  },
  changeButtonText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '500',
  },
  fileGridContainer: {
    marginTop: 16,
  },
  fileGridTitle: {
    fontSize: 14,
    fontWeight: '500',
    color: '#666',
    marginBottom: 8,
  },
  fileGrid: {
    paddingVertical: 8,
  },
  fileGridItem: {
    flex: 1,
    margin: 4,
    padding: 8,
    backgroundColor: '#f9f9f9',
    borderRadius: 8,
    borderWidth: 1,
    borderColor: '#e0e0e0',
    alignItems: 'center',
    position: 'relative',
  },
  selectedFileItem: {
    borderColor: '#007AFF',
    backgroundColor: '#f0f8ff',
  },
  fileGridImage: {
    width: 60,
    height: 60,
    borderRadius: 6,
    backgroundColor: '#f0f0f0',
  },
  fileGridText: {
    marginTop: 4,
    fontSize: 12,
    color: '#333',
    textAlign: 'center',
  },
  selectedIndicator: {
    position: 'absolute',
    top: 4,
    right: 4,
    backgroundColor: '#fff',
    borderRadius: 12,
  },
  createPairButton: {
    backgroundColor: '#007AFF',
    marginHorizontal: 16,
    marginVertical: 24,
    paddingVertical: 16,
    borderRadius: 12,
    alignItems: 'center',
    justifyContent: 'center',
  },
  disabledButton: {
    backgroundColor: '#ccc',
  },
  createPairButtonText: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
  },
  loadingContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
  },
  loadingText: {
    marginTop: 16,
    fontSize: 16,
    color: '#666',
  },
  modalContainer: {
    flex: 1,
    backgroundColor: '#fff',
  },
  modalHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#e0e0e0',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
  },
  documentTypeItem: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 16,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  selectedDocumentType: {
    backgroundColor: '#f0f8ff',
  },
  documentTypeText: {
    fontSize: 16,
    color: '#333',
  },
  selectedDocumentTypeText: {
    color: '#007AFF',
    fontWeight: '500',
  },
});

export default DocumentPairingScreen;