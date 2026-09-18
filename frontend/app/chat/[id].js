import React, { useState, useEffect, useRef } from 'react';
import {
  View,
  Text,
  FlatList,
  StyleSheet,
  TouchableOpacity,
  ActivityIndicator,
  TextInput,
  KeyboardAvoidingView,
  Platform,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchPaperById, chatAboutPaper } from '../../services/api';
import theme from '../../constants/theme';

// The backend chat endpoint is stateless (no server-side conversation memory) - each request
// resends the full message history alongside the new question, so it's kept here as plain state.
export default function PaperChatScreen() {
  const router = useRouter();
  const { id } = useLocalSearchParams();
  const [paper, setPaper] = useState(null);
  const [loadingPaper, setLoadingPaper] = useState(true);
  const [messages, setMessages] = useState([]); // [{role: 'user'|'assistant', content}]
  const [input, setInput] = useState('');
  const [sending, setSending] = useState(false);
  const listRef = useRef(null);

  useEffect(() => {
    const load = async () => {
      try {
        setLoadingPaper(true);
        const data = await fetchPaperById(id);
        setPaper(data);
      } catch (err) {
        console.error(err);
      } finally {
        setLoadingPaper(false);
      }
    };

    if (id) {
      load();
    }
  }, [id]);

  const send = async () => {
    const question = input.trim();
    if (!question || sending) {
      return;
    }

    const history = messages;
    const nextMessages = [...history, { role: 'user', content: question }];
    setMessages(nextMessages);
    setInput('');
    setSending(true);

    try {
      const answer = await chatAboutPaper(id, question, history);
      setMessages([...nextMessages, { role: 'assistant', content: answer }]);
    } catch (err) {
      setMessages([
        ...nextMessages,
        { role: 'assistant', content: "Sorry, I couldn't answer that just now. Please try again." },
      ]);
    } finally {
      setSending(false);
      setTimeout(() => listRef.current?.scrollToEnd({ animated: true }), 100);
    }
  };

  return (
    <SafeAreaView style={styles.container} edges={['top', 'bottom']}>
      <View style={styles.header}>
        <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
          <Ionicons name="arrow-back" size={22} color={theme.text} />
        </TouchableOpacity>
        <Text style={styles.headerTitle} numberOfLines={1}>
          {loadingPaper ? 'Loading...' : paper?.title ?? 'Chat about this paper'}
        </Text>
        <View style={{ width: 22 }} />
      </View>

      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === 'ios' ? 'padding' : undefined}
        keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
      >
        {loadingPaper ? (
          <ActivityIndicator style={{ marginTop: 40 }} size="large" color={theme.text} />
        ) : (
          <FlatList
            ref={listRef}
            data={messages}
            keyExtractor={(_, index) => String(index)}
            contentContainerStyle={styles.list}
            onContentSizeChange={() => listRef.current?.scrollToEnd({ animated: true })}
            ListHeaderComponent={
              <View style={styles.introBox}>
                <Text style={styles.introText}>
                  Ask anything about this paper - its methods, findings, or how it relates to
                  other work.
                </Text>
              </View>
            }
            renderItem={({ item }) => (
              <View
                style={[
                  styles.bubble,
                  item.role === 'user' ? styles.userBubble : styles.assistantBubble,
                ]}
              >
                <Text style={item.role === 'user' ? styles.userText : styles.assistantText}>
                  {item.content}
                </Text>
              </View>
            )}
          />
        )}

        {sending && (
          <View style={styles.typingRow}>
            <ActivityIndicator size="small" color={theme.textMuted} />
            <Text style={styles.typingText}>Thinking...</Text>
          </View>
        )}

        <View style={styles.inputRow}>
          <TextInput
            style={styles.input}
            value={input}
            onChangeText={setInput}
            placeholder="Ask a question..."
            placeholderTextColor={theme.textMuted}
            multiline
            editable={!loadingPaper}
          />
          <TouchableOpacity
            style={[styles.sendButton, (!input.trim() || sending) && styles.sendButtonDisabled]}
            onPress={send}
            disabled={!input.trim() || sending}
          >
            <Ionicons name="arrow-up" size={18} color={theme.surface} />
          </TouchableOpacity>
        </View>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  flex: {
    flex: 1,
  },
  header: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
    paddingHorizontal: 20,
    paddingTop: 10,
    paddingBottom: 16,
    borderBottomWidth: 1,
    borderBottomColor: theme.border,
  },
  backButton: {
    width: 22,
  },
  headerTitle: {
    flex: 1,
    fontFamily: theme.serif,
    fontSize: 15,
    fontWeight: 'bold',
    color: theme.text,
    textAlign: 'center',
    marginHorizontal: 10,
  },
  list: {
    paddingHorizontal: 16,
    paddingTop: 16,
    paddingBottom: 8,
    flexGrow: 1,
  },
  introBox: {
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: 10,
    padding: 12,
    marginBottom: 16,
  },
  introText: {
    fontSize: 12,
    color: theme.textMuted,
    lineHeight: 17,
  },
  bubble: {
    maxWidth: '85%',
    borderRadius: 14,
    paddingHorizontal: 14,
    paddingVertical: 10,
    marginBottom: 10,
  },
  userBubble: {
    alignSelf: 'flex-end',
    backgroundColor: theme.text,
  },
  assistantBubble: {
    alignSelf: 'flex-start',
    backgroundColor: theme.surface,
    borderWidth: 1,
    borderColor: theme.border,
  },
  userText: {
    color: theme.surface,
    fontSize: 14,
    lineHeight: 19,
  },
  assistantText: {
    color: theme.text,
    fontSize: 14,
    lineHeight: 19,
  },
  typingRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 6,
    paddingHorizontal: 20,
    paddingBottom: 6,
  },
  typingText: {
    fontSize: 12,
    color: theme.textMuted,
  },
  inputRow: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 10,
    paddingHorizontal: 16,
    paddingVertical: 12,
    borderTopWidth: 1,
    borderTopColor: theme.border,
    backgroundColor: theme.background,
  },
  input: {
    flex: 1,
    maxHeight: 100,
    borderWidth: 1,
    borderColor: theme.border,
    borderRadius: 18,
    paddingHorizontal: 16,
    paddingVertical: 10,
    fontSize: 14,
    color: theme.text,
    backgroundColor: theme.surface,
  },
  sendButton: {
    width: 36,
    height: 36,
    borderRadius: 18,
    backgroundColor: theme.text,
    alignItems: 'center',
    justifyContent: 'center',
  },
  sendButtonDisabled: {
    opacity: 0.4,
  },
});
