import React, { useCallback, useEffect, useMemo, useRef, useState } from 'react';
import {
  View,
  Text,
  TouchableOpacity,
  StyleSheet,
  ActivityIndicator,
  Dimensions,
} from 'react-native';
import { SafeAreaView } from 'react-native-safe-area-context';
import Svg, { Circle, Line, Text as SvgText } from 'react-native-svg';
import Animated, { useSharedValue, useAnimatedStyle } from 'react-native-reanimated';
import { Gesture, GestureDetector } from 'react-native-gesture-handler';
import { forceSimulation, forceManyBody, forceLink, forceCollide, forceX, forceY } from 'd3-force';
import { useRouter, useFocusEffect } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { fetchViewedPapersGraph } from '../../services/api';
import { useAuth } from '../../hooks/useAuth';
import { useTheme } from '../../hooks/useTheme';

const { width, height } = Dimensions.get('window');
const CANVAS_SIZE = Math.max(width, height) * 1.6; // bigger than the viewport - that's what makes panning meaningful
const NODE_BASE_RADIUS = 22;

// A small fixed palette (rather than fully random hues) so bubble colors stay within the app's
// muted paper/parchment feel instead of clashing with it. Picked by hashing the category name,
// so the same category always gets the same color across sessions.
const CATEGORY_PALETTE = ['#c5b590', '#8fa8a3', '#c98a6b', '#7f9cc4', '#b98fb3', '#9fb37a', '#c47f7f', '#7fb3ab'];

function hashCategoryColor(category, fallbackColor) {
  if (!category) return fallbackColor;
  let hash = 0;
  for (let i = 0; i < category.length; i++) {
    hash = (hash * 31 + category.charCodeAt(i)) | 0;
  }
  return CATEGORY_PALETTE[Math.abs(hash) % CATEGORY_PALETTE.length];
}

/**
 * Edges between papers: the server's embedding-similarity edges (semantic closeness) plus a
 * weaker edge for every pair sharing at least one category, so papers still cluster by topic
 * when embeddings are missing or the similarity threshold is too strict.
 */
function buildEdges(nodes, semanticEdges) {
  const byPair = new Map();
  const key = (a, b) => (a < b ? `${a}|${b}` : `${b}|${a}`);
  (semanticEdges || []).forEach((e) => {
    byPair.set(key(e.source, e.target), { source: e.source, target: e.target, strength: e.similarity, semantic: true });
  });
  for (let i = 0; i < nodes.length; i++) {
    for (let j = i + 1; j < nodes.length; j++) {
      const a = nodes[i];
      const b = nodes[j];
      const shared = (a.categories || []).filter((c) => (b.categories || []).includes(c)).length;
      if (!shared) continue;
      const k = key(a.id, b.id);
      const existing = byPair.get(k);
      if (existing) {
        existing.strength = Math.min(1, existing.strength + 0.1 * shared);
      } else {
        byPair.set(k, { source: a.id, target: b.id, strength: Math.min(0.6, 0.35 + 0.1 * shared), semantic: false });
      }
    }
  }
  return Array.from(byPair.values());
}

