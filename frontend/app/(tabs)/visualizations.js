import React, { useEffect, useMemo, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  SafeAreaView,
  Dimensions,
} from 'react-native';
import Svg, { Circle, Line, Text as SvgText } from 'react-native-svg';
import Animated, { useSharedValue, useAnimatedStyle } from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { forceSimulation, forceManyBody, forceLink, forceCenter, forceCollide } from 'd3-force';
import { useRouter } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchViewedPapersGraph } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import theme from '../../constants/theme';

const { width, height } = Dimensions.get('window');
const CANVAS_SIZE = Math.max(width, height) * 1.6; // bigger than the viewport - that's what makes panning meaningful
const NODE_BASE_RADIUS = 22;
const SIMULATION_TICKS = 300;

// A small fixed palette (rather than fully random hues) so bubble colors stay within the app's
// muted paper/parchment feel instead of clashing with it. Picked by hashing the category name,
// so the same category always gets the same color across sessions.
const CATEGORY_PALETTE = ['#c5b590', '#8fa8a3', '#c98a6b', '#7f9cc4', '#b98fb3', '#9fb37a', '#c47f7f', '#7fb3ab'];

function hashCategoryColor(category) {
  if (!category) return theme.textMuted;
  let hash = 0;
  for (let i = 0; i < category.length; i++) {
    hash = (hash * 31 + category.charCodeAt(i)) | 0;
  }
  return CATEGORY_PALETTE[Math.abs(hash) % CATEGORY_PALETTE.length];
}

/**
 * Runs d3-force synchronously to a stable layout (rather than animating tick-by-tick), since
 * this is a "here's the shape of your reading history" snapshot, not a live simulation - a
 * static-but-pannable result is both simpler and cheaper than continuous physics.
 */
function computeLayout(nodes, edges) {
  const simNodes = nodes.map((n) => ({ ...n }));
  const degreeById = {};
  edges.forEach((e) => {
    degreeById[e.source] = (degreeById[e.source] || 0) + 1;
    degreeById[e.target] = (degreeById[e.target] || 0) + 1;
  });

  const simulation = forceSimulation(simNodes)
    .force('charge', forceManyBody().strength(-140))
    .force(
      'link',
      forceLink(edges)
        .id((d) => d.id)
        .distance(90)
        .strength((d) => d.similarity)
    )
    .force('center', forceCenter(0, 0))
    .force('collide', forceCollide().radius((d) => NODE_BASE_RADIUS + Math.min(degreeById[d.id] || 0, 5) * 3 + 6))
    .stop();

  for (let i = 0; i < SIMULATION_TICKS; i++) simulation.tick();

  return simNodes.map((n) => ({
    ...n,
    x: n.x + CANVAS_SIZE / 2,
    y: n.y + CANVAS_SIZE / 2,
    radius: NODE_BASE_RADIUS + Math.min(degreeById[n.id] || 0, 5) * 3,
  }));
}

/**
 * Visualizations tab: a pannable bubble map of every paper the user has clicked "View Original
 * Paper" for (app/paper/[id].js), connected by cosine similarity of their stored embeddings
 * (backend/paper/embeddings.py, via GET /api/papers/viewed/graph) - e.g. two economics papers
 * cluster together, and a paper spanning economics and biology bridges both clusters. The layout
 * is computed once per load (d3-force, run to convergence) and rendered as static SVG the user
 * can drag around, rather than a live physics simulation.
 */
