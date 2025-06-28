
// components/FileDetails.js
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  ScrollView,
  StyleSheet,
  TouchableOpacity,
  Alert,
  ActivityIndicator,
  Share,
} from 'react-native';
import OCRService from '../services/ocrService';

const FileDetails = ({ route, navigation }) => {
  const { fileId } = route.params;
  const [file, setFile] = useState(null);
  const [ocrStatus, setOcrStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [processingOCR, setProcessingOCR] = useState(false);
  const [showFullText, setShowFullText] = useState(false);

  useEffect(() => {
    loadFileDetails();
  }, [fileId]);

  const loadFileDetails = async () => {
    try {
      setLoading(true);
      
      // Load file details and OCR status
      const [fileResponse, ocrResponse] = await Promise.all([
        OCRService.getFileDetails(fileId),
        OCRService.getOCRStatus(fileId),
      ]);

      setFile(fileResponse);
      setOcrStatus(ocrResponse);
    } catch (error) {
      console.error('Failed to load file details:', error);
      Alert.alert('Error', 'Failed to load file details');
    } finally {
      setLoading(false);
    }
  };

  const processOCR = async () => {
    try {
      setProcessingOCR(true);
      const response = await OCRService.processOCR(fileId);
      
      if (response.success) {
        Alert.alert('OCR Started', 'Text extraction has been initiated');
        // Poll for completion
        pollOCRStatus();
      } else {
        Alert.alert('Error', response.error || 'Failed to start OCR');
      }
    } catch (error) {
      console.error('OCR processing error:', error);
      Alert.alert('Error', 'Failed to process OCR');
    } finally {
      setProcessingOCR(false);
    }
  };

  const pollOCRStatus = async (attempts = 0) => {
    const maxAttempts = 30;
    
    try {
      const response = await OCRService.getOCRStatus(fileId);
      
      if (response.success && response.ocr_status === 'completed') {
        await loadFileDetails(); // Reload to get updated data
        Alert.alert('OCR Complete', 'Text extraction completed successfully');
        return;
      }

      if (attempts < maxAttempts) {
        setTimeout(() => pollOCRStatus(attempts + 1), 5000);
      }
    } catch (error) {
      console.error('OCR polling error:', error);
    }
  };

  const shareOCRText = async () => {
    if (ocrStatus?.ocr_text) {
      try {
        await Share.share({
          message: `OCR Text from ${file?.original_filename}:\n\n${ocrStatus.ocr_text}`,
          title: 'OCR Text',
        });
      } catch (error) {
        console.error('Share error:', error);
      }
    }
  };

  const getStatusColor = (status) => {
    switch (status) {
      case 'completed': return '#28a745';
      case 'processing': return '#ffc107';
      case 'failed': return '#dc3545';
      case 'not_started': return '#6c757d';
      default: return '#6c757d';
    }
  };

  const getStatusText = (status) => {
    switch (status) {
      case 'completed': return 'Completed';
      case 'processing': return 'Processing...';
      case 'failed': return 'Failed';
      case 'not_started': return 'Not Started';
      default: return 'Unknown';
    }
  };

  if (loading) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading file details...</Text>
      </View>
    );
  }

  return (
    <ScrollView style={styles.container}>
      {/* File Information */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>File Information</Text>
        <View style={styles.infoCard}>
          <Text style={styles.fileName}>{file?.original_filename}</Text>
          <Text style={styles.fileInfo}>Type: {file?.file_type}</Text>
          <Text style={styles.fileInfo}>Size: {file?.file_size_display}</Text>
          <Text style={styles.fileInfo}>Category: {file?.category || 'Uncategorized'}</Text>
          <Text style={styles.fileInfo}>
            Uploaded: {new Date(file?.upload_date).toLocaleDateString()}
          </Text>
        </View>
      </View>

      {/* OCR Status */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>OCR Status</Text>
        <View style={styles.ocrStatusCard}>
          <View style={styles.statusRow}>
            <Text style={styles.statusLabel}>Status:</Text>
            <View style={[
              styles.statusBadge,
              { backgroundColor: getStatusColor(ocrStatus?.ocr_status) }
            ]}>
              <Text style={styles.statusText}>
                {getStatusText(ocrStatus?.ocr_status)}
              </Text>
            </View>
          </View>

          {ocrStatus?.ocr_status === 'not_started' && file?.file_type !== 'audio' && (
            <TouchableOpacity
              style={styles.processButton}
              onPress={processOCR}
              disabled={processingOCR}
            >
              {processingOCR ? (
                <ActivityIndicator color="white" />
              ) : (
                <Text style={styles.processButtonText}>Start OCR Processing</Text>
              )}
            </TouchableOpacity>
          )}
        </View>
      </View>

      {/* OCR Text Content */}
      {ocrStatus?.ocr_text && (
        <View style={styles.section}>
          <View style={styles.textHeader}>
            <Text style={styles.sectionTitle}>Extracted Text</Text>
            <TouchableOpacity onPress={shareOCRText} style={styles.shareButton}>
              <Text style={styles.shareButtonText}>Share</Text>
            </TouchableOpacity>
          </View>
          
          <View style={styles.textCard}>
            <Text style={styles.textPreview}>
              {showFullText 
                ? ocrStatus.ocr_text 
                : `${ocrStatus.ocr_text.substring(0, 300)}...`
              }
            </Text>
            
            {ocrStatus.ocr_text.length > 300 && (
              <TouchableOpacity
                style={styles.toggleButton}
                onPress={() => setShowFullText(!showFullText)}
              >
                <Text style={styles.toggleButtonText}>
                  {showFullText ? 'Show Less' : 'Show More'}
                </Text>
              </TouchableOpacity>
            )}
          </View>
        </View>
      )}

      {/* OCR Features Info */}
      <View style={styles.section}>
        <Text style={styles.sectionTitle}>OCR Features</Text>
        <View style={styles.featuresCard}>
          <Text style={styles.featureItem}>✓ Automatic text extraction</Text>
          <Text style={styles.featureItem}>✓ Smart categorization</Text>
          <Text style={styles.featureItem}>✓ Searchable content</Text>
          <Text style={styles.featureItem}>✓ Support for PDF, images, and documents</Text>
        </View>
      </View>
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
    backgroundColor: '#f8f9fa',
  },
  loadingText: {
    marginTop: 10,
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
  fileName: {
    fontSize: 18,
    fontWeight: '600',
    marginBottom: 10,
    color: '#333',
  },
  fileInfo: {
    fontSize: 16,
    marginBottom: 5,
    color: '#666',
  },
  ocrStatusCard: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  statusRow: {
    flexDirection: 'row',
    alignItems: 'center',
    marginBottom: 15,
  },
  statusLabel: {
    fontSize: 16,
    marginRight: 10,
    color: '#333',
  },
  statusBadge: {
    paddingHorizontal: 12,
    paddingVertical: 6,
    borderRadius: 20,
  },
  statusText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
  },
  processButton: {
    backgroundColor: '#007AFF',
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  processButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
  textHeader: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: 10,
  },
  shareButton: {
    backgroundColor: '#28a745',
    paddingHorizontal: 15,
    paddingVertical: 8,
    borderRadius: 6,
  },
  shareButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
  },
  textCard: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  textPreview: {
    fontSize: 14,
    lineHeight: 20,
    color: '#333',
    marginBottom: 10,
  },
  toggleButton: {
    alignSelf: 'flex-start',
    paddingVertical: 8,
  },
  toggleButtonText: {
    color: '#007AFF',
    fontSize: 14,
    fontWeight: '500',
  },
  featuresCard: {
    backgroundColor: 'white',
    padding: 20,
    borderRadius: 12,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  featureItem: {
    fontSize: 16,
    marginBottom: 8,
    color: '#666',
  },
});

export default FileDetails;