function radiusFor(degree) {
  return NODE_BASE_RADIUS + Math.min(degree, 5) * 3;
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
  const { theme } = useTheme();
  const styles = useMemo(() => createStyles(theme), [theme]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [graph, setGraph] = useState(null);

  // Reload every time this tab regains focus - not just on mount/token change - so a paper
  // viewed just before switching tabs shows up immediately, the same staleness fix already
  // applied to the Saved tab.
  useFocusEffect(
    useCallback(() => {
      if (!token) {
        setLoading(false);
        setGraph(null);
        return;
      }

      let cancelled = false;
      const load = async () => {
        try {
          setLoading(true);
          setError(null);
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
    }, [token])
  );

  const edges = useMemo(() => (graph ? buildEdges(graph.nodes, graph.edges) : []), [graph]);

  // Live d3-force simulation: bubbles spring toward their linked neighbours, bounce off each
  // other, and keep wobbling after being dragged. Positions live in a ref and are copied to
  // state once per animation frame to re-render the SVG.
  const simRef = useRef(null);
  const simNodesRef = useRef([]);
  const [, forceRender] = useState(0);
  const frameRef = useRef(null);

  useEffect(() => {
    if (!graph || graph.nodes.length === 0) {
      simNodesRef.current = [];
      return undefined;
    }
    const degree = {};
    edges.forEach((e) => {
      degree[e.source] = (degree[e.source] || 0) + 1;
      degree[e.target] = (degree[e.target] || 0) + 1;
    });
    const center = CANVAS_SIZE / 2;
    const simNodes = graph.nodes.map((n, i) => {
      const angle = (i / graph.nodes.length) * Math.PI * 2;
      return {
        ...n,
        radius: radiusFor(degree[n.id] || 0),
        x: center + Math.cos(angle) * 120,
        y: center + Math.sin(angle) * 120,
      };
    });
    simNodesRef.current = simNodes;

    const simulation = forceSimulation(simNodes)
      .force('charge', forceManyBody().strength(-160))
      .force(
        'link',
        forceLink(edges.map((e) => ({ ...e })))
          .id((d) => d.id)
          .distance((d) => 170 - d.strength * 90)
          .strength((d) => 0.15 + d.strength * 0.5)
      )
      .force('x', forceX(center).strength(0.04))
      .force('y', forceY(center).strength(0.04))
      .force('collide', forceCollide().radius((d) => d.radius + 6).strength(0.9))
      .velocityDecay(0.22) // low friction = bouncy
      .alphaDecay(0.012)
      .alphaTarget(0.02); // never fully rests, so bubbles keep a gentle float
    simRef.current = simulation;

    simulation.on('tick', () => {
      if (frameRef.current) return;
      frameRef.current = requestAnimationFrame(() => {
        frameRef.current = null;
        forceRender((n) => n + 1);
      });
    });

    return () => {
      simulation.stop();
      if (frameRef.current) cancelAnimationFrame(frameRef.current);
      frameRef.current = null;
    };
  }, [graph, edges]);

  const laidOutNodes = simNodesRef.current;
  const [legendOpen, setLegendOpen] = useState(true);
  // Bubbles are colored by their first category, so the legend lists exactly those
  const legendCategories = Array.from(
    new Set((graph?.nodes || []).map((n) => n.categories?.[0]).filter(Boolean))
  );
  const nodesById = {};
  laidOutNodes.forEach((n) => {
    nodesById[n.id] = n;
  });

  const translateX = useSharedValue((width - CANVAS_SIZE) / 2);
  const translateY = useSharedValue((height - CANVAS_SIZE) / 2);
  const panStart = useRef({ x: 0, y: 0 });
  const dragged = useRef(null); // { node, startX, startY } while a bubble is being dragged

  const hitTest = (viewX, viewY) => {
    const cx = viewX - translateX.value;
    const cy = viewY - translateY.value;
    for (let i = simNodesRef.current.length - 1; i >= 0; i--) {
      const n = simNodesRef.current[i];
      const r = n.radius + 8;
      if ((n.x - cx) ** 2 + (n.y - cy) ** 2 <= r * r) return n;
    }
    return null;
  };

  const handleNodePress = (paperId) => {
    router.push(`/paper/${paperId}`);
  };

  // Dragging a bubble pins it to the finger while the rest of the graph reacts; letting go
  // releases it and the simulation springs it back. Dragging empty space pans the canvas.
  const panGesture = Gesture.Pan()
    .runOnJS(true)
    .onStart((event) => {
      panStart.current = { x: translateX.value, y: translateY.value };
      const node = hitTest(event.x - event.translationX, event.y - event.translationY);
      if (node) {
        dragged.current = { node, startX: node.x, startY: node.y };
        node.fx = node.x;
        node.fy = node.y;
        simRef.current?.alphaTarget(0.3).restart();
      }
    })
    .onUpdate((event) => {
      const d = dragged.current;
      if (d) {
        d.node.fx = d.startX + event.translationX;
        d.node.fy = d.startY + event.translationY;
      } else {
        translateX.value = panStart.current.x + event.translationX;
        translateY.value = panStart.current.y + event.translationY;
      }
    })
    .onFinalize(() => {
      const d = dragged.current;
      if (d) {
        d.node.fx = null;
        d.node.fy = null;
        dragged.current = null;
        simRef.current?.alphaTarget(0.02).alpha(0.6).restart();
      }
    });

  const tapGesture = Gesture.Tap()
    .runOnJS(true)
    .onEnd((event, success) => {
      if (!success) return;
      const node = hitTest(event.x, event.y);
      if (node) handleNodePress(node.id);
    });

  const gesture = Gesture.Exclusive(panGesture, tapGesture);

  const canvasStyle = useAnimatedStyle(() => ({
    transform: [{ translateX: translateX.value }, { translateY: translateY.value }],
  }));

  return (
    <SafeAreaView style={styles.container} edges={['top']}>
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
          <Text style={styles.emptyText}> Log in to see a map of the papers you've read. </Text>
          <TouchableOpacity style={styles.loginButton} onPress={() => router.push('/login')}>
            <Text style={styles.loginButtonText}>Log In</Text>
          </TouchableOpacity>
        </View>
      ) : error ? (
        <View style={styles.centerContainer}>
          <Text style={styles.emptyText}>{error}</Text>
        </View>
      ) : !graph || graph.nodes.length === 0 ? (
        <View style={styles.centerContainer}>
          <Ionicons name="git-network-outline" size={40} color={theme.textMuted} />
          <Text style={styles.emptyText}>
            Any full texts you explore through the app will show up here!
          </Text>
          <TouchableOpacity
            style={[styles.exploreButton, styles.actionButton]}
            onPress={() => router.push('/')}
          >
            <Text style={styles.exploreButtonText}>Go Explore Now</Text>
          </TouchableOpacity>
        </View>
      ) : (
        <>
        <View style={styles.canvasViewport}>
          <GestureDetector gesture={gesture}>
            <View style={styles.gestureSurface} collapsable={false}>
              <Animated.View style={[styles.canvas, canvasStyle]} pointerEvents="none">
                <Svg width={CANVAS_SIZE} height={CANVAS_SIZE}>
                  {edges.map((edge) => {
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
                        strokeWidth={1 + edge.strength * 2}
                        strokeOpacity={edge.semantic ? 0.45 : 0.25}
                        strokeDasharray={edge.semantic ? undefined : '4,4'}
                      />
                    );
                  })}
                  {laidOutNodes.map((node) => (
                    <React.Fragment key={node.id}>
                      <Circle
                        cx={node.x}
                        cy={node.y}
                        r={node.radius}
                        fill={hashCategoryColor(node.categories?.[0], theme.textMuted)}
                        stroke={theme.border}
                        strokeWidth={1.5}
                      />
                      <SvgText
                        x={node.x}
                        y={node.y + node.radius + 14}
                        fontSize={11}
                        fill={theme.text}
                        textAnchor="middle"
                      >
                        {node.title.length > 22 ? `${node.title.slice(0, 22)}...` : node.title}
                      </SvgText>
                    </React.Fragment>
                  ))}
                </Svg>
              </Animated.View>
            </View>
          </GestureDetector>
          {legendOpen ? (
            <View style={styles.legend}>
                <TouchableOpacity style={styles.legendHeader} onPress={() => setLegendOpen(false)}>
                  <Text style={styles.legendTitle}>Legend</Text>
                  <Ionicons name="chevron-up" size={14} color={theme.textMuted} />
                </TouchableOpacity>
                  {legendCategories.map((category) => (
                    <View key={category} style={styles.legendRow}>
                      <View style={[styles.legendDot, { backgroundColor: hashCategoryColor(category, theme.textMuted) }]} />
                      <Text style={styles.legendText}>{category+"  "}</Text>
                    </View>
                  ))}
                <View style={styles.legendRow}>
                  <View style={[styles.legendLine, { backgroundColor: theme.textMuted }]} />
                  <Text style={styles.legendText}>Similar content  </Text>
                </View>
                <View style={styles.legendRow}>
                  <View style={styles.legendDashed}>
                    {[0, 1, 2].map((i) => (
                      <View key={i} style={[styles.legendDash, { backgroundColor: theme.textMuted }]} />
                    ))}
                  </View>
                  <Text style={styles.legendText}>Shared category  </Text>
                </View>
                <Text style={styles.legendNote}>Thicker line = stronger link. Bigger bubble = more links.</Text>
              
              
            </View>
          ) : (
            <TouchableOpacity style={styles.legendCollapsed} onPress={() => setLegendOpen(true)}>
              <Ionicons name="information-circle-outline" size={16} color={theme.textMuted} />
              <Text style={styles.legendTitle}>Legend</Text>
            </TouchableOpacity>
          )}
        </View>
        <Text style={styles.hintText}>Drag a bubble to play with it, drag the background to pan, tap to open</Text>
        </>
      )}
    </SafeAreaView>
  );
}

