import React, { useEffect, useRef } from 'react';
import { View, Image, StyleSheet } from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';
import theme from '../constants/theme';

const VIDEO_SOURCE = require('../assets/splash-video.mp4');
const POSTER_SOURCE = require('../assets/splash-static.png');

// Safety net: if the video never fires an end/error event (a corrupt file, a platform quirk),
// don't leave the user staring at the intro forever - move on after this long regardless.
const MAX_INTRO_MS = 6000;

/**
 * Full-screen logo intro, played once on cold app start (see app/_layout.tsx) before the app's
 * normal content (already mounted underneath) becomes visible. Not a route - just an overlay
 * that unmounts itself via onFinish, so there's no navigation history entry to back out of.
 */
export default function IntroVideo({ onFinish }) {
  const finishedRef = useRef(false);

  const finish = () => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    onFinish();
  };

  const player = useVideoPlayer(VIDEO_SOURCE, (p) => {
    p.loop = false;
    p.play();
  });

  useEffect(() => {
    const endSubscription = player.addListener('playToEnd', finish);
    const statusSubscription = player.addListener('statusChange', (event) => {
      if (event.status === 'error') finish();
    });
    const timeout = setTimeout(finish, MAX_INTRO_MS);

    return () => {
      endSubscription.remove();
      statusSubscription.remove();
      clearTimeout(timeout);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [player]);

  return (
    <View style={styles.container}>
      <Image source={POSTER_SOURCE} style={StyleSheet.absoluteFill} resizeMode="contain" />
      <VideoView player={player} style={styles.video} contentFit="contain" nativeControls={false} />
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: theme.background,
    zIndex: 999,
    elevation: 999,
  },
  video: {
    flex: 1,
  },
});
