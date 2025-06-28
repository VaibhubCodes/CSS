Okay, here is a comprehensive `FEguide.md` file tailored for the React Native developer integrating with the updated Django backend, including the refined AI features and response handling based on our discussion and the PDF examples.

---

# `FEguide.md` - Frontend Integration Guide for CrossStorage & Sparkle

## 1. Introduction

This guide provides instructions and examples for integrating the React Native frontend application with the CrossStorage Django backend API, including the Sparkle AI assistant features.

**Base API URL:**

All API endpoints assume the following base URL. Ensure this is correctly configured in your environment. For local development with an Android emulator:

```
const API_BASE_URL = 'http://10.0.2.2:8000'; // Adjust if needed for iOS or different setup
```

## 2. Authentication

Authentication uses JWT (JSON Web Tokens). After successful login or email verification, the backend provides an `access` token and a `refresh` token.

*   **Storage:** Store both tokens securely, preferably using `AsyncStorage`.
*   **API Requests:** Include the `access` token in the `Authorization` header for all protected API calls:
    ```
    Authorization: Bearer <your_access_token>
    ```
*   **Token Refresh:** Use the `refresh` token to obtain a new `access` token when the current one expires using the `/auth/api/mobile/token/refresh/` endpoint.

### Key Auth Endpoints:

*   **Login:** `POST /auth/api/mobile/login/`
    *   **Body:** `{ "username": "email_or_username", "password": "your_password" }`
    *   **Response:** `{ success: true, user: {...}, tokens: { refresh: "...", access: "..." } }` or `{ success: false, error: "..." }`
*   **Signup:** `POST /auth/api/mobile/register/`
    *   **Body:** `{ "username": "...", "email": "...", "password": "...", "confirm_password": "..." }`
    *   **Response:** `{ success: true, message: "...", email: "..." }` (Triggers OTP) or `{ success: false, error: "..." }`
*   **Verify Email:** `POST /auth/api/mobile/verify-email/`
    *   **Body:** `{ "email": "...", "otp": "..." }`
    *   **Response:** `{ success: true, message: "...", tokens: {...}, user: {...} }` or `{ success: false, error: "..." }`
*   **Resend Verification:** `POST /auth/api/resend-verification/` (Check backend `users/urls.py` if a mobile specific one exists, otherwise use this)
    *   **Body:** `{ "email": "..." }`
    *   **Response:** `{ success: true, message: "..." }` or `{ success: false, error: "..." }`
*   **Google Sign-In:**
    1.  Use `@react-native-google-signin/google-signin` on the frontend to get the `idToken`.
    2.  Send this token to the backend: `POST /auth/api/google/` (Confirm if `/api/mobile/google/` exists, otherwise use this standard one).
    *   **Body:** `{ "token": "google_id_token" }`
    *   **Response:** `{ success: true, message: "...", tokens: {...}, user: {...}, is_new_user: bool }` or `{ success: false, error: "..." }`
*   **Token Refresh:** `POST /auth/api/mobile/token/refresh/`
    *   **Body:** `{ "refresh": "your_refresh_token" }`
    *   **Response:** `{ success: true, tokens: { access: "...", refresh: "..." }, user: {...} }` or `{ success: false, error: "..." }`

### Example API Service Setup (`src/services/api.js` - Partial)

```javascript
import axios from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';

const API_BASE_URL = 'http://10.0.2.2:8000'; // Or your actual backend URL

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Interceptor to add the token to requests
apiClient.interceptors.request.use(
  async (config) => {
    const token = await AsyncStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    // Important for file uploads using FormData
    if (config.data instanceof FormData) {
      // Let axios set the correct multipart header
      delete config.headers['Content-Type'];
    }
    return config;
  },
  (error) => {
    return Promise.reject(error);
  }
);

// Add interceptor for refreshing token (example, adapt as needed)
// apiClient.interceptors.response.use( ... logic to handle 401 and refresh token ... );

export default apiClient;

// Example usage (adapt based on your structure)
export const loginUser = (credentials) => apiClient.post('/auth/api/mobile/login/', credentials);
export const registerUser = (userData) => apiClient.post('/auth/api/mobile/register/', userData);
// ... other API functions
```

## 3. Core File Management APIs

These endpoints use the standard mobile response format: `{ success: bool, data: {...} | error: "..." }`. Ensure the `Authorization: Bearer <token>` header is sent.

*   **List Files:** `GET /file_management/api/mobile/files/`
    *   **Query Params (Optional):** `category` (name), `file_type` (document, image, audio), `search` (keyword)
    *   **Response Data:** `{ files: [...UserFileSerializer], categories: [...] }`
*   **Get File Detail:** `GET /file_management/api/mobile/files/<file_id>/`
    *   **Response Data:** `{ ...UserFileSerializer, ocr_text?: "...", ocr_status?: "..." }`
*   **Upload File:** `POST /file_management/api/mobile/upload/`
    *   **Body:** `FormData` containing:
        *   `file`: The file object (`{ uri, name, type }`)
        *   `file_type`: 'document', 'image', or 'audio'
        *   `category_id` (Optional): ID of the user-selected category. If omitted or invalid, auto-categorization will occur after OCR.
    *   **Response Data:** `{ file: {...UserFileSerializer}, message: "...", storage_info?: {...}, auto_categorizing: true/false }`
*   **Delete File:** `DELETE /file_management/api/mobile/files/<file_id>/`
    *   **Response Data:** `{ message: "..." }`
