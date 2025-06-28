// FE/SparkleChat.js

import React, { useState, useRef, useEffect, useCallback } from 'react';
import {
  View, Text, TextInput, StyleSheet,
  TouchableOpacity, Image, ScrollView, ActivityIndicator,
  Platform, KeyboardAvoidingView, Alert // Added Alert
} from 'react-native';
import Icon from 'react-native-vector-icons/MaterialCommunityIcons';
import AudioRecorderPlayer, { AVEncoderAudioQualityIOSType, AVEncodingOption } from 'react-native-audio-recorder-player';
import RNFetchBlob from 'rn-fetch-blob';
import Sound from 'react-native-sound';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { useFocusEffect } from '@react-navigation/native';

// Initialize Sound
Sound.setCategory('Playback');

// --- Configuration ---
const API_BASE_URL = 'http://10.0.2.2:8000'; // Adjust if needed
const dirs = RNFetchBlob.fs.dirs;
const audioSet = {
  // iOS
  AVEncoderAudioQualityKeyIOS: AVEncoderAudioQualityIOSType.high,
  AVNumberOfChannelsKeyIOS: 2,
  AVFormatIDKeyIOS: AVEncodingOption.aac,
  // Android
  AudioEncoderAndroid: 3, // AAC
  AudioSourceAndroid: 1, // MIC
  OutputFormatAndroid: 2, // MPEG_4
};

// --- Helper Functions ---
const getAuthToken = async () => await AsyncStorage.getItem('accessToken');

