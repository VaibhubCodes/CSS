
// components/FileUpload.js
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Alert,
  ActivityIndicator,
  ScrollView,
} from 'react-native';
import DocumentPicker from 'react-native-document-picker';
import { launchImageLibrary, launchCamera } from 'react-native-image-picker';
import OCRService from '../services/ocrService';

const FileUpload = ({ onUploadComplete, navigation }) => {
  const [uploading, setUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState('');
  const [categories, setCategories] = useState([]);
  const [selectedCategory, setSelectedCategory] = useState(null);

  useEffect(() => {
    loadCategories();
  }, []);

  const loadCategories = async () => {
    try {
      const response = await OCRService.getFiles();
      if (response.categories) {
        setCategories(response.categories);
      }
    } catch (error) {
      console.error('Failed to load categories:', error);
    }
  };

  const selectDocument = async () => {
    try {
      const result = await DocumentPicker.pickSingle({
        type: [DocumentPicker.types.pdf, DocumentPicker.types.doc, DocumentPicker.types.docx],
        copyTo: 'cachesDirectory',
      });

      await handleFileUpload(result, 'document');
    } catch (error) {
      if (!DocumentPicker.isCancel(error)) {
        Alert.alert('Error', 'Failed to select document');
      }
    }
  };

  const selectImage = () => {
    Alert.alert(
      'Select Image',
      'Choose an option',
      [
        { text: 'Camera', onPress: openCamera },
        { text: 'Gallery', onPress: openGallery },
        { text: 'Cancel', style: 'cancel' },
      ]
    );
  };

  const openCamera = () => {
    const options = {
      mediaType: 'photo',
      quality: 0.8,
      includeBase64: false,
    };

    launchCamera(options, (response) => {
      if (response.assets && response.assets[0]) {
        const asset = response.assets[0];
        const fileData = {
          uri: asset.uri,
          type: asset.type,
          name: asset.fileName || 'camera_image.jpg',
        };
        handleFileUpload(fileData, 'image');
      }
    });
  };

  const openGallery = () => {
    const options = {
      mediaType: 'photo',
      quality: 0.8,
      includeBase64: false,
    };

    launchImageLibrary(options, (response) => {
      if (response.assets && response.assets[0]) {
        const asset = response.assets[0];
        const fileData = {
          uri: asset.uri,
          type: asset.type,
          name: asset.fileName || 'gallery_image.jpg',
        };
        handleFileUpload(fileData, 'image');
      }
    });
  };

  const handleFileUpload = async (fileData, fileType) => {
    setUploading(true);
    setUploadProgress('Uploading file...');

    try {
      // Upload file
      const uploadResponse = await OCRService.uploadFile(
        fileData,
        fileType,
        selectedCategory
      );

      if (uploadResponse.success) {
        setUploadProgress('File uploaded successfully!');
        
        // Check OCR result
        const ocrResult = uploadResponse.ocr_result;
        if (ocrResult) {
          if (ocrResult.status === 'completed') {
            setUploadProgress('OCR processing completed!');
            showOCRResults(uploadResponse.file, ocrResult);
          } else if (ocrResult.status === 'processing') {
            setUploadProgress('OCR processing in progress...');
            pollOCRStatus(uploadResponse.file.id);
          } else if (ocrResult.status === 'error') {
            setUploadProgress('OCR processing failed');
            Alert.alert('OCR Error', ocrResult.error || 'Unknown error');
          }
        }

        if (onUploadComplete) {
          onUploadComplete(uploadResponse.file);
        }
      } else {
        throw new Error(uploadResponse.error || 'Upload failed');
      }
    } catch (error) {
      console.error('Upload error:', error);
      Alert.alert('Upload Error', error.message);
      setUploadProgress('Upload failed');
    } finally {
      setTimeout(() => {
        setUploading(false);
        setUploadProgress('');
      }, 2000);
    }
  };

  const pollOCRStatus = async (fileId, attempts = 0) => {
    const maxAttempts = 30; // 5 minutes max (30 * 10 seconds)
    
    try {
      const statusResponse = await OCRService.getOCRStatus(fileId);
      
      if (statusResponse.success) {
        if (statusResponse.ocr_status === 'completed') {
          setUploadProgress('OCR processing completed!');
          const fileDetails = await OCRService.getFileDetails(fileId);
          showOCRResults(fileDetails, statusResponse);
          return;
        } else if (statusResponse.ocr_status === 'failed') {
          setUploadProgress('OCR processing failed');
          Alert.alert('OCR Error', 'Text extraction failed');
          return;
        }
      }

      // Continue polling if not completed and under max attempts
      if (attempts < maxAttempts) {
        setTimeout(() => {
          setUploadProgress(`OCR processing... (${attempts + 1}/${maxAttempts})`);
          pollOCRStatus(fileId, attempts + 1);
        }, 10000); // Check every 10 seconds
      } else {
        setUploadProgress('OCR processing timeout');
        Alert.alert('OCR Timeout', 'Processing is taking longer than expected');
      }
    } catch (error) {
      console.error('OCR status polling error:', error);
      setUploadProgress('Error checking OCR status');
    }
  };

  const showOCRResults = (file, ocrResult) => {
    const category = file.category || 'Miscellaneous';
    const hasText = ocrResult.ocr_text || ocrResult.has_text;
    
    Alert.alert(
      'OCR Processing Complete',
      `File: ${file.original_filename}\nCategory: ${category}\nText extracted: ${hasText ? 'Yes' : 'No'}`,
      [
        {
          text: 'View Details',
          onPress: () => navigation?.navigate('FileDetails', { fileId: file.id }),
        },
        { text: 'OK' },
      ]
    );
  };

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.title}>Upload Document</Text>
      
      {/* Category Selection */}
      {categories.length > 0 && (
        <View style={styles.categorySection}>
          <Text style={styles.sectionTitle}>Select Category (Optional)</Text>
          <ScrollView horizontal showsHorizontalScrollIndicator={false}>
            <TouchableOpacity
              style={[
                styles.categoryButton,
                !selectedCategory && styles.categoryButtonSelected,
              ]}
              onPress={() => setSelectedCategory(null)}
            >
              <Text style={[
                styles.categoryButtonText,
                !selectedCategory && styles.categoryButtonTextSelected,
              ]}>
                Auto-Categorize
              </Text>
            </TouchableOpacity>
            
            {categories.map((category) => (
              <TouchableOpacity
                key={category.id}
                style={[
                  styles.categoryButton,
                  selectedCategory === category.id && styles.categoryButtonSelected,
                ]}
                onPress={() => setSelectedCategory(category.id)}
              >
                <Text style={[
                  styles.categoryButtonText,
                  selectedCategory === category.id && styles.categoryButtonTextSelected,
                ]}>
                  {category.name}
                </Text>
              </TouchableOpacity>
            ))}
          </ScrollView>
        </View>
      )}

      {/* Upload Buttons */}
      <View style={styles.uploadSection}>
        <TouchableOpacity
          style={[styles.uploadButton, styles.documentButton]}
          onPress={selectDocument}
          disabled={uploading}
        >
          <Text style={styles.uploadButtonText}>📄 Upload Document</Text>
          <Text style={styles.uploadButtonSubtext}>PDF, DOC, DOCX</Text>
        </TouchableOpacity>

        <TouchableOpacity
          style={[styles.uploadButton, styles.imageButton]}
          onPress={selectImage}
          disabled={uploading}
        >
          <Text style={styles.uploadButtonText}>📷 Upload Image</Text>
          <Text style={styles.uploadButtonSubtext}>JPG, PNG</Text>
        </TouchableOpacity>
      </View>

      {/* Upload Progress */}
      {uploading && (
        <View style={styles.progressSection}>
          <ActivityIndicator size="large" color="#007AFF" />
          <Text style={styles.progressText}>{uploadProgress}</Text>
          <Text style={styles.progressSubtext}>
            OCR will automatically extract text and categorize your document
          </Text>
        </View>
      )}

      {/* OCR Info */}
      <View style={styles.infoSection}>
        <Text style={styles.infoTitle}>Automatic OCR Processing</Text>
        <Text style={styles.infoText}>
          • Text extraction from documents and images{'\n'}
          • Automatic categorization based on content{'\n'}
          • Professional, Banking, Medical, and more{'\n'}
          • Searchable text content
        </Text>
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    padding: 20,
    backgroundColor: '#f8f9fa',
  },
  title: {
    fontSize: 24,
    fontWeight: 'bold',
    marginBottom: 20,
    textAlign: 'center',
    color: '#333',
  },
  categorySection: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 10,
    color: '#333',
  },
  categoryButton: {
    backgroundColor: '#e9ecef',
    paddingVertical: 8,
    paddingHorizontal: 16,
    borderRadius: 20,
    marginRight: 10,
    borderWidth: 1,
    borderColor: '#dee2e6',
  },
  categoryButtonSelected: {
    backgroundColor: '#007AFF',
    borderColor: '#007AFF',
  },
  categoryButtonText: {
    color: '#495057',
    fontSize: 14,
    fontWeight: '500',
  },
  categoryButtonTextSelected: {
    color: 'white',
  },
  uploadSection: {
    marginBottom: 20,
  },
  uploadButton: {
    padding: 20,
    borderRadius: 12,
    marginBottom: 15,
    alignItems: 'center',
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  documentButton: {
    backgroundColor: '#28a745',
  },
  imageButton: {
    backgroundColor: '#17a2b8',
  },
  uploadButtonText: {
    color: 'white',
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 5,
  },
  uploadButtonSubtext: {
    color: 'white',
    fontSize: 14,
    opacity: 0.9,
  },
  progressSection: {
    alignItems: 'center',
    padding: 20,
    backgroundColor: 'white',
    borderRadius: 12,
    marginBottom: 20,
  },
  progressText: {
    marginTop: 10,
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  progressSubtext: {
    marginTop: 5,
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
  },
  infoSection: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 12,
    borderLeftWidth: 4,
    borderLeftColor: '#007AFF',
  },
  infoTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 10,
    color: '#333',
  },
  infoText: {
    fontSize: 14,
    color: '#666',
    lineHeight: 20,
  },
});

export default FileUpload;
