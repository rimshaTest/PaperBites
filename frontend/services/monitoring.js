/**
 * Crash/error reporting - currently just funnels everything through console.error with a tag,
 * so nothing is silently swallowed. This is the single choke point to wire up a real crash
 * reporter (e.g. @sentry/react-native) later without touching every call site: replace the body
 * of reportError() once a DSN/project exists, and every caller below (the global JS error
 * handler and the root ErrorBoundary) starts reporting for real with no other changes needed.
 */
export const reportError = (error, context) => {
  console.error('[PaperBites crash]', context ? `(${context})` : '', error);
};

/**
 * Catches JS errors that occur outside of React's render (event handlers, timers, promise
 * executors) - React's own error boundaries only catch render-phase errors, so without this an
 * error thrown from, say, a button's onPress would only show up as a console warning and
 * otherwise vanish. Call once at app startup (see app/_layout.tsx).
 */
export const installGlobalErrorHandler = () => {
  if (typeof global === 'undefined' || !global.ErrorUtils) {
    return;
  }
  const previousHandler = global.ErrorUtils.getGlobalHandler();
  global.ErrorUtils.setGlobalHandler((error, isFatal) => {
    reportError(error, isFatal ? 'fatal' : 'non-fatal');
    if (previousHandler) {
      previousHandler(error, isFatal);
    }
  });
};
