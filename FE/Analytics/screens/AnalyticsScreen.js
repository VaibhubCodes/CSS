import React, { useState, useEffect } from 'react';
import { View, ScrollView, Text, ActivityIndicator, StyleSheet, Button } from 'react-native';
import { getStorageAnalytics } from '../services/analyticsService';
import StorageDonutChart from '../components/StorageDonutChart';
import MonthlyBarChart from '../components/MonthlyBarChart';
import { Picker } from '@react-native-picker/picker'; // npm install @react-native-picker/picker

const AnalyticsScreen = () => {
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [analyticsData, setAnalyticsData] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);

  const fetchData = async () => {
    try {
      setLoading(true);
      setError(null);
      const data = await getStorageAnalytics();
      setAnalyticsData(data);
      // Set the default category for the bar chart
      if (data.monthly_trends && Object.keys(data.monthly_trends).length > 0) {
        setSelectedCategory(Object.keys(data.monthly_trends)[0]);
      }
    } catch (e) {
      setError('Failed to load analytics data.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchData();
  }, []);

  if (loading) {
    return <ActivityIndicator size="large" style={styles.center} />;
  }

  if (error) {
    return (
      <View style={styles.center}>
        <Text style={styles.errorText}>{error}</Text>
        <Button title="Retry" onPress={fetchData} />
      </View>
    );
  }

  if (!analyticsData) {
    return <Text style={styles.center}>No data available.</Text>;
  }

  const { storage_overview, storage_breakdown, monthly_trends } = analyticsData;
  const trendCategories = Object.keys(monthly_trends);

  return (
    <ScrollView style={styles.container}>
      <Text style={styles.header}>Storage Analytics</Text>

      {/* Storage Overview Donut Chart */}
      <StorageDonutChart overview={storage_overview} breakdown={storage_breakdown} />
      
      {/* Buttons from UI */}
      <View style={styles.buttonContainer}>
          <Button title="View Less" onPress={() => {}} />
          <Button title="Manage Storage" onPress={() => {}} />
      </View>

      <View style={styles.trendsContainer}>
        <Text style={styles.trendsHeader}>Monthly Trends</Text>

        {/* Category Picker for Bar Charts */}
        {trendCategories.length > 0 && (
          <View style={styles.pickerContainer}>
            <Picker
              selectedValue={selectedCategory}
              onValueChange={(itemValue) => setSelectedCategory(itemValue)}>
              {trendCategories.map(cat => (
                <Picker.Item key={cat} label={cat} value={cat} />
              ))}
            </Picker>
          </View>
        )}
        
        {/* Render the selected bar chart */}
        {selectedCategory && monthly_trends[selectedCategory] && (
            <MonthlyBarChart 
                categoryName={selectedCategory}
                data={monthly_trends[selectedCategory]}
            />
        )}
      </View>
    </ScrollView>
  );
};

const styles = StyleSheet.create({
  container: { flex: 1, backgroundColor: '#f0f2f5', },
  center: { flex: 1, justifyContent: 'center', alignItems: 'center', },
  header: { fontSize: 24, fontWeight: 'bold', padding: 16, color: '#1e3a8a', },
  errorText: { color: 'red', marginBottom: 10, },
  trendsContainer: { paddingHorizontal: 16, marginTop: 20 },
  trendsHeader: { fontSize: 20, fontWeight: 'bold', marginBottom: 10, color: '#334155' },
  pickerContainer: { borderWidth: 1, borderColor: '#cbd5e1', borderRadius: 8, backgroundColor: '#fff', marginVertical: 10, },
  buttonContainer: {
    flexDirection: 'row',
    justifyContent: 'space-around',
    marginVertical: 10,
    paddingHorizontal: 16,
  }
});

export default AnalyticsScreen;