const createStyles = (theme) => StyleSheet.create({
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
    margin: 10,
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
  gestureSurface: {
    flex: 1,
  },
  canvas: {
    position: 'absolute',
    width: CANVAS_SIZE,
    height: CANVAS_SIZE,
  },
  hintText: {
    // Its own row under the canvas (not floating over it), so it can never sit on top of bubbles
    paddingTop: 8,
    paddingBottom: 30, // clears the raised center tab button
    paddingHorizontal: 16,
    textAlign: 'center',
    fontSize: 12,
    color: theme.textMuted,
  },
  legend: {
    position: 'absolute',
    top: 10,
    left: 10,
    maxWidth: '70%',
    padding: 10,
    borderRadius: 10,
    borderWidth: 1,
    borderColor: theme.border,
    backgroundColor: theme.surface,
    opacity: 0.75,
    gap: 6,
  },
  legendCollapsed: {
    position: 'absolute',
    top: 10,
    left: 10,
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    paddingHorizontal: 10,
    paddingVertical: 6,
    borderRadius: 14,
    borderWidth: 1,
    borderColor: theme.border,
    backgroundColor: theme.surface,
  },
  legendHeader: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'space-between',
  },
  legendTitle: {
    fontSize: 12,
    fontWeight: 'bold',
    color: theme.text,
  },
  legendRow: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 8,
  },
  legendDot: {
    width: 12,
    height: 12,
    borderRadius: 6,
    borderWidth: 1,
    borderColor: theme.border,
  },
  legendLine: {
    width: 24,
    height: 2,
  },
  legendDashed: {
    width: 24,
    flexDirection: 'row',
    justifyContent: 'space-between',
  },
  legendDash: {
    width: 6,
    height: 2,
  },
  legendText: {
    fontSize: 12,
    color: theme.text,
  },
  legendNote: {
    fontSize: 11,
    color: theme.textMuted,
  },
  actionRow: {
    gap: 10,
  },
  actionButton: {
    flexDirection: 'row',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 6,
    borderRadius: 10,
    paddingVertical: 12,
    paddingHorizontal: 10,
    
  },
  exploreButton: {
    backgroundColor: theme.accent,
  },
  exploreButtonText: {
    color: theme.text,
    fontWeight: 'bold',
    fontSize: 14,
  },
});
