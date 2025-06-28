// PairedDocumentsScreen.js - List all paired documents with preview
import React, { useState, useEffect, useCallback } from 'react';
import {
  View,
  Text,
  FlatList,
  TouchableOpacity,
  Image,
  Alert,
  ActivityIndicator,
  RefreshControl,
  StyleSheet,
  SafeAreaView,
  ActionSheetIOS,
  Platform,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import { useFocusEffect, useNavigation } from '@react-navigation/native';
import { apiService } from '../services/apiService';

const PairedDocumentsScreen = () => {
  const navigation = useNavigation();
  
  const [pairedDocuments, setPairedDocuments] = useState({});
  const [isLoading, setIsLoading] = useState(true);
  const [refreshing, setRefreshing] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState(null);

  useFocusEffect(
    useCallback(() => {
      loadPairedDocuments();
    }, [])
  );

  const loadPairedDocuments = async (showRefresh = false) => {
    try {
      if (showRefresh) {
        setRefreshing(true);
      } else {
        setIsLoading(true);
      }
      
      const response = await apiService.getPairedDocuments();
      
      if (response.success) {
        setPairedDocuments(response.paired_documents);
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to load paired documents: ' + error.message);
    } finally {
      setIsLoading(false);
      setRefreshing(false);
    }
  };

  const onRefresh = () => {
    loadPairedDocuments(true);
  };

  const viewDocument = (documentPair, documentType) => {
    navigation.navigate('DocumentFlipViewer', {
      documentPair: {
        front: documentPair.front,
        back: documentPair.back,
      },
      documentType,
    });
  };

  const showDocumentOptions = (documentPair, documentType) => {
    const options = [
      'View Document',
      'Break Pair',
      'Cancel',
    ];

    const cancelButtonIndex = 2;
    const destructiveButtonIndex = 1;

    if (Platform.OS === 'ios') {
      ActionSheetIOS.showActionSheetWithOptions(
        {
          options,
          cancelButtonIndex,
          destructiveButtonIndex,
          title: `${documentType} Options`,
        },
        (buttonIndex) => {
          if (buttonIndex === 0) {
            viewDocument(documentPair, documentType);
          } else if (buttonIndex === 1) {
            confirmBreakPair(documentPair, documentType);
          }
        }
      );
    } else {
      // For Android, show custom alert
      Alert.alert(
        `${documentType} Options`,
        'Choose an action',
        [
          {
            text: 'View Document',
            onPress: () => viewDocument(documentPair, documentType),
          },
          {
            text: 'Break Pair',
            style: 'destructive',
            onPress: () => confirmBreakPair(documentPair, documentType),
          },
          {
            text: 'Cancel',
            style: 'cancel',
          },
        ]
      );
    }
  };

  const confirmBreakPair = (documentPair, documentType) => {
    Alert.alert(
      'Break Document Pair',
      `Are you sure you want to break the pair for ${documentType}? This will separate the front and back sides into individual documents.`,
      [
        {
          text: 'Cancel',
          style: 'cancel',
        },
        {
          text: 'Break Pair',
          style: 'destructive',
          onPress: () => breakDocumentPair(documentPair.front?.id || documentPair.back?.id),
        },
      ]
    );
  };

  const breakDocumentPair = async (fileId) => {
    try {
      setIsLoading(true);
      
      const response = await apiService.breakDocumentPair(fileId);
      
      if (response.success) {
        Alert.alert('Success', 'Document pair broken successfully');
        loadPairedDocuments();
      }
    } catch (error) {
      Alert.alert('Error', 'Failed to break document pair: ' + error.message);
    } finally {
      setIsLoading(false);
    }
  };

  const renderDocumentPair = ({ item: documentType }) => {
    const documentPairs = pairedDocuments[documentType];
    
    return (
      <View style={styles.documentTypeSection}>
        <Text style={styles.documentTypeTitle}>{documentType}</Text>
        
        {documentPairs.map((pair, index) => (
          <TouchableOpacity
            key={`${documentType}-${index}`}
            style={styles.documentPairCard}
            onPress={() => viewDocument(pair, documentType)}
            onLongPress={() => showDocumentOptions(pair, documentType)}
          >
            <View style={styles.documentPairContent}>
              <View style={styles.documentSides}>
                {/* Front Side Preview */}
                <View style={styles.documentSide}>
                  <Text style={styles.sideLabel}>FRONT</Text>
                  {pair.front ? (
                    <Image 
                      source={{ uri: pair.front.file_url }} 
                      style={styles.documentPreview}
                      defaultSource={require('../assets/document-placeholder.png')}
                    />
                  ) : (
                    <View style={styles.missingDocument}>
                      <Ionicons name="document-outline" size={24} color="#ccc" />
                      <Text style={styles.missingText}>Missing</Text>
                    </View>
                  )}
                </View>

                {/* Flip Icon */}
                <View style={styles.flipIcon}>
                  <Ionicons name="refresh" size={20} color="#007AFF" />
                </View>

                {/* Back Side Preview */}
                <View style={styles.documentSide}>
                  <Text style={styles.sideLabel}>BACK</Text>
                  {pair.back ? (
                    <Image 
                      source={{ uri: pair.back.file_url }} 
                      style={styles.documentPreview}
                      defaultSource={require('../assets/document-placeholder.png')}
                    />
                  ) : (
                    <View style={styles.missingDocument}>
                      <Ionicons name="document-outline" size={24} color="#ccc" />
                      <Text style={styles.missingText}>Missing</Text>
                    </View>
                  )}
                </View>
              </View>

              <View style={styles.documentInfo}>
                <Text style={styles.documentName}>{documentType}</Text>
                <Text style={styles.documentDetails}>
                  {pair.front && pair.back 
                    ? 'Complete pair' 
                    : `Missing ${!pair.front ? 'front' : 'back'} side`
                  }
                </Text>
                <Text style={styles.documentDate}>
                  Created: {new Date(pair.front?.upload_date || pair.back?.upload_date).toLocaleDateString()}
                </Text>
              </View>
            </View>

            <TouchableOpacity
              style={styles.optionsButton}
              onPress={() => showDocumentOptions(pair, documentType)}
            >
              <Ionicons name="ellipsis-vertical" size={20} color="#666" />
            </TouchableOpacity>
          </TouchableOpacity>
        ))}
      </View>
    );
  };

  const renderEmptyState = () => (
    <View style={styles.emptyState}>
      <Ionicons name="documents-outline" size={64} color="#ccc" />
      <Text style={styles.emptyStateTitle}>No Paired Documents</Text>
      <Text style={styles.emptyStateMessage}>
        Create your first document pair to see them here.
      </Text>
      <TouchableOpacity
        style={styles.createPairButton}
        onPress={() => navigation.navigate('DocumentPairing')}
      >
        <Ionicons name="add" size={20} color="#fff" />
        <Text style={styles.createPairButtonText}>Create Pair</Text>
      </TouchableOpacity>
    </View>
  );

  if (isLoading && !refreshing) {
    return (
      <SafeAreaView style={styles.container}>
        <View style={styles.header}>
          <TouchableOpacity onPress={() => navigation.goBack()}>
            <Ionicons name="arrow-back" size={24} color="#333" />
          </TouchableOpacity>
          <Text style={styles.headerTitle}>Paired Documents</Text>
          <TouchableOpacity onPress={() => navigation.navigate('DocumentPairing')}>
            <Ionicons name="add" size={24} color="#007AFF" />
          </TouchableOpacity>
        </View>
        <FlatList
          data={Object.keys(pairedDocuments)}
          renderItem={renderDocumentPair}
          keyExtractor={(item) => item}
          ListEmptyComponent={renderEmptyState}
          refreshControl={
            <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
          }
        />
      </SafeAreaView>
    );
  };

  return renderPairedDocuments();
};

export default PairedDocumentsScreen;