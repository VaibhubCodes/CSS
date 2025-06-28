import React, { useEffect, useState } from 'react';
import {
  View,
  Text,
  Modal,
  TouchableOpacity,
  StyleSheet,
  Alert,
  FlatList,
} from 'react-native';
import LinearGradient from 'react-native-linear-gradient';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import { BlurView } from '@react-native-community/blur';
import { launchCamera, launchImageLibrary } from 'react-native-image-picker';
import DocumentPicker from 'react-native-document-picker';
import { useNavigation } from '@react-navigation/native';
import { getCategories } from '../services/api';

const UploadItem = ({ isVisible, onClose, onUpload, category }) => {
  const navigation = useNavigation();
  const [categoryModalVisible, setCategoryModalVisible] = useState(false);
  const [categories, setCategories] = useState([]);
  const [pendingFile, setPendingFile] = useState(null);
  const [miscellaneousCategoryId, setMiscellaneousCategoryId] = useState(null);

  useEffect(() => {
    if (categoryModalVisible) {
      loadCategories();
    }
  }, [categoryModalVisible]);

  const loadCategories = async () => {
    try {
      const data = await getCategories();
      setCategories(data);
      
      // Find the Miscellaneous category ID
      const miscCategory = data.find(cat => cat.name === 'Miscellaneous');
      if (miscCategory) {
        setMiscellaneousCategoryId(miscCategory.id);
      }
    } catch (err) {
      Alert.alert('Error loading categories');
    }
  };

  const handleCategorySelect = (categoryId) => {
    if (pendingFile) {
      onUpload({ ...pendingFile, categoryId });
      setPendingFile(null);
      setCategoryModalVisible(false);
    }
  };

  const prepareUpload = (file) => {
    if (category) {
      onUpload({ ...file, categoryId: category });
    } else {
      setPendingFile(file);
      setCategoryModalVisible(true);
    }
  };

  const handleCamera = () => {
    launchCamera({ mediaType: 'photo' }, (response) => {
      if (response?.assets?.[0]) {
        prepareUpload(response.assets[0]);
      } else if (response?.errorMessage) {
        Alert.alert('Camera Error', response.errorMessage);
      }
    });
  };

  const handleGallery = () => {
    launchImageLibrary({ mediaType: 'photo' }, (response) => {
      if (response?.assets?.[0]) {
        prepareUpload(response.assets[0]);
      } else if (response?.errorMessage) {
        Alert.alert('Gallery Error', response.errorMessage);
      }
    });
  };

  const handleDocument = async () => {
    try {
      const res = await DocumentPicker.pick({
        type: [DocumentPicker.types.allFiles],
      });

      if (res?.[0]) {
        prepareUpload({
          uri: res[0].uri,
          name: res[0].name,
          type: res[0].type,
        });
      }
    } catch (err) {
      if (!DocumentPicker.isCancel(err)) {
        console.warn('Document Picker Error:', err);
      }
    }
  };

  if (!isVisible) return null;

  return (
    <Modal animationType="fade" transparent visible={isVisible} onRequestClose={onClose}>
      <View style={styles.modalOverlay}>
        <BlurView style={styles.blurBackground} blurType="light" blurAmount={10} />
        <View style={styles.modalContainer}>
          <TouchableOpacity onPress={onClose} style={styles.closeButton}>
            <Icon name="close" size={20} color="#777" />
          </TouchableOpacity>

          <Text style={styles.modalTitle}>Upload</Text>
          <Text style={styles.modalSubtitle}>Select a source</Text>
          <Icon name="cloud-upload-outline" size={40} color="#26458C" style={styles.uploadIcon} />

          <View style={styles.buttonRow}>
            <LinearGradient colors={['#426BB6', '#26458C']} style={styles.cameraButton}>
              <TouchableOpacity onPress={handleCamera}>
                <Text style={styles.cameraText}>Camera</Text>
              </TouchableOpacity>
            </LinearGradient>

            <TouchableOpacity style={styles.galleryButton} onPress={handleGallery}>
              <Text style={styles.galleryText}>Gallery</Text>
            </TouchableOpacity>
          </View>

          <TouchableOpacity onPress={handleDocument} style={styles.documentButton}>
            <Text style={styles.documentText}>Choose Document</Text>
          </TouchableOpacity>

          <Text style={styles.scanText}>
            Or, would you like to{' '}
            <Text style={styles.scanLink} onPress={() => {
              onClose();
              navigation.navigate('ScanDocumentScreen');
            }}>
              Scan
            </Text>?
          </Text>
        </View>

        {/* Category Selection Modal */}
        <Modal visible={categoryModalVisible} transparent animationType="slide">
          <View style={styles.categoryOverlay}>
            <View style={styles.categoryModal}>
              <Text style={styles.modalTitle}>Select Category</Text>
              <Text style={styles.categorySubtitle}>
                For automatic categorization, select Miscellaneous
              </Text>
              <FlatList
                data={categories}
                keyExtractor={(item) => item.id.toString()}
                renderItem={({ item }) => (
                  <TouchableOpacity
                    style={[
                      styles.categoryOption,
                      item.name === 'Miscellaneous' && styles.miscellaneousOption
                    ]}
                    onPress={() => handleCategorySelect(item.id)}
                  >
                    <Text 
                      style={[
                        styles.categoryText,
                        item.name === 'Miscellaneous' && styles.miscellaneousText
                      ]}
                    >
                      {item.name}
                      {item.name === 'Miscellaneous' && ' (Auto-Categorization)'}
                    </Text>
                  </TouchableOpacity>
                )}
              />
              <TouchableOpacity onPress={() => setCategoryModalVisible(false)}>
                <Text style={[styles.scanLink, { marginTop: 10 }]}>Cancel</Text>
              </TouchableOpacity>
            </View>
          </View>
        </Modal>
      </View>
    </Modal>
  );
};

