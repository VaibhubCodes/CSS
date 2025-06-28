import React, { useState, useRef, useContext, useEffect } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  Image,
  Animated,
  Modal,
  Alert,
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import LottieView from 'lottie-react-native';
import UploadItem from '../components/UploadItem';
import { uploadFile } from '../services/api';
import LinearGradient from 'react-native-linear-gradient';
import { ThemeContext } from '../context/ThemeContext';

const UploadingScreen = ({ route }) => {
  const { categoryName, categoryId } = route.params || {};
  const { theme } = useContext(ThemeContext);
  const [selectedFile, setSelectedFile] = useState(null);
  const [uploadProgress, setUploadProgress] = useState(0);
  const [isUploading, setIsUploading] = useState(false);
  const [showSuccess, setShowSuccess] = useState(false);
  const [modalVisible, setModalVisible] = useState(false);
  const [uploadResponse, setUploadResponse] = useState(null);
  const progressAnim = useRef(new Animated.Value(0)).current;

  const triggerUpload = async () => {
    if (!selectedFile?.uri || !selectedFile?.name || !selectedFile?.type) {
      Alert.alert('Invalid file', 'Please select a valid file');
      return;
    }

    setIsUploading(true);
    setUploadProgress(0);

    try {
      const res = await uploadFile(
        selectedFile.uri,
        'document',
        selectedFile.categoryId || categoryId,
        selectedFile.name
      );

      setUploadResponse(res);

      // Simulate upload progress with animation
      let progress = 0;
      const interval = setInterval(() => {
        progress += 10;
        setUploadProgress(progress);
        Animated.timing(progressAnim, {
          toValue: progress,
          duration: 100,
          useNativeDriver: false,
        }).start();

        if (progress >= 100) {
          clearInterval(interval);
          setIsUploading(false);
          setShowSuccess(true);
          
          // Display auto-categorization message if applicable
          if (res && res.auto_categorizing) {
            setTimeout(() => {
              Alert.alert(
                'Auto-Categorization',
                'Your document has been uploaded to Miscellaneous category and will be automatically categorized after OCR processing is complete.',
                [{ text: 'OK' }]
              );
            }, 1000);
          }
          
          setTimeout(() => {
            setShowSuccess(false);
            setSelectedFile(null);
            setUploadProgress(0);
            setUploadResponse(null);
          }, 2000);
        }
      }, 80);
    } catch (error) {
      setIsUploading(false);
      Alert.alert('Upload failed', error.message);
    }
  };

  const progressWidth = progressAnim.interpolate({
    inputRange: [0, 100],
    outputRange: ['0%', '100%'],
  });

  return (
    <View style={[styles.containerCentered, { backgroundColor: theme.background }]}>
      {!selectedFile ? (
        <View style={styles.centeredContent}>
          <Image
            source={require('../../assets/gifs/Videoupload.gif')}
            style={styles.gif}
          />

          <LinearGradient colors={['#426BB6', '#26458C']} style={styles.uploadButton}>
            <TouchableOpacity onPress={() => setModalVisible(true)}>
              <View style={styles.buttonContentSmall}>
                <Icon name="upload" size={20} color="white" />
                <Text style={styles.uploadButtonText}>Upload File</Text>
              </View>
            </TouchableOpacity>
          </LinearGradient>

          <Text style={[styles.infoText, { color: theme.textTertiary }]}>
            CrossStorage Intelligently sorts your files in related category and notifies you in no time.
          </Text>
        </View>
      ) : (
        <View style={styles.centeredContent}>
          <LottieView
            source={require('../../assets/animations/UpArrow.json')}
            autoPlay
            loop
            style={styles.animation}
          />

          <View style={styles.previewContainer}>
            <Text style={[styles.fileName, { color: theme.textPrimary }]}>{selectedFile.name}</Text>

            {!isUploading ? (
              <LinearGradient colors={['#426BB6', '#26458C']} style={styles.uploadButton}>
                <TouchableOpacity onPress={triggerUpload}>
                  <View style={styles.buttonContentSmall}>
                    <Icon name="cloud-upload" size={20} color="white" />
                    <Text style={styles.uploadButtonText}>Start Upload</Text>
                  </View>
                </TouchableOpacity>
              </LinearGradient>
            ) : (
              <View style={styles.progressContainer}>
                <View style={[styles.progressBar, { backgroundColor: theme.cardBackground }]}>
                  <Animated.View style={[styles.progressFill, { width: progressWidth, backgroundColor: theme.accent }]} />
                </View>
                <Text style={[styles.percentageText, { color: theme.accent }]}>{uploadProgress}%</Text>
              </View>
            )}
          </View>

          <Text style={[styles.infoText, { marginTop: 20, color: theme.textTertiary }]}>
            CrossStorage Intelligently sorts your files in related category and notifies you in no time.
          </Text>
        </View>
      )}

      <UploadItem
        isVisible={modalVisible}
        onClose={() => setModalVisible(false)}
        onUpload={(file) => {
          setSelectedFile(file);
          setModalVisible(false);
        }}
        category={categoryId}
      />

      <Modal visible={showSuccess} transparent animationType="fade">
        <View style={styles.successOverlay}>
          <View style={[styles.successModal, { backgroundColor: theme.cardBackground }]}>
            <LottieView
              source={require('../../assets/animations/Uploaded.json')}
              autoPlay
              loop={false}
              style={{ width: 120, height: 120 }}
            />
            <Text style={[styles.successTitle, { color: theme.textPrimary }]}>Upload Successful!</Text>
            <Text style={[styles.successSubtitle, { color: theme.textTertiary }]}>
              {uploadResponse && uploadResponse.auto_categorizing 
                ? 'Your file will be processed with OCR'
                : 'Your file has been uploaded'}
            </Text>
          </View>
        </View>
      </Modal>
    </View>
  );
};