*   **Move File:** `POST /file_management/api/mobile/files/<file_id>/move/`
    *   **Body:** `{ "category_id": <target_category_id> }`
    *   **Response Data:** `{ message: "...", file: {...UserFileSerializer} }`
*   **Rename File:** `POST /file_management/api/mobile/files/<file_id>/rename/`
    *   **Body:** `{ "new_name": "new_file_name.ext" }`
    *   **Response Data:** `{ message: "...", file: {...UserFileSerializer} }`
*   **Share File:** `POST /file_management/api/mobile/files/<file_id>/share/`
    *   **Response Data:** `{ message: "...", share_url: "...", expires_in: "..." }` (Provides temporary S3 URL)
*   **Lock File:** `POST /file_management/api/mobile/files/<file_id>/lock/`
    *   **Body:** `{ "password": "..." }`
    *   **Response Data:** `{ message: "..." }`
*   **Unlock File:** `POST /file_management/api/mobile/files/<file_id>/unlock/`
    *   **Body:** `{ "password": "..." }`
    *   **Response Data:** `{ message: "..." }`

### Example File Upload (`src/services/api.js` or similar)

```javascript
export const uploadMobileFile = async (fileUri, fileType, fileName, fileMimeType, categoryId = null) => {
  const formData = new FormData();
  formData.append('file', {
    uri: fileUri,
    name: fileName, // Use original filename
    type: fileMimeType, // e.g., 'application/pdf', 'image/jpeg'
  });
  formData.append('file_type', fileType); // 'document', 'image', or 'audio'
  if (categoryId) {
    formData.append('category_id', categoryId.toString());
  }

  try {
    // Use fetch directly for FormData or ensure Axios config is correct
    const token = await AsyncStorage.getItem('accessToken');
    const response = await fetch(`${API_BASE_URL}/file_management/api/mobile/upload/`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            // Content-Type is set automatically by fetch for FormData
        },
        body: formData,
    });

    const data = await response.json();

    if (!response.ok) {
        throw new Error(data.error || `HTTP error! status: ${response.status}`);
    }
    return data; // Should be { success: true, data: { file: ..., ... } }

  } catch (error) {
    console.error('Mobile Upload Error:', error);
    throw error; // Re-throw for handling in the component
  }
};
```

### Automatic File Categorization

The backend now supports automatic categorization of document files based on OCR text analysis:

1. **How it works:**
   * When uploading a document file without specifying a `category_id`, the system will:
     * Initially assign the file to "Miscellaneous" category
     * Run OCR on the document to extract text
     * Analyze the text content to determine an appropriate category
     * Automatically move the file to the detected category if confidence is high (≥40%)
   * The system is robust to errors - if OCR fails for any reason, the file will remain in "Miscellaneous"

2. **Frontend Integration:**
   * **Upload UI:** Make the category selection optional in your file upload form
   * **Response Handling:**
     ```javascript
     // Example category dropdown in upload form
     const [selectedCategory, setSelectedCategory] = useState(null); // null is valid
     
     // Upload handler
     const handleUpload = async () => {
       const result = await uploadMobileFile(uri, 'document', filename, mimeType, selectedCategory);
       
       if (result.success) {
         if (result.data.auto_categorizing) {
           // Show message about pending categorization
           Toast.show({
             message: 'File uploaded successfully. Categorization in progress...',
             type: 'info',
             duration: 3000
           });
         } else {
           Toast.show({
             message: 'File uploaded successfully',
             type: 'success',
             duration: 2000
           });
         }
       }
     };
     ```

3. **Fetching Updated Category:**
   * The file's category may change after initial upload and OCR processing
   * To get the most current category, refresh your file list or fetch the specific file details
   * You can check the `pending_auto_categorization` flag in the file details to know if the process is still ongoing
   * Alternatively, you can poll the file details endpoint if you need to know when the category changes:
     ```javascript
     // Poll for category update (optional)
     const pollForCategoryUpdate = async (fileId) => {
       let attempts = 0;
       const maxAttempts = 5;
       const pollInterval = 5000; // 5 seconds
       
       const checkCategory = async () => {
         attempts++;
         try {
           const fileDetails = await fetchFileDetails(fileId);
           // If category is no longer 'Miscellaneous', categorization is complete
           // OR if pending_auto_categorization is false
           if (fileDetails.success && 
               ((fileDetails.data.category && 
                fileDetails.data.category.name !== 'Miscellaneous') || 
                !fileDetails.data.pending_auto_categorization)) {
             console.log('File categorized as:', fileDetails.data.category?.name || 'Miscellaneous');
             return fileDetails.data.category?.name || 'Miscellaneous';
           } else if (attempts >= maxAttempts) {
             console.log('Max polling attempts reached');
             return null;
           } else {
             // Continue polling
             setTimeout(checkCategory, pollInterval);
           }
         } catch (error) {
           console.error('Error polling category:', error);
           return null;
         }
       };
       
       return checkCategory();
     };
     ```

4. **Error Handling:**
   * If the OCR or categorization process fails for any reason, the file will remain in the "Miscellaneous" category
   * The `pending_auto_categorization` flag will be set to `false` after the process completes, whether successful or not
   * Your UI should handle files that remain in "Miscellaneous" gracefully - the user can manually move them if needed
   * Consider adding a method to manually trigger OCR and categorization if needed:
     ```javascript
     // Manually trigger OCR for a file
     const triggerOCR = async (fileId) => {
       try {
         const token = await AsyncStorage.getItem('accessToken');
         const response = await fetch(`${API_BASE_URL}/file_management/api/mobile/files/${fileId}/process-ocr/`, {
             method: 'POST',
             headers: {
                 'Authorization': `Bearer ${token}`,
                 'Content-Type': 'application/json'
             }
         });
     
         const data = await response.json();
         if (!response.ok) {
             throw new Error(data.error || `HTTP error! status: ${response.status}`);
         }
         
         // Show message about pending categorization
         Toast.show({
           message: 'OCR processing started. Categorization in progress...',
           type: 'info',
           duration: 3000
         });
         
         return data;
       } catch (error) {
         console.error('OCR Trigger Error:', error);
         Toast.show({
           message: 'Failed to start OCR process',
           type: 'error',
           duration: 3000
         });
         throw error;
       }
     };
     ```

