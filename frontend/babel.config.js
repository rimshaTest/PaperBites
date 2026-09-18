module.exports = function (api) {
  api.cache(true);
  return {
    presets: ['babel-preset-expo'],
    // Required by react-native-reanimated (used for the drag-to-expand paper card).
    // Must be listed last.
    plugins: ['react-native-worklets/plugin'],
  };
};