// --- Component ---
const SparkleChat = ({ navigation }) => {
  const [message, setMessage] = useState('');
  const [chat, setChat] = useState([]);
  const [recording, setRecording] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [currentAudio, setCurrentAudio] = useState(null);
  const [recordSecs, setRecordSecs] = useState(0);
  const [recordTime, setRecordTime] = useState('00:00');
  // --- State for Conversation ID ---
  const [currentConversationId, setCurrentConversationId] = useState(null); // Initialize to null
  const audioRecorderPlayer = useRef(new AudioRecorderPlayer()).current;
  const scrollViewRef = useRef(null);

  // --- Sound Management ---
  const stopCurrentAudio = useCallback(() => {
    if (currentAudio) {
      currentAudio.stop(() => {
        currentAudio.release();
        setCurrentAudio(null);
      });
    }
  }, [currentAudio]);

  useFocusEffect(
    useCallback(() => {
      return () => stopCurrentAudio(); // Cleanup on blur
    }, [stopCurrentAudio])
  );

  const playAudioResponse = useCallback((url) => {
    if (!url) return;
    console.log("Attempting to play audio:", url);
    stopCurrentAudio();

    const sound = new Sound(url, null, (error) => {
      if (error) {
        console.log('Failed to load the sound', error);
        Alert.alert('Audio Error', 'Could not play the audio response.'); // User feedback
        return;
      }
      console.log('Audio loaded: duration ' + sound.getDuration() + 's');
      setCurrentAudio(sound);
      sound.play((success) => {
        if (!success) {
          console.log('Playback failed due to audio decoding errors');
          // Optional: Alert user if playback fails consistently
        }
        sound.release();
        setCurrentAudio(null);
      });
    });
  }, [stopCurrentAudio]);

  // --- Chat Management ---
  const addChatMessage = (sender, textOrObject, extraData = {}) => {
    let messageText;
    let viewFileData = null;
    let messageId = `${sender}-${Date.now()}-${Math.random()}`; // More unique key

    // Handle different inputs for the second argument
    if (typeof textOrObject === 'string') {
        messageText = textOrObject;
        // Check if extraData itself contains viewFile
        if (extraData && extraData.viewFile) {
            viewFileData = extraData.viewFile;
        }
    } else if (typeof textOrObject === 'object' && textOrObject !== null) {
        // Assuming the object is the full message item
        messageText = textOrObject.text;
        viewFileData = textOrObject.viewFile; // Extract viewFile
        // Preserve other potential fields from the object
        extraData = { ...textOrObject, ...extraData }; // Merge, extraData takes precedence if keys overlap
        if(textOrObject.id) messageId = textOrObject.id; // Use provided ID if available
    } else {
        messageText = "System Message: Invalid input format"; // Fallback for clarity
        sender = 'system'; // Mark as system message
    }

    setChat(prev => [
        ...prev,
        {
            id: messageId, // Use generated or provided ID
            sender,
            text: messageText,
            timestamp: Date.now(),
            viewFile: viewFileData, // Attach viewFile data to the message object
            ...extraData // Spread any other relevant data
        }
    ]);

    // Scroll to bottom
    setTimeout(() => scrollViewRef.current?.scrollToEnd({ animated: true }), 150); // Slightly longer delay
};


  // --- API Interaction ---
  const handleApiResponse = useCallback(async (apiResult) => {
    console.log('[handleApiResponse] Received API Result:', JSON.stringify(apiResult, null, 2));

    if (apiResult && apiResult.success && apiResult.data) {
      const data = apiResult.data;

      // --- Store/Update Conversation ID ---
      if (data.conversation_id) {
        setCurrentConversationId(data.conversation_id); // Update state
        console.log('[Conversation] Using conversation ID:', data.conversation_id);
      }

      const sparkleMsg = {
          sender: 'sparkle',
          text: data.response,
          id: data.interaction_id || `sparkle-${Date.now()}` // Use interaction ID if available
      };

      // --- Check for display_file action payload ---
      if (data.action?.type === 'display_file' && data.action?.payload?.success) {
         const payload = data.action.payload;
         // Prioritize specific fields, then fallbacks
         const fileUrl = payload.fileUrl || payload.file_url || payload.url || payload.direct_url;
         const fileName = payload.fileName || payload.file_name;
         if (fileUrl && fileName) {
             sparkleMsg.viewFile = {
                  fileUrl: fileUrl,
                  fileName: fileName,
                  fileType: payload.fileType || payload.file_type || 'unknown',
                  fileId: payload.fileId || payload.file_id // Include ID if available
             };
             console.log('[Sparkle] Action: Display File -> ', sparkleMsg.viewFile);
         } else {
              console.warn('[Sparkle] Display File action missing URL or Filename in payload:', payload);
         }
      }
      // --- Fallback check on file_details ---
      else if (data.file_details?.success && (data.file_details?.fileUrl || data.file_details?.file_url)){
           const details = data.file_details;
           const fileUrl = details.fileUrl || details.file_url || details.url || details.direct_url;
           const fileName = details.fileName || details.file_name;
           if(fileUrl && fileName) {
               sparkleMsg.viewFile = {
                   fileUrl: fileUrl,
                   fileName: fileName,
                   fileType: details.fileType || details.file_type || 'unknown',
                   fileId: details.fileId || details.file_id
               };
               console.log('[Sparkle] Fallback: Display File (via file_details) -> ', sparkleMsg.viewFile);
           } else {
               console.warn('[Sparkle] Fallback Display File missing URL or Filename in file_details:', details);
           }
      }

      addChatMessage('sparkle', sparkleMsg); // Pass the whole object

      // Play audio if available
      if (data.audio_url) {
        playAudioResponse(data.audio_url);
      }
    } else {
       // Improved error message extraction
       let errorMsg = 'Sorry, something went wrong.';
       if(apiResult && !apiResult.success) {
           errorMsg = apiResult.error || (apiResult.data?.response /* check error within data */) || errorMsg;
       } else if (apiResult && apiResult.data && !apiResult.data.response) {
           // Handle cases where success might be true but response is missing
           errorMsg = "Received an unexpected empty response.";
       }
       console.error('[API ERROR]', errorMsg, 'Full Response:', apiResult);
       addChatMessage('sparkle', errorMsg);
    }
  }, [playAudioResponse, addChatMessage]); // Include dependencies

  const sendApiRequest = useCallback(async (payload) => {
    setIsTyping(true);
    const token = await getAuthToken();
    if (!token) {
      console.error("Authentication token not found.");
      addChatMessage('sparkle', "Authentication error. Please log in again.");
      setIsTyping(false);
      return;
    }

    const isFormData = payload instanceof FormData;
    const headers = {
      'Authorization': `Bearer ${token}`,
    };
    // Let fetch/axios handle Content-Type for FormData
    if (!isFormData) {
      headers['Content-Type'] = 'application/json';
    }

    let body = payload;

    // --- Include Conversation ID ---
    if (currentConversationId) {
      if (isFormData) {
        body.append('conversation_id', currentConversationId);
      } else {
         // Ensure payload is an object if it's not FormData
         if(typeof body !== 'object' || body === null) {
            // If body was just text, wrap it
            if(typeof body === 'string'){ body = { text: body }; }
            else { body = {}; } // Fallback to empty object
         }
          body.conversation_id = currentConversationId;
      }
    }

    // Stringify JSON body
    if (!isFormData) {
      body = JSON.stringify(body);
    }

    try {
      console.log(`[API Request] Sending to /voice/api/process/`, isFormData ? '(FormData)' : body);
      const response = await fetch(`${API_BASE_URL}/voice/api/process/`, {
        method: 'POST',
        headers,
        body: body,
      });

       const contentType = response.headers.get("content-type");
       if (!response.ok) {
            let errorBody = `Request failed with status ${response.status}`;
            try { // Try to parse error JSON, but don't fail if it's not JSON
                 if (contentType && contentType.includes("application/json")) {
                    const errorJson = await response.json();
                    errorBody = errorJson.error || JSON.stringify(errorJson);
                 } else {
                    errorBody = await response.text();
                 }
            } catch (parseError) {
                 console.error("Failed to parse error response body:", parseError);
            }
            throw new Error(errorBody);
        }

        if (!contentType || !contentType.includes("application/json")) {
            const textResponse = await response.text();
            throw new Error(`Server returned non-JSON response (${response.status}): ${textResponse}`);
        }

      const result = await response.json();

      // --- Update Conversation ID from Response ---
      if (result.success && result.data?.conversation_id) {
        setCurrentConversationId(result.data.conversation_id);
        console.log("[Conversation] Updated conversation ID from response:", result.data.conversation_id);
      }

      handleApiResponse(result);

    } catch (err) {
      console.error('API Send Error:', err);
      addChatMessage('sparkle', `Error: ${err.message}`);
    } finally {
      setIsTyping(false);
    }
  }, [handleApiResponse, currentConversationId, addChatMessage]); // Add dependencies

  // --- Handlers ---
  const handleTextSend = () => {
    const textToSend = message.trim();
    if (!textToSend || isTyping || recording) return; // Prevent sending if busy or empty
    addChatMessage('user', textToSend);
    setMessage('');

    const payload = {
      text: textToSend,
      include_audio: true // Make this configurable if needed
    };
    sendApiRequest(payload); // sendApiRequest adds conversation_id
  };

  const handleStartRecord = async () => {
     if (isTyping) return; // Don't allow recording if Sparkle is typing
    console.log('Starting recording...');
    setRecording(true);
    setRecordSecs(0);
    try {
      const path = Platform.select({
        ios: `sparkle_rec_${Date.now()}.m4a`,
        android: `${dirs.CacheDir}/sparkle_rec_${Date.now()}.mp4`,
      });
      console.log(`Recording to path: ${path}`);
      const uri = await audioRecorderPlayer.startRecorder(path, audioSet); // Use configured audioSet
      console.log(`Recorder started, saving to URI: ${uri}`); // Log the actual save URI
      audioRecorderPlayer.addRecordBackListener((e) => {
        setRecordSecs(Math.floor(e.currentPosition / 1000));
        setRecordTime(audioRecorderPlayer.mmssss(Math.floor(e.currentPosition)));
      });
    } catch (err) {
      console.error('Failed to start recording', err);
      Alert.alert('Recording Error', 'Could not start audio recording.');
      setRecording(false);
    }
  };

  const handleStopRecord = async () => {
    console.log('Stopping recording...');
    setRecording(false);
    try {
      const resultUri = await audioRecorderPlayer.stopRecorder();
      audioRecorderPlayer.removeRecordBackListener();
      setRecordSecs(0);
      setRecordTime('00:00');
      console.log('Recording stopped, result URI:', resultUri);
      if (resultUri) { // Ensure URI is valid
         sendAudio(resultUri); // Send the recorded audio
      } else {
         console.error("Stop recorder did not return a valid URI.");
         addChatMessage('sparkle', 'Error: Could not save recording.');
      }
    } catch (err) {
      console.error('Failed to stop recording', err);
       Alert.alert('Recording Error', 'Could not stop audio recording properly.');
    }
  };

  const sendAudio = useCallback(async (filePathUri) => {
    console.log("Preparing to send audio:", filePathUri);
    if (!filePathUri || typeof filePathUri !== 'string') { // Check type
      console.error("File path URI is invalid:", filePathUri);
      addChatMessage('sparkle', 'Error: Recording path is invalid.');
      return;
    }

    const formData = new FormData();
    const fileName = filePathUri.split('/').pop();
    const fileType = Platform.OS === 'ios' ? 'audio/m4a' : (fileName.endsWith('.mp4') ? 'audio/mp4' : 'audio/aac'); // Adjust based on actual format

    formData.append('audio', {
      uri: Platform.OS === 'android' ? `file://${filePathUri}` : filePathUri, // Ensure 'file://' prefix on Android if needed
      name: fileName,
      type: fileType,
    });
    formData.append('include_audio', 'true');

    // sendApiRequest adds conversation_id
    sendApiRequest(formData);
  }, [sendApiRequest, addChatMessage]); // Add addChatMessage dependency

  // --- Function to Start New Conversation ---
  const startNewConversation = () => {
    stopCurrentAudio(); // Stop any playing audio
    setRecording(false); // Stop recording if active
    audioRecorderPlayer.stopRecorder().catch(()=>{/* ignore error */}); // Attempt to stop just in case
    audioRecorderPlayer.removeRecordBackListener(); // Remove listener
    setCurrentConversationId(null); // Reset the conversation ID
    setChat([]); // Clear the chat display
    setMessage(''); // Clear input field
    addChatMessage('system', 'New conversation started.'); // Optional system message
    console.log("[Conversation] Started new conversation.");
  };


  // --- File Viewer Navigation ---
  const openViewer = (fileUrl, fileName) => {
    if (fileUrl && fileName) {
      console.log(`[Navigation] Navigating to GoogleDocViewer for: ${fileName} URL: ${fileUrl}`);
      // Ensure GoogleDocViewer screen exists and can handle S3 presigned URLs
      navigation.navigate('GoogleDocViewer', { fileUrl, fileName });
    } else {
      console.error("Cannot open viewer: Missing fileUrl or fileName.", { fileUrl, fileName });
      Alert.alert('Error', "Sorry, I couldn't prepare the file for viewing.");
    }
  };

  // --- Rendering ---
  const renderMessage = useCallback((item, index) => {
    const isUser = item.sender === 'user';
    const isSparkle = item.sender === 'sparkle';
    const isSystem = item.sender === 'system'; // Handle system messages

    if(isSystem) {
      return (
        <View key={item.id || `system-${index}`} style={styles.systemMessageContainer}>
            <Text style={styles.systemMessageText}>{item.text}</Text>
        </View>
      )
    }

    return (
      <View
        key={item.id || `${item.sender}-${item.timestamp}-${index}`} // Use message ID if available
        style={[
          styles.messageBubbleContainer,
          isUser ? styles.userAlign : styles.sparkleAlign,
        ]}
      >
        {isSparkle && (
          <Image source={require('../../assets/images/Sparkle.png')} style={styles.sparkleIconSmall} />
        )}
        <View
          style={[
            styles.messageBubble,
            isUser ? styles.userBubble : styles.sparkleBubble,
          ]}
        >
          <Text style={isUser ? styles.userMessageText : styles.messageText}>
            {item.text}
          </Text>

          {/* --- Render 'View File' button --- */}
          {isSparkle && item.viewFile?.fileUrl && item.viewFile?.fileName && (
            <TouchableOpacity
              style={styles.viewBtn} // Use specific style
              onPress={() => openViewer(item.viewFile.fileUrl, item.viewFile.fileName)}
              activeOpacity={0.7}
            >
              <Text style={styles.viewText}>📄 View {item.viewFile.fileName}</Text>
            </TouchableOpacity>
          )}
        </View>
      </View>
    );
  }, [openViewer]); // Include openViewer dependency

  // --- Component Return ---
  return (
    <KeyboardAvoidingView
      behavior={Platform.OS === "ios" ? "padding" : "height"}
      style={styles.container}
      keyboardVerticalOffset={Platform.OS === "ios" ? 64 : 0}
    >
      {/* Header */}
      <View style={styles.header}>
        <TouchableOpacity onPress={() => navigation.goBack()}>
          <Icon name="arrow-left" size={22} color="#000" />
        </TouchableOpacity>
        <Text style={styles.title}>Sparkle</Text>
        {/* --- New Chat Button --- */}
        <TouchableOpacity onPress={startNewConversation} style={styles.newChatButton}>
          <Icon name="plus-circle-outline" size={24} color="#426BB6" />
          {/* Or use Text: <Text style={styles.newChatText}>New Chat</Text> */}
        </TouchableOpacity>
      </View>

      {/* Chat Area */}
      <ScrollView
        ref={scrollViewRef}
        contentContainerStyle={styles.chatContainer}
        onContentSizeChange={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
        onLayout={() => scrollViewRef.current?.scrollToEnd({ animated: true })}
      >
        {chat.length === 0 && !isTyping ? (
          <View style={styles.emptyContainer}>
            <Image source={require('../../assets/images/Sparklebot.png')} style={styles.emptyImage} resizeMode="contain" />
            <Text style={styles.emptyText}>Ask me anything about your files!</Text>
          </View>
        ) : (
          chat.map(renderMessage)
        )}

        {isTyping && (
          <View style={[styles.messageBubbleContainer, styles.sparkleAlign]}>
            <Image source={require('../../assets/images/Sparkle.png')} style={styles.sparkleIconSmall} />
            <View style={[styles.messageBubble, styles.sparkleBubble, styles.typingBubble]}>
              <ActivityIndicator size="small" color="#426BB6" style={{ marginRight: 8 }} />
              <Text style={styles.typingText}>Sparkle is thinking...</Text>
            </View>
          </View>
        )}
      </ScrollView>

      {/* Input Area */}
      <View style={styles.inputRow}>
        <TextInput
          value={message}
          onChangeText={setMessage}
          placeholder={recording ? `Recording... ${recordTime}` : "Ask anything..."}
          placeholderTextColor="#aaa"
          style={styles.input}
          editable={!recording && !isTyping} // Disable input while recording or typing
          multiline
        />
        <TouchableOpacity
          onPressIn={handleStartRecord}
          onPressOut={handleStopRecord}
          disabled={isTyping} // Disable mic if Sparkle is thinking
          style={[styles.micButton, isTyping && styles.disabledButton]} // Visual feedback when disabled
        >
          <Icon
            name="microphone"
            size={24}
            color={recording ? '#FF5252' : (isTyping ? '#ccc' : '#426BB6')}
          />
        </TouchableOpacity>
        <TouchableOpacity
          onPress={handleTextSend}
          disabled={!message.trim() || isTyping || recording} // Disable send if busy or empty
          style={[styles.sendButton, (!message.trim() || isTyping || recording) && styles.disabledButton]} // Visual feedback
         >
          <Icon
            name="send-circle"
            size={32} // Slightly larger send icon
            color={!message.trim() || isTyping || recording ? '#ccc' : '#426BB6'}
          />
        </TouchableOpacity>
      </View>
    </KeyboardAvoidingView>
  );
};

// --- Styles ---
const styles = StyleSheet.create({
    container: { flex: 1, backgroundColor: '#FAFAF8' },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingTop: Platform.OS === 'ios' ? 50 : 15,
        paddingBottom: 8,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#eee'
    },
    title: { fontSize: 18, fontFamily: 'Poppins-SemiBold', color: '#000' },
    // Style for New Chat Button
    newChatButton: {
        padding: 5, // Add padding for easier tapping
    },
    // Optional: Style for text if using text instead of icon
    // newChatText: {
    //     fontSize: 16,
    //     color: '#426BB6',
    //     fontFamily: 'Poppins-Medium',
    // },
    chatContainer: { padding: 16, paddingBottom: 20 },
    messageBubbleContainer: {
        flexDirection: 'row',
        marginBottom: 12,
        maxWidth: '85%',
    },
    userAlign: { alignSelf: 'flex-end', justifyContent: 'flex-end' },
    sparkleAlign: { alignSelf: 'flex-start', alignItems: 'flex-end' },
    sparkleIconSmall: { width: 24, height: 24, marginRight: 6, alignSelf: 'flex-end' },
    messageBubble: { paddingVertical: 10, paddingHorizontal: 14, borderRadius: 18 },
    userBubble: { backgroundColor: '#426BB6', borderTopRightRadius: 4 },
    sparkleBubble: { backgroundColor: '#EEF1F9', borderTopLeftRadius: 4, marginLeft: 30 },
    messageText: { fontSize: 14, fontFamily: 'Poppins-Regular', color: '#333', lineHeight: 20 },
    userMessageText: { color: '#fff', fontSize: 14, fontFamily: 'Poppins-Regular', lineHeight: 20 },
    inputRow: {
        flexDirection: 'row', alignItems: 'center', paddingHorizontal: 10, paddingVertical: 8,
        backgroundColor: '#fff', borderTopWidth: 1, borderTopColor: '#eee',
    },
    input: {
        flex: 1, minHeight: 40, maxHeight: 120, backgroundColor: '#f0f0f0',
        borderRadius: 20, paddingHorizontal: 15, paddingVertical: Platform.OS === 'ios' ? 10 : 8, // Adjust padding
        fontSize: 14, fontFamily: 'Poppins-Regular', marginRight: 8, color: '#000',
    },
    micButton: { padding: 8 },
    sendButton: { paddingLeft: 5, paddingRight: 5 },
    disabledButton: { opacity: 0.5 }, // Style for disabled buttons
    emptyContainer: { flex: 1, justifyContent: 'center', alignItems: 'center', paddingBottom: 100 },
    emptyImage: { width: 180, height: 180, marginBottom: 20, opacity: 0.7 },
    emptyText: { fontSize: 14, fontFamily: 'Poppins-Regular', color: '#aaa', textAlign: 'center' },
    // System Message Style
    systemMessageContainer: {
        alignSelf: 'center', // Center system messages
        marginVertical: 10,
        paddingHorizontal: 12,
        paddingVertical: 6,
        backgroundColor: '#e5e7eb', // A neutral background
        borderRadius: 12,
    },
    systemMessageText: {
        fontSize: 12,
        color: '#4b5563', // Darker grey text
        fontStyle: 'italic',
        textAlign: 'center',
    },
    // View File Button Style
    viewBtn: {
        marginTop: 10, // Space above the button
        marginBottom: 4, // Space below the button
        alignSelf: 'flex-start', // Align to the left within the bubble
        backgroundColor: 'rgba(66, 107, 182, 0.85)', // Slightly transparent theme color
        paddingHorizontal: 14,
        paddingVertical: 7,
        borderRadius: 16, // More rounded
        flexDirection: 'row', // Align icon and text
        alignItems: 'center',
        // Optional: Add subtle shadow/elevation if desired
        shadowColor: "#000",
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.1,
        shadowRadius: 1.5,
        elevation: 2,
    },
    viewText: {
        color: '#FFFFFF', // White text
        fontSize: 13,
        fontFamily: 'Poppins-Medium', // Use a medium weight font
        marginLeft: 6, // Space between icon and text (if using an icon component)
    },
    typingBubble: { flexDirection: 'row', alignItems: 'center' },
    typingText: { fontFamily: 'Poppins-Regular', fontSize: 13, color: '#666', fontStyle: 'italic' },
});

export default SparkleChat;