/**
 * Play an expo-audio player, tolerating the case where it hasn't finished loading its source
 * yet. useAudioPlayer(source) loads the file asynchronously in the background after the hook
 * mounts; calling .play() before that finishes is a silent no-op rather than something that
 * queues up - which is why the very first swipe/bookmark right after the app opens often played
 * no sound at all, while every later one (once the player had since finished loading) worked
 * fine. If the player isn't loaded yet, this waits for its one "loaded" status update and plays
 * then instead of dropping the sound.
 */
export const playWhenReady = (player) => {
  if (!player) return;

  if (player.isLoaded) {
    player.seekTo(0);
    player.play();
    return;
  }

  const subscription = player.addListener('playbackStatusUpdate', (status) => {
    if (status.isLoaded) {
      subscription.remove();
      player.seekTo(0);
      player.play();
    }
  });
};