5. **Testing the Feature:**
   * Upload a document without selecting a category
   * Check that the file initially appears in "Miscellaneous"
   * After OCR completes, the file should move to the appropriate category based on content
   * Verify that the `pending_auto_categorization` flag is `false` after the process completes

## 4. Sparkle AI Integration (`screens/SparkleChat.js`)

The primary interaction point is the `/voice/api/process/` endpoint.

*   **Endpoint:** `POST /voice/api/process/`
*   **Authentication:** Requires `Authorization: Bearer <token>` header.
*   **Request Body:**
    *   If sending **text**:
        *   `Content-Type: application/json`
        *   `{ "text": "Your query", "include_audio": true/false, "conversation_id": "uuid-string-here" }`
    *   If sending **audio**:
        *   `Content-Type: multipart/form-data`
        *   `FormData` containing:
            *   `audio`: The audio file object (`{ uri, name, type }`) - Use `.m4a`/`audio/m4a` (iOS) or `.mp4`/`audio/mp4` (Android) if using AAC. Check backend compatibility or use WAV.
            *   `include_audio`: 'true' or 'false' (as string in FormData)
            *   `conversation_id`: The conversation UUID string for context tracking (optional for new conversations)
*   **Response Body (Standard Format):**
    ```json
    {
      "success": true | false,
      "data | error": { // If success: data, if failure: error string
        "prompt": "User's transcribed text or original text",
        "response": "Sparkle's text response to display",
        "audio_url": "Optional: Presigned S3 URL for TTS audio",
        "interaction_id": 123, // ID of the saved interaction
        "interaction_success": true | false, // Whether the underlying action (if any) succeeded
        "conversation_id": "uuid-string", // Use this for follow-up requests
        // --- Action Payload (ONLY for 'display_file') ---
        "action": {
            "type": "display_file",
            "payload": {
                 "success": true, // Indicates the file details were successfully retrieved
                 "fileName": "your_document.pdf",
                 "fileUrl": "https://your-s3-bucket...", // Presigned S3 URL
                 "fileType": "document",
                 "fileId": 45
            }
        }, // Or action: null if no specific action needed by frontend
        // --- file_details (alternative/redundant for display_file) ---
        "file_details": { // May mirror action.payload for display_file, or be null
            "success": true,
            "fileName": "your_document.pdf",
            "fileUrl": "https://your-s3-bucket...",
            // ... potentially other fields if needed in future
        } // Or file_details: null
      }
    }
    ```

### Conversation Memory & Context Management

The backend now intelligently maintains conversation context, especially for file references:

1. **Conversation ID Handling**:
   * When starting a new conversation, omit the `conversation_id` parameter
   * The first response will include a `conversation_id` field
   * Store this ID and include it in all subsequent requests in the same conversation
   * This ensures Sparkle remembers previous messages and file references

2. **Reference Resolution**: 
   * Sparkle can now understand contextual references like "this file", "it", etc.
   * When a user says "show this to me" after mentioning a file, Sparkle will remember which file

3. **Implementation in React Native**:
   ```javascript
   // In your SparkleChat component:
   const [currentConversationId, setCurrentConversationId] = useState(null);
   
   const sendApiRequest = useCallback(async (payload) => {
       setIsTyping(true);
       const token = await getAuthToken();
       if (!token) {
           console.error("No auth token found");
           addChatMessage('sparkle', 'Authentication error. Please log in again.');
           setIsTyping(false);
           return;
       }

       // If we have a conversation ID, add it to maintain context
       if (currentConversationId) {
           if (payload instanceof FormData) {
               payload.append('conversation_id', currentConversationId);
           } else {
               payload.conversation_id = currentConversationId;
           }
       }

       try {
           const response = await fetch(`${API_BASE_URL}/voice/api/process/`, {
               method: 'POST',
               headers: {
                   'Authorization': `Bearer ${token}`,
               },
               body: payload, // Can be FormData or JSON string
           });

           if (!response.ok) {
               // Error handling...
           }

           const result = await response.json();
           
           // Store conversation ID from response for future messages
           if (result.success && result.data && result.data.conversation_id) {
               setCurrentConversationId(result.data.conversation_id);
               console.log('[Sparkle] Using conversation ID:', result.data.conversation_id);
           }
           
           handleApiResponse(result);
       } catch (err) {
           console.error('API Send Error:', err);
           addChatMessage('sparkle', `Error processing request: ${err.message}`);
       } finally {
           setIsTyping(false);
       }
   }, [handleApiResponse, currentConversationId]);

   // In your "Start New Chat" function
   const startNewConversation = () => {
       setCurrentConversationId(null);
       setMessages([]); // Clear messages
       // Any other reset logic...
   };
   ```

4. **UI Considerations**:
   * Add a "New Chat" button to reset `currentConversationId` and clear message history
   * You might want to show conversation breaks or headers in the chat UI
   * Consider adding a visual indication when Sparkle is referencing a previous file

