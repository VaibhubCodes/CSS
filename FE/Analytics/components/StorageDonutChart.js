import React from 'react';
import { View, Text, StyleSheet } from 'react-native';
import Svg, { Path, G, Text as SvgText } from 'react-native-svg';

// Pre-defined colors for consistency
const CATEGORY_COLORS = {
  Images: '#8884d8',
  Documents: '#ff8042',
  Weblinks: '#ffc658',
  Notes: '#ff82a9',
  Coupons: '#82ca9d',
  Rewards: '#00c49f',
  Uncategorized: '#a9a9a9',
  // Add other default categories here
};

const StorageDonutChart = ({ overview, breakdown }) => {
  if (!overview || !breakdown || breakdown.length === 0) {
    return <Text style={styles.noDataText}>Not enough data to display chart.</Text>;
  }

  const totalSize = overview.used > 0 ? overview.used : 1; // Avoid division by zero
  const radius = 80;
  const strokeWidth = 25;
  const innerRadius = radius - strokeWidth;
  const circumference = 2 * Math.PI * radius;
  
  let accumulatedAngle = 0;

  return (
    <View style={styles.container}>
      <Svg height="200" width="200" viewBox="-100 -100 200 200">
        <G rotation="-90">
          {breakdown.map((slice, index) => {
            const percentage = (slice.size / totalSize);
            const angle = percentage * 360;
            const color = CATEGORY_COLORS[slice.category] || '#cccccc';
            
            const arc = describeArc(0, 0, radius, accumulatedAngle, accumulatedAngle + angle);
            accumulatedAngle += angle;

            return <Path key={index} d={arc} stroke={color} strokeWidth={strokeWidth} fill="none" />;
          })}
        </G>
        <SvgText
            x="0"
            y="5"
            fill="#333"
            textAnchor="middle"
            alignmentBaseline="middle"
            fontSize="24"
            fontWeight="bold">
            {`${Math.round(overview.percentage_left)}%`}
        </SvgText>
        <SvgText
            x="0"
            y="25"
            fill="#666"
            textAnchor="middle"
            alignmentBaseline="middle"
            fontSize="14">
            Left
        </SvgText>
      </Svg>
      <View style={styles.legendContainer}>
        {breakdown.map((slice, index) => (
          <View key={index} style={styles.legendItem}>
            <View style={[styles.legendColor, { backgroundColor: CATEGORY_COLORS[slice.category] || '#cccccc' }]} />
            <Text style={styles.legendText}>{slice.category}</Text>
          </View>
        ))}
      </View>
    </View>
  );
};

// Helper function to create SVG arc paths
function describeArc(x, y, radius, startAngle, endAngle) {
  const start = polarToCartesian(x, y, radius, endAngle);
  const end = polarToCartesian(x, y, radius, startAngle);
  const largeArcFlag = endAngle - startAngle <= 180 ? "0" : "1";
  return `M ${start.x} ${start.y} A ${radius} ${radius} 0 ${largeArcFlag} 0 ${end.x} ${end.y}`;
}

function polarToCartesian(centerX, centerY, radius, angleInDegrees) {
  const angleInRadians = (angleInDegrees - 90) * Math.PI / 180.0;
  return {
    x: centerX + (radius * Math.cos(angleInRadians)),
    y: centerY + (radius * Math.sin(angleInRadians)),
  };
}

const styles = StyleSheet.create({
  container: { alignItems: 'center', padding: 16, backgroundColor: '#fff', borderRadius: 12, marginVertical: 10, },
  noDataText: { color: '#666', fontStyle: 'italic', },
  legendContainer: { flexDirection: 'row', flexWrap: 'wrap', justifyContent: 'center', marginTop: 16, },
  legendItem: { flexDirection: 'row', alignItems: 'center', margin: 5, },
  legendColor: { width: 12, height: 12, borderRadius: 6, marginRight: 6, },
  legendText: { fontSize: 12, color: '#444' },
});

export default StorageDonutChart;