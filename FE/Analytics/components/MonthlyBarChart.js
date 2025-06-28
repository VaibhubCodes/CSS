import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Rect, G, Text as SvgText } from 'react-native-svg';

const CATEGORY_COLORS = {
  Images: { normal: '#c3b1e1', peak: '#8884d8' },
  Documents: { normal: '#ffd699', peak: '#ff8042' },
  Weblinks: { normal: '#ffe599', peak: '#ffc658' },
  Notes: { normal: '#ffb3c1', peak: '#ff82a9' },
  Coupons: { normal: '#b2dfdb', peak: '#82ca9d' },
  Rewards: { normal: '#a7d8de', peak: '#00c49f' },
  Uncategorized: { normal: '#dcdcdc', peak: '#a9a9a9' },
  Default: { normal: '#d3d3d3', peak: '#a3a3a3' }
};

const MonthlyBarChart = ({ categoryName, data }) => {
  if (!data || data.length === 0) {
    return null;
  }

  const chartHeight = 150;
  const chartWidth = 300;
  const barWidth = 30;
  const barGap = 20;
  const maxCount = Math.max(...data.map(item => item.count), 1); // Avoid division by zero
  const colors = CATEGORY_COLORS[categoryName] || CATEGORY_COLORS.Default;

  return (
    <View style={styles.container}>
      <Text style={styles.chartTitle}>{categoryName}</Text>
      <Svg height={chartHeight + 40} width={chartWidth}>
        <G>
          {data.map((item, index) => {
            const barHeight = (item.count / maxCount) * chartHeight;
            const x = index * (barWidth + barGap);
            const y = chartHeight - barHeight;
            return (
              <G key={item.month}>
                <Rect
                  x={x}
                  y={y}
                  width={barWidth}
                  height={barHeight}
                  fill={item.is_peak ? colors.peak : colors.normal}
                  rx="4"
                />
                <SvgText
                  x={x + barWidth / 2}
                  y={y - 5}
                  fill={item.is_peak ? colors.peak : '#333'}
                  fontSize="12"
                  textAnchor="middle">
                  {item.count}
                </SvgText>
                <SvgText
                  x={x + barWidth / 2}
                  y={chartHeight + 15}
                  fill={item.is_peak ? colors.peak : '#666'}
                  fontSize="12"
                  textAnchor="middle">
                  {item.month_short}
                </SvgText>
              </G>
            );
          })}
        </G>
      </Svg>
    </View>
  );
};

const styles = StyleSheet.create({
  container: {
    padding: 16,
    backgroundColor: '#fff',
    borderRadius: 12,
    marginVertical: 10,
    alignItems: 'center',
  },
  chartTitle: {
    fontSize: 16,
    fontWeight: '600',
    marginBottom: 16,
    color: '#333'
  },
});

export default MonthlyBarChart;