export default function VisualizationsScreen() {
  const router = useRouter();
  const { user, token, loading: authLoading } = useAuth();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [graph, setGraph] = useState(null);

  useEffect(() => {
    if (!token) {
      setLoading(false);
      return;
    }

    let cancelled = false;
    const load = async () => {
      try {
        setLoading(true);
        const data = await fetchViewedPapersGraph(token);
        if (!cancelled) setGraph(data);
      } catch (err) {
        console.error('Failed to load paper graph:', err);
        if (!cancelled) setError('Failed to load your paper map.');
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [token]);

  const laidOutNodes = useMemo(() => {
    if (!graph || graph.nodes.length === 0) return [];
    return computeLayout(graph.nodes, graph.edges);
  }, [graph]);

  const nodesById = useMemo(() => {
    const map = {};
    laidOutNodes.forEach((n) => {
      map[n.id] = n;
    });
    return map;
  }, [laidOutNodes]);

  // Center the canvas in the viewport on first render, then let the user drag it freely.
  const translateX = useSharedValue((width - CANVAS_SIZE) / 2);
  const translateY = useSharedValue((height - CANVAS_SIZE) / 2);
  const panStartX = useSharedValue(0);
  const panStartY = useSharedValue(0);

  const panGesture = Gesture.Pan()
    .onStart(() => {
      panStartX.value = translateX.value;
      panStartY.value = translateY.value;
    })
    .onUpdate((event) => {
      translateX.value = panStartX.value + event.translationX;
      translateY.value = panStartY.value + event.translationY;
    });

  const canvasStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }, { translateY: translateY.value }],
  }));

  const handleNodePress = (paperId) => {
    router.push(`/paper/${paperId}`);
  };

  return (
    <SafeAreaView style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>Visualize</Text>
      </View>

      {authLoading || loading ? (
        <View style={styles.centerContainer}>
          <ActivityIndicator size="large" color={theme.text} />
        </View>
      ) : !user ? (
        <View style={styles.centerContainer}>
          <Ionicons name="lock-closed-outline" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>Log in to see a map of the papers you've read.</Text>
          <TouchableOpacity style={styles.loginButton} onPress={() => router.push('/login')}>
            <Text style={styles.loginButtonText}>Log In</Text>
          </TouchableOpacity>
        </View>
      ) : error ? (
        <View style={styles.centerContainer}>
          <Text style={styles.emptyText}>{error}</Text>
        </View>
      ) : laidOutNodes.length === 0 ? (
        <View style={styles.centerContainer}>
          <Ionicons name="bubble-chart" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>
            Tap "View Original Paper" on a few papers you read, and they'll show up here -
            connected to each other by how similar they are.
          </Text>
        </View>
      ) : (
        <View style={styles.canvasViewport}>
          <GestureDetector gesture={panGesture}>
            <Animated.View style={[styles.canvas, canvasStyle]}>
              <Svg width={CANVAS_SIZE} height={CANVAS_SIZE}>
                {graph.edges.map((edge) => {
                  const source = nodesById[edge.source];
                  const target = nodesById[edge.target];
                  if (!source || !target) return null;
                  return (
                    <Line
                      key={`${edge.source}-${edge.target}`}
                      x1={source.x}
                      y1={source.y}
                      x2={target.x}
                      y2={target.y}
                      stroke={theme.textMuted}
                      strokeWidth={1 + edge.similarity * 2}
                      strokeOpacity={0.35}
                    />
                  );
                })}
                {laidOutNodes.map((node) => (
                  <React.Fragment key={node.id}>
                    <Circle
                      cx={node.x}
                      cy={node.y}
                      r={node.radius}
                      fill={hashCategoryColor(node.categories?.[0])}
                      stroke={theme.border}
                      strokeWidth={1.5}
                      onPress={() => handleNodePress(node.id)}
                    />
                    <SvgText
                      x={node.x}
                      y={node.y + node.radius + 14}
                      fontSize={11}
                      fill={theme.text}
                      textAnchor="middle"
                      onPress={() => handleNodePress(node.id)}
                    >
                      {node.title.length > 22 ? `${node.title.slice(0, 22)}...` : node.title}
                    </SvgText>
                  </React.Fragment>
                ))}
              </Svg>
            </Animated.View>
          </GestureDetector>
          <Text style={styles.hintText}>Drag to explore - tap a bubble to open that paper</Text>
        </View>
      )}
    </SafeAreaView>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    backgroundColor: theme.background,
  },
  header: {
    paddingHorizontal: 20,
    paddingVertical: 16,
    borderBottomWidth: 1.5,
    borderBottomColor: theme.border,
    backgroundColor: theme.surface,
  },
  headerTitle: {
    fontFamily: theme.serif,
    fontSize: 22,
    fontWeight: 'bold',
    color: theme.text,
  },
  centerContainer: {
    flex: 1,
    justifyContent: 'center',
    alignItems: 'center',
    padding: 30,
  },
  emptyText: {
    fontSize: 15,
    color: theme.textMuted,
    textAlign: 'center',
    marginTop: 10,
  },
  loginButton: {
    backgroundColor: theme.accent,
    borderWidth: 1.5,
    borderColor: theme.border,
    borderRadius: 10,
    paddingVertical: 10,
    paddingHorizontal: 30,
    marginTop: 16,
  },
  loginButtonText: {
    color: theme.text,
    fontSize: 15,
    fontWeight: 'bold',
  },
  canvasViewport: {
    flex: 1,
    overflow: 'hidden',
  },
  canvas: {
    position: 'absolute',
    width: CANVAS_SIZE,
    height: CANVAS_SIZE,
  },
  hintText: {
    position: 'absolute',
    bottom: 20,
    left: 0,
    right: 0,
    textAlign: 'center',
    fontSize: 12,
    color: theme.textMuted,
  },
});
