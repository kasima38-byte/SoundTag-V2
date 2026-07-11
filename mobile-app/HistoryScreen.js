import React, { useState, useEffect, useCallback } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, FlatList, Image } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Path, Circle, Rect } from 'react-native-svg';
import AsyncStorage from '@react-native-async-storage/async-storage';

const FILTERS = ['All', 'Today', 'This Week', 'Favorites'];

function getCategory(timestamp) {
  const now = new Date();
  const songDate = new Date(timestamp);
  const diffMs = now - songDate;
  const diffHours = diffMs / (1000 * 60 * 60);
  if (diffHours < 24 && now.toDateString() === songDate.toDateString()) return 'today';
  if (diffHours < 24 * 7) return 'week';
  return 'older';
}

function formatTime(timestamp) {
  const now = new Date();
  const songDate = new Date(timestamp);
  const diffMs = now - songDate;
  const diffMins = Math.floor(diffMs / (1000 * 60));
  const diffHours = Math.floor(diffMs / (1000 * 60 * 60));
  if (diffMins < 1) return 'Just now';
  if (diffMins < 60) return diffMins + ' min' + (diffMins > 1 ? 's' : '') + ' ago';
  if (diffHours < 24) return diffHours + ' hour' + (diffHours > 1 ? 's' : '') + ' ago';
  return songDate.toLocaleDateString();
}

