// src/screens/password/PasswordDetailScreen.js
import React, { useContext } from 'react';
import { View, Text, StyleSheet } from 'react-native';
import { ThemeContext } from '../../context/ThemeContext';

const PasswordDetailScreen = ({ route }) => {
  const { theme } = useContext(ThemeContext);
  const { passwordId } = route.params;

  // In a real app, you'd fetch details for passwordId here
  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <Text style={[styles.title, { color: theme.textPrimary }]}>Password Detail</Text>
      <Text style={{color: theme.textSecondary}}>Details for ID: {passwordId}</Text>
      {/* Display password details here */}
    </View>
  );
};
const styles = StyleSheet.create({
  container: { flex: 1, padding: 20, justifyContent: 'center', alignItems: 'center' },
  title: { fontSize: 22, fontWeight: 'bold', marginBottom: 20 },
});
export default PasswordDetailScreen;