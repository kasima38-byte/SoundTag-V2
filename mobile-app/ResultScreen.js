import React, { useState, useRef, useEffect } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Image, TextInput, ScrollView, Share, Linking, Animated } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Path, Rect, Circle } from 'react-native-svg';
import { useAudioPlayer, useAudioPlayerStatus } from 'expo-audio';

export default function ResultScreen({ navigation, route }) {
  const song = route?.params?.song || {
    title: 'Unknown Song',
    artist: 'Unknown Artist',
    album: '',
    year: '',
    albumArt: null,
    genre: '-',
    bpm: '-',
    key: '-',
    previewUrl: null,
  };

  const [isFavorite, setIsFavorite] = useState(false);
  const [note, setNote] = useState('');
  const [saved, setSaved] = useState(true);

  const fadeAnim = useRef(new Animated.Value(0)).current;
  const scaleAnim = useRef(new Animated.Value(0.9)).current;

  const player = useAudioPlayer(song.previewUrl || null);
  const status = useAudioPlayerStatus(player);

  useEffect(() => {
    Animated.parallel([
      Animated.timing(fadeAnim, { toValue: 1, duration: 500, useNativeDriver: true }),
      Animated.spring(scaleAnim, { toValue: 1, friction: 6, useNativeDriver: true }),
    ]).start();
  }, []);

  const handlePlayPreview = () => {
    if (!song.previewUrl) return;
    if (status.playing) {
      player.pause();
    } else {
      if (status.currentTime >= status.duration && status.duration > 0) {
        player.seekTo(0);
      }
      player.play();
    }
  };

  const progressPercent = status.duration > 0 ? (status.currentTime / status.duration) * 100 : 0;

  const handleSpotify = () => {
    const query = encodeURIComponent(`${song.title} ${song.artist}`);
    Linking.openURL(`https://open.spotify.com/search/${query}`);
  };

  const handleYouTube = () => {
    const query = encodeURIComponent(`${song.title} ${song.artist}`);
    Linking.openURL(`https://www.youtube.com/results?search_query=${query}`);
  };

  const handleShare = async () => {
    try {
      await Share.share({
        message: `Check out "${song.title}" by ${song.artist} — found with soundTag!`,
      });
    } catch (error) {
      console.log('Share error:', error);
    }
  };

  return (
    <LinearGradient colors={['#0D0710', '#150A1F', '#0D0710']} style={styles.container}>
      <View style={styles.topRow}>
        <TouchableOpacity onPress={() => navigation.navigate('Listen')}>
          <Svg width={22} height={22} viewBox="0 0 24 24">
            <Path d="M15 18l-6-6 6-6" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" fill="none" />
          </Svg>
        </TouchableOpacity>
        <TouchableOpacity>
          <Svg width={22} height={22} viewBox="0 0 24 24">
            <Rect x="4" y="11" width="3" height="3" rx="1.5" fill="#FFFFFF" />
            <Rect x="10.5" y="11" width="3" height="3" rx="1.5" fill="#FFFFFF" />
            <Rect x="17" y="11" width="3" height="3" rx="1.5" fill="#FFFFFF" />
          </Svg>
        </TouchableOpacity>
      </View>

      <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={styles.scrollContent}>
        <Animated.View style={{ opacity: fadeAnim, transform: [{ scale: scaleAnim }], width: '100%', alignItems: 'center' }}>
          <View style={styles.albumArtWrapper}>
            {song.albumArt ? (
              <Image source={{ uri: song.albumArt }} style={styles.albumArt} />
            ) : (
              <View style={[styles.albumArt, styles.albumArtPlaceholder]}>
                <Svg width={40} height={40} viewBox="0 0 24 24">
                  <Path d="M9 18V5l12-2v13" stroke="#8A8691" strokeWidth="1.5" fill="none" />
                  <Circle cx="6" cy="18" r="3" stroke="#8A8691" strokeWidth="1.5" fill="none" />
                  <Circle cx="18" cy="16" r="3" stroke="#8A8691" strokeWidth="1.5" fill="none" />
                </Svg>
              </View>
            )}
          </View>

          <Text style={styles.songTitle}>{song.title}</Text>
          <Text style={styles.artist}>{song.artist}</Text>
          {(song.album || song.year) && (
            <Text style={styles.albumYear}>
              {song.album}{song.album && song.year ? ' • ' : ''}{song.year}
            </Text>
          )}

          <View style={styles.playerBar}>
            <TouchableOpacity style={styles.playButton} onPress={handlePlayPreview}>
              {status.playing ? (
                <Svg width={16} height={16} viewBox="0 0 24 24">
                  <Rect x="6" y="5" width="4" height="14" rx="1" fill="#0D0710" />
                  <Rect x="14" y="5" width="4" height="14" rx="1" fill="#0D0710" />
                </Svg>
              ) : (
                <Svg width={18} height={18} viewBox="0 0 24 24">
                  <Path d="M8 5v14l11-7z" fill="#0D0710" />
                </Svg>
              )}
            </TouchableOpacity>
            <View style={styles.waveformTrack}>
              <View style={[styles.waveformFill, { width: `${progressPercent}%` }]} />
            </View>
            <Text style={styles.duration}>
              {song.previewUrl ? '0:30' : 'No preview'}
            </Text>
          </View>

          <View style={styles.metaRow}>
            <View style={styles.metaItem}>
              <Text style={styles.metaLabel}>Genre</Text>
              <Text style={styles.metaValue}>{song.genre}</Text>
            </View>
            <View style={styles.metaItem}>
              <Text style={styles.metaLabel}>BPM</Text>
              <Text style={styles.metaValue}>{song.bpm}</Text>
            </View>
            <View style={styles.metaItem}>
              <Text style={styles.metaLabel}>Key</Text>
              <Text style={styles.metaValue}>{song.key}</Text>
            </View>
          </View>

          <View style={styles.actionsRow}>
            <TouchableOpacity style={styles.actionButton} onPress={handleSpotify}>
              <View style={[styles.actionIcon, { backgroundColor: '#1DB954' }]}>
                <Svg width={26} height={26} viewBox="0 0 168 168">
                  <Circle cx="84" cy="84" r="84" fill="#1DB954" />
                  <Path
                    d="M119.5 108.5c-1.7 2.8-5.3 3.7-8.1 2-22.2-13.6-50.2-16.6-83.1-9.1-3.2.7-6.4-1.3-7.1-4.5-.7-3.2 1.3-6.4 4.5-7.1 36-8.2 66.9-4.7 91.7 10.4 2.9 1.8 3.8 5.4 2.1 8.3zm10.2-22.7c-2.1 3.4-6.5 4.5-9.9 2.4-25.4-15.6-64.1-20.1-94.1-11-3.8 1.1-7.8-1-9-4.8-1.1-3.8 1-7.8 4.8-9 34.3-10.4 76.9-5.4 106.1 12.5 3.4 2.1 4.5 6.5 2.1 9.9zm.9-23.6C99.7 45.2 51.1 43.6 22.6 52.2c-4.5 1.4-9.3-1.2-10.7-5.7-1.4-4.5 1.2-9.3 5.7-10.7C50.8 25.6 105 27.5 141 49c4 2.4 5.3 7.6 2.9 11.6-2.4 4-7.6 5.3-11.3 2.6z"
                    fill="#000000"
                  />
                </Svg>
              </View>
              <Text style={styles.actionLabel}>Open in{'\n'}Spotify</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionButton} onPress={handleYouTube}>
              <View style={[styles.actionIcon, { backgroundColor: '#FF0000' }]}>
                <Svg width={24} height={24} viewBox="0 0 24 24">
                  <Rect x="1" y="5" width="22" height="14" rx="4" fill="#FF0000" />
                  <Path d="M10 8.5l6 3.5-6 3.5v-7z" fill="#FFFFFF" />
                </Svg>
              </View>
              <Text style={styles.actionLabel}>Watch on{'\n'}YouTube</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionButton} onPress={handleShare}>
              <View style={styles.actionIconDark}>
                <Svg width={18} height={18} viewBox="0 0 24 24">
                  <Path d="M12 3v12M8 7l4-4 4 4M5 13v6a2 2 0 002 2h10a2 2 0 002-2v-6" stroke="#FFFFFF" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
                </Svg>
              </View>
              <Text style={styles.actionLabel}>Share</Text>
            </TouchableOpacity>

            <TouchableOpacity style={styles.actionButton} onPress={() => setIsFavorite(!isFavorite)}>
              <View style={styles.actionIconDark}>
                <Svg width={18} height={18} viewBox="0 0 24 24">
                  <Path
                    d="M12 21s-7-4.5-9.5-9C1 8.5 2.5 5 6 5c2 0 3.5 1.2 6 3.5C14.5 6.2 16 5 18 5c3.5 0 5 3.5 3.5 7-2.5 4.5-9.5 9-9.5 9z"
                    fill={isFavorite ? '#B14EFF' : 'none'}
                    stroke="#B14EFF"
                    strokeWidth="1.5"
                  />
                </Svg>
              </View>
              <Text style={styles.actionLabel}>Favorite</Text>
            </TouchableOpacity>
          </View>

          <View style={styles.noteBox}>
            <Text style={styles.noteLabel}>📝 Add a note</Text>
            <TextInput
              style={styles.noteInput}
              placeholder="Write something about this song..."
              placeholderTextColor="#6B6773"
              value={note}
              onChangeText={setNote}
              multiline
            />
          </View>

          <TouchableOpacity style={styles.savedButton} onPress={() => setSaved(!saved)}>
            {saved && (
              <Svg width={18} height={18} viewBox="0 0 24 24" style={{ marginRight: 8 }}>
                <Path d="M5 13l4 4L19 7" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" fill="none" />
              </Svg>
            )}
            <Text style={styles.savedText}>{saved ? 'Saved to History' : 'Save to History'}</Text>
          </TouchableOpacity>
        </Animated.View>
      </ScrollView>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingHorizontal: 20, paddingTop: 60 },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center', marginBottom: 10 },
  scrollContent: { alignItems: 'center', paddingBottom: 40 },
  albumArtWrapper: { marginTop: 10, marginBottom: 20 },
  albumArt: { width: 220, height: 220, borderRadius: 16 },
  albumArtPlaceholder: { backgroundColor: '#1E1626', alignItems: 'center', justifyContent: 'center' },
  songTitle: { fontSize: 24, fontWeight: 'bold', color: '#FFFFFF', textAlign: 'center' },
  artist: { fontSize: 17, color: '#B14EFF', marginTop: 4 },
  albumYear: { fontSize: 13, color: '#8A8691', marginTop: 4 },
  playerBar: {
    flexDirection: 'row', alignItems: 'center', backgroundColor: '#1A1220',
    borderRadius: 30, paddingHorizontal: 14, paddingVertical: 10, marginTop: 24, width: '100%',
  },
  playButton: {
    width: 34, height: 34, borderRadius: 17, backgroundColor: '#FFFFFF',
    alignItems: 'center', justifyContent: 'center', marginRight: 10,
  },
  waveformTrack: {
    flex: 1, height: 24, backgroundColor: '#3A2A4A', borderRadius: 4, marginRight: 10, overflow: 'hidden',
  },
  waveformFill: {
    height: '100%', backgroundColor: '#B14EFF',
  },
  duration: { color: '#8A8691', fontSize: 12 },
  metaRow: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', backgroundColor: '#1A1220', borderRadius: 16, paddingVertical: 16, marginTop: 20 },
  metaItem: { flex: 1, alignItems: 'center' },
  metaLabel: { color: '#8A8691', fontSize: 12, marginBottom: 4 },
  metaValue: { color: '#B14EFF', fontSize: 15, fontWeight: '600' },
  actionsRow: { flexDirection: 'row', justifyContent: 'space-between', width: '100%', marginTop: 20 },
  actionButton: { alignItems: 'center', flex: 1 },
  actionIcon: { width: 44, height: 44, borderRadius: 12, alignItems: 'center', justifyContent: 'center', marginBottom: 6, overflow: 'hidden' },
  actionIconDark: { width: 44, height: 44, borderRadius: 12, backgroundColor: '#1A1220', alignItems: 'center', justifyContent: 'center', marginBottom: 6 },
  actionLabel: { color: '#C9C6D0', fontSize: 11, textAlign: 'center' },
  noteBox: { width: '100%', backgroundColor: '#1A1220', borderRadius: 14, padding: 14, marginTop: 24 },
  noteLabel: { color: '#C9C6D0', fontSize: 13, marginBottom: 8 },
  noteInput: { color: '#FFFFFF', fontSize: 14, minHeight: 20 },
  savedButton: {
    flexDirection: 'row', backgroundColor: '#9D4EDD', width: '100%', paddingVertical: 16,
    borderRadius: 30, alignItems: 'center', justifyContent: 'center', marginTop: 24,
  },
  savedText: { color: '#FFFFFF', fontSize: 16, fontWeight: 'bold' },
});