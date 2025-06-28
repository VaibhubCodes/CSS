import React, { createContext, useState, useContext, useCallback, useEffect } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';

const MASTER_VALID_UNTIL_KEY = 'masterPasswordValidUntil';

const MasterPasswordContext = createContext({
  isMasterPasswordVerified: false,
  verifyMasterPasswordSession: async () => false,
  setMasterPasswordSession: async (validUntilTimestamp) => {},
  clearMasterPasswordSession: async () => {},
  isLoading: true,
});

export const useMasterPassword = () => useContext(MasterPasswordContext);

export const MasterPasswordProvider = ({ children }) => {
  const [isVerified, setIsVerified] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const checkSessionValidity = useCallback(async () => {
    setIsLoading(true);
    try {
      const validUntil = await AsyncStorage.getItem(MASTER_VALID_UNTIL_KEY);
      if (validUntil && Date.now() < Number(validUntil)) {
        setIsVerified(true);
      } else {
        setIsVerified(false);
        await AsyncStorage.removeItem(MASTER_VALID_UNTIL_KEY); // Clean up expired
      }
    } catch (e) {
      console.error("Failed to check master password session:", e);
      setIsVerified(false);
    } finally {
      setIsLoading(false);
    }
  }, []);

  useEffect(() => {
    checkSessionValidity();
  }, [checkSessionValidity]);

  const verifyMasterPasswordSession = useCallback(async () => {
    // This function mainly re-checks AsyncStorage, actual API call is in VerifyScreen
    await checkSessionValidity();
    return isVerified; // Return the current state after check
  }, [checkSessionValidity, isVerified]);

  const setMasterPasswordSession = async (validUntilTimestamp) => {
    try {
      await AsyncStorage.setItem(MASTER_VALID_UNTIL_KEY, String(validUntilTimestamp));
      setIsVerified(true);
      console.log("Master password session set, valid until:", new Date(validUntilTimestamp));
    } catch (e) {
      console.error("Failed to set master password session:", e);
    }
  };

  const clearMasterPasswordSession = async () => {
    try {
      await AsyncStorage.removeItem(MASTER_VALID_UNTIL_KEY);
      setIsVerified(false);
      console.log("Master password session cleared.");
    } catch (e) {
      console.error("Failed to clear master password session:", e);
    }
  };

  return (
    <MasterPasswordContext.Provider
      value={{
        isMasterPasswordVerified: isVerified,
        verifyMasterPasswordSession,
        setMasterPasswordSession,
        clearMasterPasswordSession,
        isLoadingMasterPasswordContext: isLoading,
      }}
    >
      {children}
    </MasterPasswordContext.Provider>
  );
};