const styles = StyleSheet.create({
  containerCentered: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  centeredContent: {
    alignItems: 'center',
    justifyContent: 'center',
    width: '100%',
  },
  uploadButton: {
    borderRadius: 25,
    marginTop: 10,
  },
  buttonContentSmall: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    paddingVertical: 10,
    paddingHorizontal: 20,
  },
  uploadButtonText: {
    color: 'white',
    fontSize: 14,
    marginLeft: 8,
    fontFamily: 'Poppins-Bold',
  },
  infoText: {
    fontSize: 13,
    marginTop: 10,
    textAlign: 'center',
    fontFamily: 'Poppins-Regular',
  },
  previewContainer: {
    alignItems: 'center',
    marginTop: 10,
    width: '100%',
  },
  fileName: {
    fontSize: 16,
    fontFamily: 'Poppins-Regular',
    marginBottom: 20,
  },
  progressContainer: {
    width: '100%',
    alignItems: 'center',
  },
  progressBar: {
    width: '80%',
    height: 10,
    borderRadius: 5,
    marginVertical: 20,
  },
  progressFill: {
    height: '100%',
    borderRadius: 5,
  },
  percentageText: {
    fontSize: 16,
    fontFamily: 'Poppins-Bold',
  },
  successOverlay: {
    flex: 1,
    backgroundColor: 'rgba(0,0,0,0.5)',
    justifyContent: 'center',
    alignItems: 'center',
  },
  successModal: {
    borderRadius: 20,
    padding: 25,
    alignItems: 'center',
  },
  successTitle: {
    fontSize: 18,
    fontFamily: 'Poppins-Bold',
    marginTop: 10,
  },
  successSubtitle: {
    fontSize: 14,
    fontFamily: 'Poppins-Regular',
    marginTop: 5,
  },
  animation: {
    width: 200,
    height: 200,
    marginBottom: 10,
  },
  gif: {
    width: 200,
    height: 200,
    marginBottom: 10,
    resizeMode: 'contain',
  },
});

export default UploadingScreen;