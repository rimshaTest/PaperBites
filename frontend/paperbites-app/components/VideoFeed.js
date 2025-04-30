import React, { useState, useRef } from 'react';
import { 
  View, 
  FlatList, 
  Dimensions, 
  StyleSheet 
} from 'react-native';
import VideoPlayer from './VideoPlayer';
import VideoInfo from './VideoInfo';

const { width, height } = Dimensions.get('window');

const VideoFeed = ({ videos }) => {
  const [activeVideoIndex, setActiveVideoIndex] = useState(0);
  const flatListRef = useRef(null);

  const viewabilityConfig = {
    itemVisiblePercentThreshold: 50,
  };

  const onViewableItemsChanged = useRef(({ viewableItems }) => {
    if (viewableItems.length > 0) {
      setActiveVideoIndex(viewableItems[0].index);
    }
  }).current;

  const renderItem = ({ item, index }) => {
    const isActive = index === activeVideoIndex;
    
    return (
      <View style={styles.videoContainer}>
        <VideoPlayer 
          uri={item.videoUrl} 
          isActive={isActive} 
        />
        <VideoInfo 
          title={item.title}
          summary={item.summary}
          keywords={item.keywords}
          doi={item.doi}
          isActive={isActive}
        />
      </View>
    );
  };

  return (
    <FlatList
      ref={flatListRef}
      data={videos}
      renderItem={renderItem}
      keyExtractor={(item) => item.id}
      pagingEnabled
      showsVerticalScrollIndicator={false}
      snapToInterval={height}
      snapToAlignment="start"
      decelerationRate="fast"
      viewabilityConfig={viewabilityConfig}
      onViewableItemsChanged={onViewableItemsChanged}
      initialNumToRender={2}
      maxToRenderPerBatch={3}
      windowSize={5}
      removeClippedSubviews={true}
      vertical
    />
  );
};

const styles = StyleSheet.create({
  videoContainer: {
    width,
    height,
    backgroundColor: '#000',
  },
});

export default VideoFeed;