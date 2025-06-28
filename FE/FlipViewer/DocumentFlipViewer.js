// DocumentFlipViewer.js - Main flip viewer component
import React, { useState, useRef, useEffect } from 'react';
import {
  View,
  Text,
  Image,
  TouchableOpacity,
  Animated,
  Dimensions,
  StyleSheet,
  SafeAreaView,
  StatusBar,
  Alert,
  ActivityIndicator,
  PanGestureHandler,
  State,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import * as FileSystem from 'expo-file-system';
import { shareAsync } from 'expo-sharing';

const { width, height } = Dimensions.get('window');

const DocumentFlipViewer = ({ route, navigation }) => {
  const { documentPair, documentType } = route.params;
  
  // Animation states
  const [isFlipped, setIsFlipped] = useState(false);
  const [isAnimating, setIsAnimating] = useState(false);
  const flipAnimation = useRef(new Animated.Value(0)).current;
  const scaleAnimation = useRef(new Animated.Value(1)).current;
  
  // Image states
  const [frontImageLoaded, setFrontImageLoaded] = useState(false);
  const [backImageLoaded, setBackImageLoaded] = useState(false);
  const [imageError, setImageError] = useState(null);
  
  // Zoom and pan states
  const [scale, setScale] = useState(1);
  const translateX = useRef(new Animated.Value(0)).current;
  const translateY = useRef(new Animated.Value(0)).current;
  const lastScale = useRef(1);
  const lastTranslateX = useRef(0);
  const lastTranslateY = useRef(0);

  useEffect(() => {
    StatusBar.setHidden(true);
    return () => StatusBar.setHidden(false);
  }, []);

  const flipCard = () => {
    if (isAnimating) return;
    
    setIsAnimating(true);
    const toValue = isFlipped ? 0 : 1;
    
    Animated.sequence([
      Animated.timing(scaleAnimation, {
        toValue: 0.95,
        duration: 100,
        useNativeDriver: true,
      }),
      Animated.timing(flipAnimation, {
        toValue,
        duration: 600,
        useNativeDriver: true,
      }),
      Animated.timing(scaleAnimation, {
        toValue: 1,
        duration: 100,
        useNativeDriver: true,
      }),
    ]).start(() => {
      setIsFlipped(!isFlipped);
      setIsAnimating(false);
    });
  };

  const resetZoom = () => {
    Animated.parallel([
      Animated.timing(translateX, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
      Animated.timing(translateY, {
        toValue: 0,
        duration: 300,
        useNativeDriver: true,
      }),
    ]).start();
    
    setScale(1);
    lastScale.current = 1;
    lastTranslateX.current = 0;
    lastTranslateY.current = 0;
  };

  const handlePinch = (event) => {
    const { scale: eventScale } = event.nativeEvent;
    const newScale = lastScale.current * eventScale;
    
    if (newScale >= 0.5 && newScale <= 3) {
      setScale(newScale);
    }
  };

  const handlePinchEnd = () => {
    lastScale.current = scale;
    if (scale < 1) {
      resetZoom();
    }
  };

  const handlePan = (event) => {
    if (scale > 1) {
      const { translationX, translationY } = event.nativeEvent;
      
      translateX.setValue(lastTranslateX.current + translationX);
      translateY.setValue(lastTranslateY.current + translationY);
    }
  };

  const handlePanEnd = (event) => {
    if (scale > 1) {
      const { translationX, translationY } = event.nativeEvent;
      lastTranslateX.current += translationX;
      lastTranslateY.current += translationY;
    }
  };

  const downloadImage = async () => {
    try {
      const currentSide = isFlipped ? 'back' : 'front';
      const imageUrl = documentPair[currentSide]?.file_url;
      const filename = documentPair[currentSide]?.original_filename || `${documentType}_${currentSide}.jpg`;
      
      if (!imageUrl) {
        Alert.alert('Error', 'Image URL not available');
        return;
      }

      const downloadPath = `${FileSystem.documentDirectory}${filename}`;
      const downloadResult = await FileSystem.downloadAsync(imageUrl, downloadPath);
      
      if (downloadResult.status === 200) {
        await shareAsync(downloadResult.uri);
      } else {
        Alert.alert('Error', 'Failed to download image');
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to download image: ' + error.message);
    }
  };

  const frontRotateY = flipAnimation.interpolate({
    inputRange: [0, 1],
    outputRange: ['0deg', '180deg'],
  });

  const backRotateY = flipAnimation.interpolate({
    inputRange: [0, 1],
    outputRange: ['180deg', '360deg'],
  });

  const frontOpacity = flipAnimation.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [1, 0, 0],
  });

  const backOpacity = flipAnimation.interpolate({
    inputRange: [0, 0.5, 1],
    outputRange: [0, 0, 1],
  });

  if (!documentPair || (!documentPair.front && !documentPair.back)) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.errorContainer}>
          <Ionicons name="document-outline" size={64} color="#ccc" />
          <Text style={styles.errorText}>No document pair found</Text>
          <TouchableOpacity style={styles.backButton} onPress={() => navigation.goBack()}>
            <Text style={styles.backButtonText}>Go Back</Text>
          </TouchableOpacity>
        </View>
      </SafeAreaView>
    );
  }

  return (
    <SafeAreaView style={styles.container}>
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity style={styles.headerButton} onPress={() => navigation.goBack()}>
          <Ionicons name="arrow-back" size={24} color="#fff" />
        </TouchableOpacity>
        
        <Text style={styles.headerTitle} numberOfLines={1}>
          {documentType || 'Document'}
        </Text>
        
        <TouchableOpacity style={styles.headerButton} onPress={downloadImage}>
          <Ionicons name="download-outline" size={24} color="#fff" />
        </TouchableOpacity>
      </View>

      {/* Document Viewer */}
      <View style={styles.documentContainer}>
        <PanGestureHandler
          onGestureEvent={handlePan}
          onHandlerStateChange={(event) => {
            if (event.nativeEvent.state === State.END) {
              handlePinch(event);
            }
          }}
          minPointers={1}
          maxPointers={1}
          avgTouches
        >
          <Animated.View
            style={[
              styles.documentWrapper,
              {
                transform: [
                  { scale: scaleAnimation },
                  { scale },
                  { translateX },
                  { translateY },
                ],
              },
            ]}
          >
            {/* Front Side */}
            <Animated.View
              style={[
                styles.cardSide,
                {
                  transform: [{ rotateY: frontRotateY }],
                  opacity: frontOpacity,
                },
              ]}
            >
              {documentPair.front ? (
                <>
                  <Image
                    source={{ uri: documentPair.front.file_url }}
                    style={styles.documentImage}
                    resizeMode="contain"
                    onLoad={() => setFrontImageLoaded(true)}
                    onError={() => setImageError('Failed to load front image')}
                  />
                  {!frontImageLoaded && (
                    <View style={styles.loadingOverlay}>
                      <ActivityIndicator size="large" color="#007AFF" />
                      <Text style={styles.loadingText}>Loading front side...</Text>
                    </View>
                  )}
                </>
              ) : (
                <View style={styles.noImageContainer}>
                  <Ionicons name="document-outline" size={64} color="#ccc" />
                  <Text style={styles.noImageText}>Front side not available</Text>
                </View>
              )}
              
              <View style={styles.sideLabel}>
                <Text style={styles.sideLabelText}>FRONT</Text>
              </View>
            </Animated.View>

            {/* Back Side */}
            <Animated.View
              style={[
                styles.cardSide,
                styles.cardBack,
                {
                  transform: [{ rotateY: backRotateY }],
                  opacity: backOpacity,
                },
              ]}
            >
              {documentPair.back ? (
                <>
                  <Image
                    source={{ uri: documentPair.back.file_url }}
                    style={styles.documentImage}
                    resizeMode="contain"
                    onLoad={() => setBackImageLoaded(true)}
                    onError={() => setImageError('Failed to load back image')}
                  />
                  {!backImageLoaded && (
                    <View style={styles.loadingOverlay}>
                      <ActivityIndicator size="large" color="#007AFF" />
                      <Text style={styles.loadingText}>Loading back side...</Text>
                    </View>
                  )}
                </>
              ) : (
                <View style={styles.noImageContainer}>
                  <Ionicons name="document-outline" size={64} color="#ccc" />
                  <Text style={styles.noImageText}>Back side not available</Text>
                </View>
              )}
              
              <View style={styles.sideLabel}>
                <Text style={styles.sideLabelText}>BACK</Text>
              </View>
            </Animated.View>
          </Animated.View>
        </PanGestureHandler>
      </View>

      {/* Controls */}
      <View style={styles.controls}>
        <TouchableOpacity
          style={[styles.controlButton, { opacity: isAnimating ? 0.5 : 1 }]}
          onPress={flipCard}
          disabled={isAnimating}
        >
          <Ionicons name="refresh" size={24} color="#fff" />
          <Text style={styles.controlButtonText}>
            {isFlipped ? 'Show Front' : 'Show Back'}
          </Text>
        </TouchableOpacity>

        {scale > 1 && (
          <TouchableOpacity style={styles.controlButton} onPress={resetZoom}>
            <Ionicons name="contract-outline" size={24} color="#fff" />
            <Text style={styles.controlButtonText}>Reset Zoom</Text>
          </TouchableOpacity>
        )}
      </View>

      {/* Side Indicator */}
      <View style={styles.sideIndicator}>
        <View style={[styles.dot, !isFlipped && styles.activeDot]} />
        <View style={[styles.dot, isFlipped && styles.activeDot]} />
      </View>

      {/* Instructions */}
      <View style={styles.instructions}>
        <Text style={styles.instructionText}>
          Tap flip button or swipe to see {isFlipped ? 'front' : 'back'} side
        </Text>
        {scale === 1 && (
          <Text style={styles.instructionText}>
            Pinch to zoom • Pan to move when zoomed
          </Text>
        )}
      </View>

      {imageError && (
        <View style={styles.errorBanner}>
          <Text style={styles.errorBannerText}>{imageError}</Text>
          <TouchableOpacity onPress={() => setImageError(null)}>
            <Ionicons name="close" size={20} color="#fff" />
          </TouchableOpacity>
        </View>
      )}
    </SafeAreaView>
  );
};

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: '#000',
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 16,
    paddingVertical: 12,
    backgroundColor: 'rgba(0, 0, 0, 0.8)',
    borderBottomWidth: 1,
    borderBottomColor: 'rgba(255, 255, 255, 0.1)',
  },
  headerButton: {
    padding: 8,
    borderRadius: 20,
    backgroundColor: 'rgba(255, 255, 255, 0.1)',
  },
  headerTitle: {
    color: '#fff',
    fontSize: 18,
    fontWeight: '600',
    flex: 1,
    textAlign: 'center',
    marginHorizontal: 16,
  },
  documentContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
  },
  documentWrapper: {
    width: width - 40,
    height: height * 0.6,
    borderRadius: 12,
    elevation: 8,
    shadowColor: '#000',
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
  },
  cardSide: {
    position: 'absolute',
    width: '100%',
    height: '100%',
    borderRadius: 12,
    backgroundColor: '#fff',
    backfaceVisibility: 'hidden',
    overflow: 'hidden',
  },
  cardBack: {
    transform: [{ rotateY: '180deg' }],
  },
  documentImage: {
    width: '100%',
    height: '100%',
    borderRadius: 12,
  },
  loadingOverlay: {
    position: 'absolute',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    backgroundColor: 'rgba(255, 255, 255, 0.9)',
    justifyContent: 'center',
    alignItems: 'center',
    borderRadius: 12,
  },
  loadingText: {
    marginTop: 12,
    color: '#007AFF',
    fontSize: 16,
    fontWeight: '500',
  },
  noImageContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: '#f5f5f5',
  },
  noImageText: {
    marginTop: 12,
    color: '#999',
    fontSize: 16,
  },
  sideLabel: {
    position: 'absolute',
    top: 12,
    left: 12,
    backgroundColor: 'rgba(0, 0, 0, 0.7)',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 4,
  },
  sideLabelText: {
    color: '#fff',
    fontSize: 12,
    fontWeight: '600',
  },
  controls: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingVertical: 16,
    gap: 16,
  },
  controlButton: {
    flexDirection: 'row',
    alignItems: 'center',
    backgroundColor: '#007AFF',
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderRadius: 24,
    gap: 8,
  },
  controlButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '500',
  },
  sideIndicator: {
    flexDirection: 'row',
    justifyContent: 'center',
    alignItems: 'center',
    gap: 8,
    paddingVertical: 8,
  },
  dot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: 'rgba(255, 255, 255, 0.3)',
  },
  activeDot: {
    backgroundColor: '#007AFF',
    width: 20,
  },
  instructions: {
    alignItems: 'center',
    paddingHorizontal: 20,
    paddingBottom: 16,
  },
  instructionText: {
    color: 'rgba(255, 255, 255, 0.7)',
    fontSize: 14,
    textAlign: 'center',
    marginVertical: 2,
  },
  errorContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 20,
  },
  errorText: {
    color: '#fff',
    fontSize: 18,
    marginTop: 16,
    marginBottom: 24,
    textAlign: 'center',
  },
  backButton: {
    backgroundColor: '#007AFF',
    paddingHorizontal: 24,
    paddingVertical: 12,
    borderRadius: 24,
  },
  backButtonText: {
    color: '#fff',
    fontSize: 16,
    fontWeight: '500',
  },
  errorBanner: {
    position: 'absolute',
    top: 100,
    left: 20,
    right: 20,
    backgroundColor: '#FF3B30',
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    padding: 12,
    borderRadius: 8,
  },
  errorBannerText: {
    color: '#fff',
    fontSize: 14,
    flex: 1,
  },
});

export default DocumentFlipViewer;