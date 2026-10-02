import React, { useEffect, useMemo, useRef } from 'react';
import { View, Image, StyleSheet, useWindowDimensions } from 'react-native';
import { useVideoPlayer, VideoView } from 'expo-video';
import { useTheme } from '../hooks/useTheme';

const PORTRAIT_VIDEO = require('../assets/splash-video.mp4');
const LANDSCAPE_VIDEO = require('../assets/splash-video-landscape.mp4');
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
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);
  const finishedRef = useRef(false);
  // Phones (portrait) get the tall cut; laptops/tablets (landscape) get the wide one. Picked once
  // at mount - the intro is short, so a rotation mid-playback isn't worth swapping sources for.
  const { width, height } = useWindowDimensions();
  const isLandscape = useRef(width > height).current;
  const videoSource = isLandscape ? LANDSCAPE_VIDEO : PORTRAIT_VIDEO;

  const finish = () => {
    if (finishedRef.current) return;
    finishedRef.current = true;
    onFinish();
  };

  const player = useVideoPlayer(videoSource, (p) => {
    p.loop = false;
    p.play();
  });

  useEffect(() => {
    const endSubscription = player.addListener('playToEnd', finish);
    const statusSubscription = player.addListener('statusChange', (event) => {
      if (event.status === 'error') {
        console.warn('Intro video failed to play:', event.error?.message ?? event.error);
        finish();
      }
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
      {/* The poster is only a portrait still, so it's skipped on wide screens rather than stretched */}
      {!isLandscape && (
        <Image source={POSTER_SOURCE} style={StyleSheet.absoluteFill} resizeMode="stretch" />
      )}
      {/* Explicit pixel size (not flex) so the web player can't shrink to the video's own aspect ratio */}
      <VideoView
        player={player}
        style={{ position: 'absolute', top: 0, left: 0, width, height }}
        contentFit="fill"
        nativeControls={false}
      />
    </View>
  );
}

const createStyles = (theme) => StyleSheet.create({
  container: {
    ...StyleSheet.absoluteFillObject,
    backgroundColor: theme.background,
    zIndex: 999,
    elevation: 999,
  },
});