### Frontend Handling (`SparkleChat.js` - Key Logic)

1.  **Sending Requests:**
    *   Use the `handleTextSend` logic (sending JSON) for text input.
    *   Use the `handleStartRecord`/`handleStopRecord`/`sendAudio` logic (sending `FormData`) for voice input. Ensure correct file `type` is set (`audio/m4a` or `audio/mp4` for AAC, or adjust if using WAV). Pass `include_audio: 'true'` in FormData.
    *   Always include `conversation_id` if continuing a conversation (see above)

2.  **Handling Responses:**
    *   Check the outer `success` flag first. If false, display the `error` message.
    *   If `success` is true, access the `data` object.
    *   Display `data.response` in the chat.
    *   If `data.audio_url` exists, use `react-native-sound` to play it (ensure previous sound is stopped).
    *   **Crucially, check `data.action`:**
        ```javascript
        const handleApiResponse = useCallback(async (apiResult) => {
          // ... (previous checks) ...
          if (apiResult && apiResult.success && apiResult.data) {
            const data = apiResult.data;

            // Add text response to chat
            const sparkleMsg = { sender: 'sparkle', text: data.response };

            // Check for the specific 'display_file' action
            if (data.action?.type === 'display_file' && data.action?.payload?.success) {
              const payload = data.action.payload;
              // Prepare data for navigation, but DON'T navigate yet.
              // Add it to the message object so renderMessage can create the button.
              sparkleMsg.viewFile = {
                fileUrl: payload.fileUrl,
                fileName: payload.fileName,
                fileType: payload.fileType || payload.file_type || 'unknown'
              };
              console.log('[Sparkle] Action received: Display File -> ', sparkleMsg.viewFile);
            }
            // Optionally check data.file_details as a fallback if action structure changes
            else if (data.file_details?.success && data.file_details?.fileUrl){
                 sparkleMsg.viewFile = {
                    fileUrl: data.file_details.fileUrl,
                    fileName: data.file_details.fileName,
                    fileType: data.file_details.fileType || data.file_details.file_type || 'unknown'
                };
                 console.log('[Sparkle] Action received (via file_details): Display File -> ', sparkleMsg.viewFile);
            }

            addChatMessage('sparkle', sparkleMsg.text, sparkleMsg); // Pass the full object

            // Play audio if available
            if (data.audio_url) {
              playAudioResponse(data.audio_url);
            }
          } else {
            // ... (error handling) ...
          }
        }, [addChatMessage, playAudioResponse]); // Dependencies

        // In renderMessage function:
        const renderMessage = useCallback((item, index) => {
          // ... (other rendering logic) ...
          const isSparkle = item.sender === 'sparkle';

          return (
            <View key={/* unique key */} style={/* container styles */}>
               {/* ... Icon etc ... */}
              <View style={/* bubble styles */}>
                <Text style={/* text styles */}>{item.text}</Text>

                {/* Conditionally render the "View File" button */}
                {isSparkle && item.viewFile?.fileUrl && item.viewFile?.fileName && (
                  <TouchableOpacity
                    style={styles.viewBtn}
                    onPress={() => openViewer(item.viewFile.fileUrl, item.viewFile.fileName)}
                  >
                    <Text style={styles.viewText}>📄 View {item.viewFile.fileName}</Text>
                  </TouchableOpacity>
                )}
              </View>
            </View>
          );
        }, [openViewer]); // Dependency

        // Navigation function
        const openViewer = (fileUrl, fileName) => {
          if (fileUrl && fileName) {
            console.log(`[Navigation] Navigating to GoogleDocViewer for: ${fileName}`);
            // Ensure GoogleDocViewer can handle S3 presigned URLs
            navigation.navigate('GoogleDocViewer', { fileUrl, fileName });
          } else {
            console.error("Cannot open viewer: Missing URL or Filename");
            // Optionally show an alert to the user
          }
        };

        ```
    *   The `interaction_success` flag can be used subtly (e.g., changing icon color) but the primary feedback comes from Sparkle's *text response*, which is now guided by the backend function results.

### Recent Backend Improvements

The backend now includes the following improvements that impact React Native integration:

1. **Enhanced Error Handling**
   * The backend now has more robust error handling for OpenAI API calls
   * If the first OpenAI call succeeds but the second one fails, the system will construct a reasonable response instead of throwing an error
   * This ensures the frontend will always receive a valid response, even in unusual error conditions

2. **Improved Response Consistency**
   * The response structure is more consistent, with properly formatted JSON
   * The `action` and `file_details` fields now use consistent naming conventions
   * Frontend developers should still implement fallback checks as shown above

3. **Fallback Response Generation**
   * When errors occur, the system extracts relevant information from tool responses
   * This produces more helpful error messages when the AI is unable to generate a complete response
   * The frontend should always display the `response` text without needing special error handling

4. **Key Frontend Implementation Notes**
   * Always check both `action` and `file_details` as shown in the example above
   * Implement proper fallbacks for missing fields
   * Ensure the UI gracefully handles both successful responses and error states
   * Audio responses will still be provided when possible, even if some errors occur

By implementing these changes, React Native developers can ensure a smooth and reliable user experience, even in cases where backend processing encounters challenges.

## 5. Hub & Keeper APIs

Endpoints exist but detailed frontend integration depends on specific UI requirements:

*   **Cards:** `GET`, `POST`, `DELETE` `/file_management/api/cards/` and `/file_management/api/cards/<card_id>/`. Also `/extract_from_document/`.
*   **Subscriptions:** `GET`, `POST`, `DELETE` `/file_management/api/subscriptions/` and `/file_management/api/subscriptions/<sub_id>/`. Also `/extract_from_document/`.
*   **Notes/Voice Notes:** Likely managed via `UserFile` endpoints with `file_type` 'audio' or potentially a dedicated notes endpoint if more structure is needed later.

## 6. OCR Handling

*   OCR is primarily backend-triggered after upload for relevant file types.
*   The frontend *can* poll the status using `GET /file_management/api/mobile/files/<file_id>/` (which now includes `ocr_status`) or the dedicated `GET /file_management/ocr/result/<job_id>/` if the `job_id` was returned during upload (for PDFs).
*   However, for most user flows, Sparkle should handle OCR interactions (e.g., "summarize this PDF" will trigger OCR status checks internally if needed).

## 7. Settings APIs

*   **User Profile:** `GET`, `PATCH` `/auth/api/profile/` (Use the ViewSet's default detail route, typically `/auth/api/profile/me/` or similar if configured for the current user).
*   **OCR Preferences:** `GET`, `POST` `/file_management/api/mobile/ocr-preferences/`
    *   `GET` Response: `{ success: true, data: { preference: "all|selected|none", display: "..." } }`
    *   `POST` Body: `{ "preference": "all|selected|none" }`
    *   `POST` Response: `{ success: true, data: { message: "...", preference: "...", display: "..." } }`

## 8. Error Handling

*   Always check the `success` flag in the response.
*   If `success` is `false`, display the `error` message to the user.
*   Implement standard network error handling (timeouts, connectivity issues).
*   For authentication errors (401), attempt token refresh. If refresh fails, prompt the user to log in again.

## 9. Recently Implemented Fixes: Context & Memory Management

The backend has been updated to address several key issues with context management and file display:

### 1. Context/Memory Improvements

**Problem:** Previously, when asking Sparkle to "show this file" after mentioning a file, it would forget the context and ask "which file?" instead of showing the referenced file.

**Solution:** 
- Improved reference tracking using a dedicated `reference_context` dictionary stored with each interaction
- Enhanced extraction of file mentions from both user messages and Sparkle responses
- Expanded pattern matching to catch file references in various formats
- Added more pronouns and contextual references ("this", "that", "it", "the document", etc.)

These changes allow the assistant to maintain context between messages, understanding references to previously mentioned files.

### 2. File Display Functionality

**Problem:** The "show file" or "open file" functionality was inconsistent, sometimes failing to provide URLs for the frontend to display files.

**Solution:**
- Updated `get_file_details_for_display` to consistently return properly formatted URLs
- Ensured consistent field naming (`fileUrl`/`file_url`, `fileName`/`file_name`)
- Made sure both standard and frontend-specific keys are included in responses
- Added proper mapping between API response and frontend display data

### 3. NEW: Failproof File Handling System

To ensure files can **always** be opened reliably regardless of AI limitations, the backend now includes a direct file handler system:

#### Backend Components:
- **Direct File Handling**: A pattern matching system that bypasses LLM when high-confidence file open requests are detected
- **Dedicated API Endpoint**: A new `/voice_assistant/api/open-file/` endpoint for direct file access from the frontend
- **Improved Error Recovery**: Better file matching to find files even with partial or incomplete references

#### Frontend Integration:

1. **Add File Detection Logic**:
```javascript
// In your SparkleChat.js or similar file

// Add this file intent detection function
const detectFileOpenIntent = (userQuery) => {
  const fileOpenKeywords = ['open', 'file', 'link', 'show', 'display', 'access', 'give me'];
  const lowerQuery = userQuery.toLowerCase();
  
  // Check if the query contains file opening intent
  const hasOpenIntent = fileOpenKeywords.some(keyword => lowerQuery.includes(keyword));
  
  if (!hasOpenIntent) return null;
  
  // Try to extract potential filename
  const patterns = [
    /open (?:the )?(?:file )?([\w\s\-\_\.]+)(?:file| for me|\.|\?|$)/i,
    /give me (?:the )?(?:link to|access to|url for) ([\w\s\-\_\.]+)(?:file|\.|$)/i,
    /(?:show|display|view|access|get) (?:the )?(?:file )?([\w\s\-\_\.]+)(?:file| for me|\.|\?|$)/i,
    /(?:i need|i want) (?:the )?(?:link to|to open|to see|to access) ([\w\s\-\_\.]+)(?:file|\.|$)/i
  ];
  
  for (const pattern of patterns) {
    const match = lowerQuery.match(pattern);
    if (match && match[1] && match[1].trim().length >= 3) {
      return match[1].trim();
    }
  }
  
  // Fallback to simpler pattern
  const simpleMatch = lowerQuery.match(/(?:open|link|show|display|access|file|view).*?([\w\s\-\_\.]+)/i);
  if (simpleMatch && simpleMatch[1] && simpleMatch[1].trim().length >= 3) {
    return simpleMatch[1].trim();
  }
  
  return null;
};
```

2. **Implement Fallback File Opening**:
```javascript
// Add this function to handle fallback file opening
const handleDirectFileOpen = async (fileReference) => {
  if (!fileReference) return false;
  
  setIsLoading(true); // Show loading indicator
  
  try {
    const token = await AsyncStorage.getItem('accessToken');
    
    // Call the special direct file opening endpoint
    const response = await fetch(`${API_BASE_URL}/voice_assistant/api/open-file/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ file_reference: fileReference })
    });
    
    const data = await response.json();
    
    if (data.success && data.file_data && data.file_data.url) {
      // Successfully got file URL - open it
      const fileInfo = {
        fileUrl: data.file_data.url,
        fileName: data.file_data.name,
        fileType: data.file_data.type
      };
      
      // Add a special message to the chat
      addChatMessage('sparkle', `Here's the file "${data.file_data.name}" you requested.`, {
        viewFile: fileInfo
      });
      
      // Optionally auto-open the file
      openViewer(fileInfo.fileUrl, fileInfo.fileName);
      
      return true; // Success!
    } else if (!data.success && data.fallback_files && data.fallback_files.length > 0) {
      // Couldn't find exact file but have suggestions
      const suggestions = data.fallback_files.map(f => f.name).join(', ');
      addChatMessage('sparkle', `I couldn't find that exact file. Did you mean one of these? ${suggestions}`);
      
      // Optionally show file selector
      showFileSuggestions(data.fallback_files);
      
      return true; // Handled with fallbacks
    }
    
    return false; // Not handled
  } catch (error) {
    console.error('Direct file open error:', error);
    return false;
  } finally {
    setIsLoading(false);
  }
};

