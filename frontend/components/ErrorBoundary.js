import React from 'react';
import { View, Text, TouchableOpacity, StyleSheet } from 'react-native';
import { reportError } from '../services/monitoring';
import theme from '../constants/theme';

/**
 * Root-level render-error catcher (see app/_layout.tsx). React error boundaries can only be
 * class components - there's no hook equivalent - so this one stays plain React rather than
 * following the rest of the app's function-component convention. Deliberately uses the static
 * light theme import instead of useTheme(): if the app crashed badly enough to reach this
 * fallback UI, the ThemeProvider it would need may not be mounted/reachable either, so this
 * screen intentionally doesn't depend on it.
 */
export default class ErrorBoundary extends React.Component {
  constructor(props) {
    super(props);
    this.state = { hasError: false };
  }

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    reportError(error, `render: ${info?.componentStack?.split('\n')[1]?.trim() || 'unknown'}`);
  }

  handleRetry = () => {
    this.setState({ hasError: false });
  };

  render() {
    if (this.state.hasError) {
      return (
        <View style={styles.container}>
          <Text style={styles.title}>Something went wrong</Text>
          <Text style={styles.subtitle}>Sorry about that - please try again.</Text>
          <TouchableOpacity style={styles.button} onPress={this.handleRetry}>
            <Text style={styles.buttonText}>Try Again</Text>
          </TouchableOpacity>
        </View>
      );
    }

    return this.props.children;
  }
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
    alignItems: 'center',
    justifyContent: 'center',
    padding: 24,
  },
  title: {
    fontFamily: theme.serif,
    fontSize: 20,
    fontWeight: 'bold',
    color: theme.text,
    marginBottom: 8,
  },
  subtitle: {
    fontSize: 14,
    color: theme.textMuted,
    marginBottom: 20,
    textAlign: 'center',
  },
  button: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 30,
  },
  buttonText: {
    color: theme.text,
    fontSize: 15,
    fontWeight: 'bold',
  },
});