const styles = StyleSheet.create({
  modalOverlay: { flex: 1, justifyContent: 'center', alignItems: 'center', backgroundColor: 'rgba(0,0,0,0.4)' },
  blurBackground: { ...StyleSheet.absoluteFillObject },
  modalContainer: {
    width: '80%',
    backgroundColor: '#FFF',
    borderRadius: 20,
    padding: 20,
    alignItems: 'center',
  },
  closeButton: { position: 'absolute', top: 10, right: 10 },
  modalTitle: { fontSize: 18, fontFamily: 'Poppins-Bold', color: '#000', textAlign: 'center', marginTop: 10 },
  modalSubtitle: { fontSize: 14, fontFamily: 'Poppins-Regular', color: '#777', textAlign: 'center', marginTop: 5 },
  uploadIcon: { marginVertical: 15 },
  buttonRow: { flexDirection: 'row', justifyContent: 'center', gap: 10, marginVertical: 10 },
  cameraButton: { borderRadius: 25, paddingVertical: 10, paddingHorizontal: 30, alignItems: 'center' },
  cameraText: { fontSize: 14, fontFamily: 'Poppins-Bold', color: '#FFF' },
  galleryButton: {
    borderWidth: 1,
    borderColor: '#26458C',
    borderRadius: 25,
    paddingVertical: 10,
    paddingHorizontal: 30,
    alignItems: 'center',
  },
  galleryText: { fontSize: 14, fontFamily: 'Poppins-Bold', color: '#26458C' },
  scanText: { fontSize: 12, fontFamily: 'Poppins-Regular', color: '#777', textAlign: 'center', marginTop: 10 },
  scanLink: { fontFamily: 'Poppins-Bold', color: '#426BB6' },
  documentButton: {
    marginTop: 10,
    borderWidth: 1,
    borderColor: '#26458C',
    borderRadius: 25,
    paddingVertical: 10,
    paddingHorizontal: 30,
  },
  documentText: {
    fontSize: 14,
    fontFamily: 'Poppins-Bold',
    color: '#26458C',
    textAlign: 'center',
  },
  categoryOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.6)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  categoryModal: {
    backgroundColor: 'white',
    width: '80%',
    borderRadius: 16,
    padding: 20,
    alignItems: 'center',
  },
  categoryOption: {
    paddingVertical: 10,
    borderBottomWidth: 1,
    borderColor: '#eee',
    width: '100%',
  },
  categoryText: {
    fontSize: 14,
    fontFamily: 'Poppins-Regular',
    textAlign: 'center',
  },
  categorySubtitle: {
    fontSize: 12,
    fontFamily: 'Poppins-Regular',
    color: '#777',
    textAlign: 'center',
    marginBottom: 10,
  },
  miscellaneousOption: {
    backgroundColor: 'rgba(66, 107, 182, 0.1)',
  },
  miscellaneousText: {
    color: '#426BB6',
    fontFamily: 'Poppins-Bold',
  },
});

export default UploadItem;