// Optional helper to display file suggestions
const showFileSuggestions = (files) => {
  // Show a modal or inline UI with file options
  setFileSuggestions(files);
  setShowSuggestionsModal(true);
};

// File suggestion selection handler
const handleSuggestionSelected = async (file) => {
  setShowSuggestionsModal(false);
  
  // Get URL and open file
  try {
    const token = await AsyncStorage.getItem('accessToken');
    const response = await fetch(`${API_BASE_URL}/voice_assistant/api/open-file/`, {
      method: 'POST',
      headers: {
        'Authorization': `Bearer ${token}`,
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({ file_reference: file.id.toString() })
    });
    
    const data = await response.json();
    
    if (data.success && data.file_data && data.file_data.url) {
      const fileInfo = {
        fileUrl: data.file_data.url,
        fileName: data.file_data.name,
        fileType: data.file_data.type
      };
      
      addChatMessage('sparkle', `Opening "${data.file_data.name}" for you.`, {
        viewFile: fileInfo
      });
      
      openViewer(fileInfo.fileUrl, fileInfo.fileName);
    }
  } catch (error) {
    console.error('Error opening suggested file:', error);
  }
};
```

3. **Add File Suggestions Modal**:
```jsx
// File suggestions modal component
const FileSuggestionsModal = ({ visible, files, onSelect, onClose }) => {
  return (
    <Modal
      visible={visible}
      transparent={true}
      animationType="slide"
      onRequestClose={onClose}
    >
      <View style={styles.modalContainer}>
        <View style={styles.modalContent}>
          <Text style={styles.modalTitle}>Did you mean one of these files?</Text>
          
          <FlatList
            data={files}
            keyExtractor={(item) => item.id.toString()}
            renderItem={({ item }) => (
              <TouchableOpacity
                style={styles.fileItem}
                onPress={() => onSelect(item)}
              >
                <Text style={styles.fileIcon}>
                  {item.type === 'document' ? '📄' : 
                   item.type === 'image' ? '🖼️' : '📁'}
                </Text>
                <Text style={styles.fileName}>{item.name}</Text>
              </TouchableOpacity>
            )}
          />
          
          <TouchableOpacity
            style={styles.closeButton}
            onPress={onClose}
          >
            <Text style={styles.closeButtonText}>Close</Text>
          </TouchableOpacity>
        </View>
      </View>
    </Modal>
  );
};

// Add these to your component state
const [fileSuggestions, setFileSuggestions] = useState([]);
const [showSuggestionsModal, setShowSuggestionsModal] = useState(false);

// Add this to your render function
<FileSuggestionsModal
  visible={showSuggestionsModal}
  files={fileSuggestions}
  onSelect={handleSuggestionSelected}
  onClose={() => setShowSuggestionsModal(false)}
/>
```

4. **Integrate with Message Sending**:
```javascript
// Update your existing sendMessage function
const sendMessage = async (messageText) => {
  // Add message to chat
  addChatMessage('user', messageText);
  
  // Check if this is a file open request 
  const potentialFileName = detectFileOpenIntent(messageText);
  
  if (potentialFileName) {
    console.log(`[File Detection] Potential file request detected: "${potentialFileName}"`);
    
    // Try the direct method first
    const handled = await handleDirectFileOpen(potentialFileName);
    
    if (handled) {
      console.log('[File Detection] Request handled by direct file open system');
      return; // Skip standard API call if handled
    }
    
    // If we get here, direct method didn't work, continue with standard API
    console.log('[File Detection] Falling back to standard API');
  }
  
  // Continue with your existing API call
  const payload = {
    text: messageText,
    include_audio: includeAudio,
    conversation_id: currentConversationId
  };
  
  sendApiRequest(payload);
};
```

5. **Add Fallback for API Responses**:
```javascript 
// Update your response handling
const handleApiResponse = useCallback(async (apiResult) => {
  if (apiResult && apiResult.success && apiResult.data) {
    const data = apiResult.data;
    
    // Extract prompt for potential fallback use
    const userPrompt = data.prompt;
    
    // Add text response to chat
    const sparkleMsg = { sender: 'sparkle', text: data.response };

    // Check for the specific 'display_file' action
    if (data.action?.type === 'display_file' && data.action?.payload?.success) {
      const payload = data.action.payload;
      sparkleMsg.viewFile = {
        fileUrl: payload.fileUrl,
        fileName: payload.fileName,
        fileType: payload.fileType || payload.file_type || 'unknown'
      };
      console.log('[Sparkle] Action received: Display File -> ', sparkleMsg.viewFile);
    }
    // Optionally check data.file_details as a fallback
    else if (data.file_details?.success && data.file_details?.fileUrl){
      sparkleMsg.viewFile = {
        fileUrl: data.file_details.fileUrl,
        fileName: data.file_details.fileName,
        fileType: data.file_details.fileType || data.file_details.file_type || 'unknown'
      };
      console.log('[Sparkle] Action received (via file_details): Display File -> ', sparkleMsg.viewFile);
    }
    // NEW: Additional fallback if response suggests a file but has no URL
    else if (
      userPrompt && 
      (userPrompt.toLowerCase().includes('open') || 
       userPrompt.toLowerCase().includes('show') || 
       userPrompt.toLowerCase().includes('link')) && 
      !sparkleMsg.viewFile
    ) {
      // Response text mentions a file but no URL was provided
      const fileNameMatches = data.response.match(/file (?:called |named )?"([^"]+)"/i) || 
                              data.response.match(/file:? ([^\n.,]+)/i) ||
                              data.response.match(/"([^"]+\.(?:pdf|docx?|xlsx?|jpe?g|png))"/i);
      
      if (fileNameMatches && fileNameMatches[1]) {
        const potentialFileName = fileNameMatches[1].trim();
        console.log(`[Fallback] Detected file "${potentialFileName}" in response but no URL provided`);
        
        // Try to get the file directly
        const handled = await handleDirectFileOpen(potentialFileName);
        
        if (handled) {
          console.log('[Fallback] Successfully retrieved file URL via fallback');
          return; // Skip adding the original message if we handled it with fallback
        }
      }
    }

    addChatMessage('sparkle', sparkleMsg.text, sparkleMsg);

    // Play audio if available
    if (data.audio_url) {
      playAudioResponse(data.audio_url);
    }
  } else {
    // Error handling
    console.error('API Error Response:', apiResult);
    addChatMessage('sparkle', 'Sorry, I encountered an error processing your request.');
  }
}, [addChatMessage, playAudioResponse, handleDirectFileOpen]);
```

6. **Add Required Styles**:
```javascript
const styles = StyleSheet.create({
  // ...your existing styles,
  
  // Modal styles
  modalContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'rgba(0, 0, 0, 0.5)',
  },
  modalContent: {
    width: '80%',
    backgroundColor: 'white',
    borderRadius: 10,
    padding: 20,
    maxHeight: '70%',
  },
  modalTitle: {
    fontSize: 18,
    fontWeight: 'bold',
    marginBottom: 15,
    textAlign: 'center',
  },
  fileItem: {
    flexDirection: 'row',
    alignItems: 'center',
    padding: 12,
    borderBottomWidth: 1,
    borderBottomColor: '#f0f0f0',
  },
  fileIcon: {
    fontSize: 22,
    marginRight: 10,
  },
  fileName: {
    fontSize: 16,
    flex: 1,
  },
  closeButton: {
    marginTop: 15,
    alignSelf: 'center',
    paddingVertical: 8,
    paddingHorizontal: 20,
    backgroundColor: '#f0f0f0',
    borderRadius: 20,
  },
  closeButtonText: {
    fontSize: 16,
    color: '#333',
  },
  
  // Improved file button
  fileButton: {
    marginTop: 10,
    backgroundColor: '#f0f8ff',
    borderRadius: 8,
    padding: 12,
    borderWidth: 1,
    borderColor: '#ddeeff',
  },
  fileButtonContent: {
    flexDirection: 'row',
    alignItems: 'center',
  },
  fileDetails: {
    flex: 1,
    marginLeft: 10,
  },
  fileName: {
    fontSize: 16,
    fontWeight: '500',
    color: '#333',
  },
  viewText: {
    fontSize: 14,
    color: '#4a86e8',
    marginTop: 4,
  },
});
```

### 4. Integration Testing

To verify that the failproof file handling system is working properly:

1. **Basic Testing**:
   - Ask Sparkle about a file that doesn't exist - the AI should suggest similar files
   - Tell Sparkle to open a file that does exist - both the standard flow and the direct handler should work
   - Try complex names and references that might confuse the AI

2. **Edge Case Testing**:
   - Test with partial file names
   - Try file names with special characters
   - Test what happens when two files have very similar names

3. **Failure Recovery**:
   - If a file doesn't exist, check that suggestions appear correctly
   - When a URL is incorrect or missing, verify the fallback retrieves a working URL
   - Test context handling between messages for file references

### 5. Benefits of the New System

This failproof approach provides several advantages:

- **Reduced Dependence on LLM**: Even when the AI responds incorrectly, files can still be opened
- **Better User Experience**: Files consistently open when requested, even with vague references
- **Increased Reliability**: Multiple layers of fallbacks ensure the critical file viewing feature works
- **Improved Error Handling**: When files can't be found, users get helpful suggestions instead of errors
- **Frontend Control**: The React Native app can now take a more active role in handling file operations

By implementing all of these components, your app will have a robust, multi-layered approach to file handling that works even when the AI assistant's responses are less than perfect.

### 3. Testing Recommendations

When testing these improvements:

1. Start a new conversation
2. Ask about a file (e.g., "Do I have a file called Frontend Plan?")
3. Follow up with "show this to me" or "open it"
4. Verify that Sparkle correctly opens the file without asking "which file?"

If issues persist:
- Check network requests to ensure `conversation_id` is being passed
- Verify the app is properly updating `currentConversationId` from responses
- Test with explicit file names if contextual references fail
- Check console logs for any file URL or context-related errors

### 4. Key Changes for Frontend Integration

1. **Maintain Conversation ID** - Store and reuse the `conversation_id` for continuity
2. **Properly Handle File URLs** - Don't cache URLs; they expire after 1-3 hours
3. **Improve Error Handling** - Check both `success` flags and file URL existence
4. **Add New Chat Button** - For resetting conversation context
5. **Enhanced File Display** - Implement the improved file button with better UX

These improvements should create a more natural, conversational experience with Sparkle, especially around file references and display functionality.

## 10. Conclusion

This guide covers the primary integration points between the React Native frontend and the enhanced Django backend. Pay close attention to the Sparkle API response structure, especially the `action` payload for triggering file views, and ensure secure handling of authentication tokens. The backend now provides more descriptive text responses based on function call success/failure, reducing the need for complex status interpretation on the frontend. Remember to implement the secure storage of card details on the backend as the top priority.

### Best Practices for File References & Context in React Native

The improved backend context handling makes working with files more intuitive, but requires some considerations in the React Native app:

1. **Testing Context-Aware Commands**: 
   * The system now understands contextual references like "show this file" after mentioning a file
   * Test these flows carefully - e.g., ask Sparkle about a file, then say "open it" or "show me this"
   * Make sure your message history UI makes it clear which file is being discussed

2. **Context Debugging**:
   ```javascript
   // Add this to help debug context issues
   const debugContext = async () => {
     try {
       const token = await getAuthToken();
       const response = await fetch(`${API_BASE_URL}/voice/api/assistant/debug-context/`, {
         method: 'POST',
         headers: {
           'Authorization': `Bearer ${token}`,
           'Content-Type': 'application/json'
         },
         body: JSON.stringify({ conversation_id: currentConversationId })
       });
       
       const result = await response.json();
       console.log('[DEBUG] Context:', result.data?.context);
       // Optional: Display this debug info in a developer mode screen
     } catch (err) {
       console.error('Context debug error:', err);
     }
   };
   ```

3. **Handling File URLs Properly**:
   * File URLs from the backend are temporary S3 presigned URLs
   * They typically expire after 1-3 hours
   * Don't cache these URLs long-term; instead:
   
   ```javascript
   // Best practice for file viewing
   const viewFileById = async (fileId) => {
     try {
       const token = await getAuthToken();
       // Always get a fresh URL when viewing files
       const response = await fetch(`${API_BASE_URL}/file_management/api/mobile/files/${fileId}/view/`, {
         method: 'GET',
         headers: {
           'Authorization': `Bearer ${token}`
         }
       });
       
       const result = await response.json();
       if (result.success && result.data?.fileUrl) {
         navigation.navigate('GoogleDocViewer', {
           fileUrl: result.data.fileUrl,
           fileName: result.data.fileName
         });
       } else {
         Alert.alert('Error', 'Could not retrieve file URL');
       }
     } catch (err) {
       console.error('File view error:', err);
       Alert.alert('Error', 'Failed to load file');
     }
   };
   ```

4. **Improved File Display Button**:
   ```jsx
   // Enhanced file button with better UX
   const FileButton = ({ file, onPress }) => {
     // Determine icon based on fileType
     const getFileIcon = (fileType) => {
       const type = fileType?.toLowerCase() || '';
       if (type.includes('pdf')) return '📄';
       if (type.includes('image') || type.includes('jpg') || type.includes('png')) return '🖼️';
       if (type.includes('doc')) return '📝';
       if (type.includes('spreadsheet') || type.includes('xls')) return '📊';
       return '📁';
     };
     
     return (
       <TouchableOpacity
         style={styles.fileButton}
         onPress={onPress}
         activeOpacity={0.7}
       >
         <View style={styles.fileButtonContent}>
           <Text style={styles.fileIcon}>{getFileIcon(file.fileType)}</Text>
           <View style={styles.fileDetails}>
             <Text style={styles.fileName} numberOfLines={1} ellipsizeMode="middle">
               {file.fileName}
             </Text>
             <Text style={styles.viewText}>View File</Text>
           </View>
         </View>
       </TouchableOpacity>
     );
   };
   
   // In your message renderer:
   {isSparkle && item.viewFile?.fileUrl && (
     <FileButton 
       file={item.viewFile} 
       onPress={() => openViewer(item.viewFile.fileUrl, item.viewFile.fileName)}
     />
   )}
   ```

5. **Conversation Management UI**:
   ```jsx
   // Add a new chat button in your header
   const Header = () => (
     <View style={styles.header}>
       <Text style={styles.headerTitle}>Sparkle Assistant</Text>
       <TouchableOpacity
         style={styles.newChatButton}
         onPress={startNewConversation}
       >
         <Text style={styles.newChatButtonText}>New Chat</Text>
       </TouchableOpacity>
     </View>
   );
   
   // You might also want to add conversation history management
   const ConversationHistoryScreen = () => {
     const [conversations, setConversations] = useState([]);
     
     // Fetch conversation history on mount
     useEffect(() => {
       fetchConversationHistory();
     }, []);
     
     const fetchConversationHistory = async () => {
       try {
         const token = await getAuthToken();
         const response = await fetch(`${API_BASE_URL}/voice/api/assistant/conversations/`, {
           method: 'GET',
           headers: {
             'Authorization': `Bearer ${token}`
           }
         });
         
         const result = await response.json();
         if (result.success) {
           setConversations(result.data.conversations);
         }
       } catch (err) {
         console.error('Conversation history error:', err);
       }
     };
     
     // Render conversation list...
   };
   ```

---