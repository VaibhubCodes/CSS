
// components/FilesList.js
import React, { useState, useEffect } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  RefreshControl,
  TextInput,
  Alert,
  Modal,
} from 'react-native';
import OCRService from '../services/ocrService';

const FilesList = ({ navigation }) => {
  const [files, setFiles] = useState([]);
  const [categories, setCategories] = useState([]);
  const [loading, setLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [showCategoryModal, setShowCategoryModal] = useState(false);

  useEffect(() => {
    loadFiles();
  }, [selectedCategory, searchQuery]);

  const loadFiles = async () => {
    try {
      setLoading(true);
      const response = await OCRService.getFiles(selectedCategory, searchQuery);
      
      if (response.files) {
        setFiles(response.files);
      }
      if (response.categories) {
        setCategories(response.categories);
      }
    } catch (error) {
      console.error('Failed to load files:', error);
      Alert.alert('Error', 'Failed to load files');
    } finally {
      setLoading(false);
    }
  };

  const onRefresh = async () => {
    setRefreshing(true);
    await loadFiles();
    setRefreshing(false);
  };

  const getOCRStatusIcon = (file) => {
    if (file.file_type === 'audio') return '🎵';
    
    // Check if file has OCR text or status
    if (file.ocr_text || file.ocr_status === 'completed') {
      return '✅'; // OCR completed
    } else if (file.ocr_status === 'processing') {
      return '⏳'; // OCR processing
    } else if (file.ocr_status === 'failed') {
      return '❌'; // OCR failed
    } else {
      return '📄'; // No OCR yet
    }
  };

  const getFileTypeIcon = (fileType) => {
    switch (fileType) {
      case 'document': return '📄';
      case 'image': return '🖼️';
      case 'audio': return '🎵';
      default: return '📎';
    }
  };

  const getCategoryColor = (categoryName) => {
    const colors = {
      'Professional': '#007AFF',
      'Banking': '#28a745',
      'Medical': '#dc3545',
      'Education': '#ffc107',
      'Personal': '#6f42c1',
      'Legal': '#fd7e14',
      'Miscellaneous': '#6c757d',
    };
    return colors[categoryName] || '#6c757d';
  };

  const renderFileItem = ({ item }) => (
    <TouchableOpacity
      style={styles.fileItem}
      onPress={() => navigation.navigate('FileDetails', { fileId: item.id })}
    >
      <View style={styles.fileHeader}>
        <View style={styles.fileIconContainer}>
          <Text style={styles.fileTypeIcon}>{getFileTypeIcon(item.file_type)}</Text>
          <Text style={styles.ocrStatusIcon}>{getOCRStatusIcon(item)}</Text>
        </View>
        
        <View style={styles.fileInfo}>
          <Text style={styles.fileName} numberOfLines={2}>
            {item.original_filename}
          </Text>
          <Text style={styles.fileDetails}>
            {item.file_size_display} • {new Date(item.upload_date).toLocaleDateString()}
          </Text>
        </View>

        <View style={[
          styles.categoryBadge,
          { backgroundColor: getCategoryColor(item.category) }
        ]}>
          <Text style={styles.categoryText} numberOfLines={1}>
            {item.category || 'Uncategorized'}
          </Text>
        </View>
      </View>

      {/* OCR Preview */}
      {item.ocr_text && (
        <View style={styles.ocrPreview}>
          <Text style={styles.ocrPreviewText} numberOfLines={2}>
            {item.ocr_text.substring(0, 100)}...
          </Text>
        </View>
      )}

      {/* Processing Status */}
      {item.ocr_status === 'processing' && (
        <View style={styles.processingStatus}>
          <ActivityIndicator size="small" color="#007AFF" />
          <Text style={styles.processingText}>Processing OCR...</Text>
        </View>
      )}
    </TouchableOpacity>
  );

  const renderCategoryModal = () => (
    <Modal
      visible={showCategoryModal}
      transparent={true}
      animationType="slide"
      onRequestClose={() => setShowCategoryModal(false)}
    >
      <View style={styles.modalOverlay}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Filter by Category</Text>
          
          <TouchableOpacity
            style={[
              styles.categoryOption,
              !selectedCategory && styles.categoryOptionSelected
            ]}
            onPress={() => {
              setSelectedCategory(null);
              setShowCategoryModal(false);
            }}
          >
            <Text style={[
              styles.categoryOptionText,
              !selectedCategory && styles.categoryOptionTextSelected
            ]}>
              All Files
            </Text>
          </TouchableOpacity>

          {categories.map((category) => (
            <TouchableOpacity
              key={category.id}
              style={[
                styles.categoryOption,
                selectedCategory === category.name && styles.categoryOptionSelected
              ]}
              onPress={() => {
                setSelectedCategory(category.name);
                setShowCategoryModal(false);
              }}
            >
              <View style={styles.categoryOptionContent}>
                <Text style={[
                  styles.categoryOptionText,
                  selectedCategory === category.name && styles.categoryOptionTextSelected
                ]}>
                  {category.name}
                </Text>
                <Text style={styles.categoryCount}>({category.count})</Text>
              </View>
            </TouchableOpacity>
          ))}

          <TouchableOpacity
            style={styles.modalCloseButton}
            onPress={() => setShowCategoryModal(false)}
          >
            <Text style={styles.modalCloseButtonText}>Close</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );

  if (loading && !refreshing) {
    return (
      <View style={styles.loadingContainer}>
        <ActivityIndicator size="large" color="#007AFF" />
        <Text style={styles.loadingText}>Loading files...</Text>
      </View>
    );
  }

  return (
    <View style={styles.container}>
      {/* Search and Filter Header */}
      <View style={styles.header}>
        <View style={styles.searchContainer}>
          <TextInput
            style={styles.searchInput}
            placeholder="Search files..."
            value={searchQuery}
            onChangeText={setSearchQuery}
            autoCapitalize="none"
          />
        </View>
        
        <TouchableOpacity
          style={styles.filterButton}
          onPress={() => setShowCategoryModal(true)}
        >
          <Text style={styles.filterButtonText}>
            {selectedCategory || 'All'} ▼
          </Text>
        </TouchableOpacity>
      </View>

      {/* OCR Statistics */}
      <View style={styles.statsContainer}>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>{files.length}</Text>
          <Text style={styles.statLabel}>Total Files</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>
            {files.filter(f => f.ocr_text || f.ocr_status === 'completed').length}
          </Text>
          <Text style={styles.statLabel}>OCR Processed</Text>
        </View>
        <View style={styles.statItem}>
          <Text style={styles.statValue}>
            {files.filter(f => f.ocr_status === 'processing').length}
          </Text>
          <Text style={styles.statLabel}>Processing</Text>
        </View>
      </View>

      {/* Files List */}
      <FlatList
        data={files}
        renderItem={renderFileItem}
        keyExtractor={(item) => item.id.toString()}
        refreshControl={
          <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
        }
        contentContainerStyle={styles.listContainer}
        showsVerticalScrollIndicator={false}
        ListEmptyComponent={
          <View style={styles.emptyContainer}>
            <Text style={styles.emptyText}>No files found</Text>
            <Text style={styles.emptySubtext}>
              Upload documents and images to get started with OCR
            </Text>
          </View>
        }
      />

      {renderCategoryModal()}
    </View>
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
    flexDirection: 'row',
    padding: 15,
    backgroundColor: 'white',
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  searchContainer: {
    flex: 1,
    marginRight: 10,
  },
  searchInput: {
    backgroundColor: '#f8f9fa',
    paddingHorizontal: 15,
    paddingVertical: 12,
    borderRadius: 8,
    fontSize: 16,
    borderWidth: 1,
    borderColor: '#dee2e6',
  },
  filterButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 15,
    paddingVertical: 12,
    borderRadius: 8,
    justifyContent: 'center',
    minWidth: 80,
  },
  filterButtonText: {
    color: 'white',
    fontSize: 14,
    fontWeight: '500',
    textAlign: 'center',
  },
  statsContainer: {
    flexDirection: 'row',
    backgroundColor: 'white',
    paddingVertical: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  statItem: {
    flex: 1,
    alignItems: 'center',
  },
  statValue: {
    fontSize: 20,
    fontWeight: 'bold',
    color: '#007AFF',
  },
  statLabel: {
    fontSize: 12,
    color: '#666',
    marginTop: 2,
  },
  listContainer: {
    padding: 15,
  },
  fileItem: {
    backgroundColor: 'white',
    borderRadius: 12,
    padding: 15,
    marginBottom: 10,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 2 },
    shadowOpacity: 0.1,
    shadowRadius: 4,
    elevation: 3,
  },
  fileHeader: {
    flexDirection: 'row',
    alignItems: 'flex-start',
  },
  fileIconContainer: {
    marginRight: 12,
    alignItems: 'center',
  },
  fileTypeIcon: {
    fontSize: 24,
  },
  ocrStatusIcon: {
    fontSize: 12,
    marginTop: 2,
  },
  fileInfo: {
    flex: 1,
    marginRight: 10,
  },
  fileName: {
    fontSize: 16,
    fontWeight: '600',
    color: '#333',
    marginBottom: 4,
  },
  fileDetails: {
    fontSize: 14,
    color: '#666',
  },
  categoryBadge: {
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 12,
    maxWidth: 100,
  },
  categoryText: {
    color: 'white',
    fontSize: 12,
    fontWeight: '500',
    textAlign: 'center',
  },
  ocrPreview: {
    marginTop: 10,
    padding: 10,
    backgroundColor: '#f8f9fa',
    borderRadius: 8,
    borderLeftWidth: 3,
    borderLeftColor: '#28a745',
  },
  ocrPreviewText: {
    fontSize: 14,
    color: '#666',
    fontStyle: 'italic',
  },
  processingStatus: {
    flexDirection: 'row',
    alignItems: 'center',
    marginTop: 10,
    padding: 8,
    backgroundColor: '#fff3cd',
    borderRadius: 6,
  },
  processingText: {
    marginLeft: 8,
    fontSize: 14,
    color: '#856404',
  },
  emptyContainer: {
    alignItems: 'center',
    marginTop: 50,
  },
  emptyText: {
    fontSize: 18,
    fontWeight: '600',
    color: '#333',
    marginBottom: 8,
  },
  emptySubtext: {
    fontSize: 14,
    color: '#666',
    textAlign: 'center',
  },
  modalOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
    justifyContent: 'flex-end',
  },
  modalContent: {
    backgroundColor: 'white',
    borderTopLeftRadius: 20,
    borderTopRightRadius: 20,
    maxHeight: '80%',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: '600',
    padding: 20,
    paddingBottom: 10,
    textAlign: 'center',
    borderBottomWidth: 1,
    borderBottomColor: '#e9ecef',
  },
  categoryOption: {
    padding: 15,
    borderBottomWidth: 1,
    borderBottomColor: '#f8f9fa',
  },
  categoryOptionSelected: {
    backgroundColor: '#e3f2fd',
  },
  categoryOptionContent: {
    flexDirection: 'row',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  categoryOptionText: {
    fontSize: 16,
    color: '#333',
  },
  categoryOptionTextSelected: {
    color: '#007AFF',
    fontWeight: '600',
  },
  categoryCount: {
    fontSize: 14,
    color: '#666',
  },
  modalCloseButton: {
    backgroundColor: '#007AFF',
    margin: 20,
    padding: 15,
    borderRadius: 8,
    alignItems: 'center',
  },
  modalCloseButtonText: {
    color: 'white',
    fontSize: 16,
    fontWeight: '600',
  },
});

export default FilesList;