export default function HistoryScreen({ navigation }) {
  const [activeFilter, setActiveFilter] = useState('All');
  const [songs, setSongs] = useState([]);
  const [loading, setLoading] = useState(true);

  const loadHistory = useCallback(async () => {
    setLoading(true);
    try {
      const stored = await AsyncStorage.getItem('soundtag_history');
      const items = stored ? JSON.parse(stored) : [];
      const mapped = items.map((s) => ({
        id: s.id || String(Date.now()),
        title: s.title || 'Unknown',
        artist: s.artist || 'Unknown',
        albumArt: s.albumArt || null,
        time: formatTime(s.recognized_at || new Date().toISOString()),
        favorite: !!s.favorite,
        category: getCategory(s.recognized_at || new Date().toISOString()),
        recognized_at: s.recognized_at,
      }));
      setSongs(mapped);
    } catch (err) {
      console.log('Failed to load history:', err);
      setSongs([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { loadHistory(); }, [loadHistory]);

  const toggleFavorite = async (id) => {
    const updated = songs.map(s => s.id === id ? { ...s, favorite: !s.favorite } : s);
    setSongs(updated);
    try {
      await AsyncStorage.setItem('soundtag_history', JSON.stringify(updated));
    } catch (e) { console.log('Save error:', e); }
  };

  const getFilteredSongs = () => {
    if (activeFilter === 'All') return songs;
    if (activeFilter === 'Today') return songs.filter(s => s.category === 'today');
    if (activeFilter === 'This Week') return songs.filter(s => s.category === 'today' || s.category === 'week');
    if (activeFilter === 'Favorites') return songs.filter(s => s.favorite);
    return songs;
  };

  const renderSong = ({ item }) => (
    <View style={styles.songRow}>
      <View style={styles.albumArtBox}>
        {item.albumArt ? (
          <Image source={{ uri: item.albumArt }} style={styles.albumArtImage} />
        ) : (
          <Svg width={20} height={20} viewBox="0 0 24 24">
            <Path d="M9 18V5l12-2v13" stroke="#8A8691" strokeWidth="1.5" fill="none" />
            <Circle cx="6" cy="18" r="3" stroke="#8A8691" strokeWidth="1.5" fill="none" />
            <Circle cx="18" cy="16" r="3" stroke="#8A8691" strokeWidth="1.5" fill="none" />
          </Svg>
        )}
      </View>
      <View style={styles.songInfo}>
        <Text style={styles.songTitle} numberOfLines={1}>{item.title}</Text>
        <Text style={styles.songArtist} numberOfLines={1}>{item.artist}</Text>
        <Text style={styles.songTime}>{item.time}</Text>
      </View>
      <TouchableOpacity onPress={() => toggleFavorite(item.id)} style={styles.heartButton}>
        <Svg width={22} height={22} viewBox="0 0 24 24">
          <Path
            d="M12 21s-7-4.5-9.5-9C1 8.5 2.5 5 6 5c2 0 3.5 1.2 6 3.5C14.5 6.2 16 5 18 5c3.5 0 5 3.5 3.5 7-2.5 4.5-9.5 9-9.5 9z"
            fill={item.favorite ? "#B14EFF" : "none"} stroke="#B14EFF" strokeWidth="1.5"
          />
        </Svg>
      </TouchableOpacity>
    </View>
  );

  return (
    <LinearGradient colors={["#0D0710", "#150A1F", "#0D0710"]} style={styles.container}>
      <View style={styles.header}>
        <Text style={styles.headerTitle}>History</Text>
      </View>
      <View style={styles.filterRow}>
        {FILTERS.map((filter) => (
          <TouchableOpacity
            key={filter}
            style={[styles.filterPill, activeFilter === filter && styles.filterPillActive]}
            onPress={() => setActiveFilter(filter)}
          >
            <Text style={[styles.filterText, activeFilter === filter && styles.filterTextActive]}>
              {filter}
            </Text>
          </TouchableOpacity>
        ))}
      </View>
      <FlatList
        data={getFilteredSongs()}
        keyExtractor={(item) => item.id}
        renderItem={renderSong}
        contentContainerStyle={styles.listContent}
        showsVerticalScrollIndicator={false}
        onRefresh={loadHistory}
        refreshing={loading}
        ListEmptyComponent={
          <Text style={styles.emptyText}>
            {loading ? "Loading..." : "No songs yet. Go identify some music!"}
          </Text>
        }
      />
      <View style={styles.bottomNav}>
        <TouchableOpacity style={styles.navItem} onPress={() => navigation.navigate('Listen')}>
          <Svg width={22} height={22} viewBox="0 0 24 24">
            <Rect x="2" y="9" width="3" height="6" rx="1.5" fill="#8A8691" />
            <Rect x="7" y="5" width="3" height="14" rx="1.5" fill="#8A8691" />
            <Rect x="12" y="2" width="3" height="20" rx="1.5" fill="#8A8691" />
            <Rect x="17" y="7" width="3" height="10" rx="1.5" fill="#8A8691" />
          </Svg>
          <Text style={styles.navLabelInactive}>Listen</Text>
        </TouchableOpacity>
        <View style={styles.navItem}>
          <Svg width={22} height={22} viewBox="0 0 24 24">
            <Circle cx="12" cy="12" r="9" stroke="#B14EFF" strokeWidth="1.5" fill="none" />
            <Path d="M12 7v5l3 3" stroke="#B14EFF" strokeWidth="1.5" strokeLinecap="round" fill="none" />
          </Svg>
          <Text style={styles.navLabelActive}>History</Text>
        </View>
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingHorizontal: 20, paddingTop: 60 },
  header: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 20 },
  headerTitle: { fontSize: 28, fontWeight: 'bold', color: '#FFFFFF' },
  filterRow: { flexDirection: 'row', marginBottom: 16, flexWrap: 'wrap' },
  filterPill: { backgroundColor: '#1A1220', paddingHorizontal: 14, paddingVertical: 8, borderRadius: 20, marginRight: 8, marginBottom: 8 },
  filterPillActive: { backgroundColor: '#9D4EDD' },
  filterText: { color: '#9E9AA7', fontSize: 13 },
  filterTextActive: { color: '#FFFFFF', fontWeight: '600' },
  listContent: { paddingBottom: 20 },
  songRow: { flexDirection: 'row', alignItems: 'center', paddingVertical: 12, borderBottomWidth: 1, borderBottomColor: '#1A1220' },
  albumArtBox: { width: 50, height: 50, borderRadius: 8, backgroundColor: '#1A1220', alignItems: 'center', justifyContent: 'center', marginRight: 12, overflow: 'hidden' },
  albumArtImage: { width: 50, height: 50, borderRadius: 8 },
  songInfo: { flex: 1 },
  songTitle: { color: '#FFFFFF', fontSize: 15, fontWeight: '600' },
  songArtist: { color: '#9E9AA7', fontSize: 13, marginTop: 2 },
  songTime: { color: '#6B6773', fontSize: 11, marginTop: 2 },
  emptyText: { color: '#8A8691', fontSize: 14, textAlign: 'center', marginTop: 60 },
  heartButton: { paddingHorizontal: 8 },
  bottomNav: { flexDirection: 'row', justifyContent: 'space-around', paddingTop: 16, paddingBottom: 32, borderTopWidth: 1, borderTopColor: '#1E1626' },
  navItem: { alignItems: 'center' },
  navLabelActive: { color: '#B14EFF', fontSize: 12, marginTop: 4, fontWeight: '600' },
  navLabelInactive: { color: '#8A8691', fontSize: 12, marginTop: 4 },
});
