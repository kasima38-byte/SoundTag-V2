import React, { useRef, useEffect, useState } from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Animated, Easing, Alert } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Rect, Circle, Path } from 'react-native-svg';
import { useAudioRecorder, RecordingPresets, AudioModule, useAudioRecorderState } from 'expo-audio';

const AnimatedRect = Animated.createAnimatedComponent(Rect);
const AUDD_API_KEY = 'ee791c1c1f6a487d622421c89c0621c4';
const BACKEND_URL = 'https://soundtag-v2-production.up.railway.app';

export default function ListenScreen({ navigation }) {
  const [isListening, setIsListening] = useState(false);
  const [statusText, setStatusText] = useState('Tap to identify music');
  const [subText, setSubText] = useState("We'll listen and find the song");
  const audioRecorder = useAudioRecorder(RecordingPresets.HIGH_QUALITY);
  const bar1 = useRef(new Animated.Value(0.5)).current;
  const bar2 = useRef(new Animated.Value(0.8)).current;
  const bar3 = useRef(new Animated.Value(0.4)).current;
  const bar4 = useRef(new Animated.Value(1)).current;
  const bar5 = useRef(new Animated.Value(0.6)).current;
  const bar6 = useRef(new Animated.Value(0.3)).current;
  const ringScale = useRef(new Animated.Value(1)).current;
  const ringOpacity = useRef(new Animated.Value(0.5)).current;
  const micScale = useRef(new Animated.Value(1)).current;

  const makePulse = (val, min, max, duration) =>
    Animated.loop(Animated.sequence([
      Animated.timing(val, { toValue: max, duration, easing: Easing.inOut(Easing.ease), useNativeDriver: false }),
      Animated.timing(val, { toValue: min, duration, easing: Easing.inOut(Easing.ease), useNativeDriver: false }),
    ]));

  useEffect(() => {
    (async () => {
      const status = await AudioModule.requestRecordingPermissionsAsync();
      if (!status.granted) Alert.alert('Permission needed', 'SoundTag needs microphone access.');
    })();
    const animations = [
      makePulse(bar1, 0.4, 1, 500), makePulse(bar2, 0.6, 0.9, 650),
      makePulse(bar3, 0.3, 0.8, 550), makePulse(bar4, 0.7, 1, 480),
      makePulse(bar5, 0.4, 0.9, 620), makePulse(bar6, 0.2, 0.6, 700),
    ];
    animations.forEach(a => a.start());
    Animated.loop(Animated.sequence([
      Animated.parallel([
        Animated.timing(ringScale, { toValue: 1.08, duration: 1200, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(ringOpacity, { toValue: 0.9, duration: 1200, useNativeDriver: true }),
      ]),
      Animated.parallel([
        Animated.timing(ringScale, { toValue: 1, duration: 1200, easing: Easing.inOut(Easing.ease), useNativeDriver: true }),
        Animated.timing(ringOpacity, { toValue: 0.5, duration: 1200, useNativeDriver: true }),
      ]),
    ])).start();
    return () => animations.forEach(a => a.stop());
  }, []);

  const handleMicPress = async () => {
    if (isListening) return;
    setIsListening(true);
    setStatusText('Listening...');
    setSubText('Analyzing the sound around you');
    Animated.sequence([
      Animated.timing(micScale, { toValue: 0.85, duration: 100, useNativeDriver: true }),
      Animated.timing(micScale, { toValue: 1, duration: 150, useNativeDriver: true }),
    ]).start();
    try {
      await audioRecorder.prepareToRecordAsync();
      audioRecorder.record();
      await new Promise(resolve => setTimeout(resolve, 8000));
      await audioRecorder.stop();
      const uri = audioRecorder.uri;
      if (!uri) throw new Error('No recording found');
      setStatusText('Identifying...');
      setSubText('Searching millions of songs');
      const formData = new FormData();
      formData.append('api_token', AUDD_API_KEY);
      formData.append('return', 'spotify,apple_music');
      formData.append('file', { uri, name: 'recording.m4a', type: 'audio/m4a' });
      const response = await fetch('https://api.audd.io/', {
        method: 'POST', body: formData,
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      const data = await response.json();
      if (data.status === 'error') throw new Error(data.error?.error_message || 'Recognition failed');
      if (!data.result) {
        setIsListening(false);
        setStatusText('Tap to identify music');
        setSubText("We'll listen and find the song");
        Alert.alert('No match found', "Couldn't identify that song. Try again with clearer audio.");
        return;
      }
      const r = data.result;
      const song = {
        title: r.title, artist: r.artist, album: r.album || '',
        year: r.release_date ? r.release_date.substring(0, 4) : '',
        albumArt: r.spotify?.album?.images?.[0]?.url ||
          r.apple_music?.artwork?.url?.replace('{w}', '600').replace('{h}', '600') || null,
        genre: r.apple_music?.genreNames?.[0] || '-',
        bpm: '-', key: '-',
        previewUrl: r.spotify?.preview_url || null,
        spotifyUrl: r.spotify?.external_urls?.spotify || null,
      };
      // Save to local history
      try {
        const AsyncStorage = require('@react-native-async-storage/async-storage').default;
        const existing = await AsyncStorage.getItem('soundtag_history');
        const history = existing ? JSON.parse(existing) : [];
        history.unshift({ ...song, id: Date.now().toString(), recognized_at: new Date().toISOString() });
        await AsyncStorage.setItem('soundtag_history', JSON.stringify(history.slice(0, 100)));
      } catch (e) { console.log('History save error:', e); }
      setIsListening(false);
      setStatusText('Tap to identify music');
      setSubText("We'll listen and find the song");
      navigation.navigate('Result', { song });
    } catch (error) {
      setIsListening(false);
      setStatusText('Tap to identify music');
      setSubText("We'll listen and find the song");
      Alert.alert('Something went wrong', error.message || 'Please try again.');
    }
  };

  const barHeight = (val, base) => val.interpolate({ inputRange: [0, 1], outputRange: [base * 0.2, base] });

  return (
    <LinearGradient colors={['#0D0710', '#150A1F', '#0D0710']} style={styles.container}>
      <View style={styles.topRow}>
        <TouchableOpacity onPress={() => navigation.navigate('Welcome')}>
          <Svg width={24} height={24} viewBox="0 0 24 24">
            <Path d="M18 6L6 18M6 6l12 12" stroke="#FFFFFF" strokeWidth="2" strokeLinecap="round" />
          </Svg>
        </TouchableOpacity>
        <TouchableOpacity onPress={() => navigation.navigate('History')}>
          <Svg width={26} height={26} viewBox="0 0 24 24">
            <Circle cx="12" cy="12" r="9" stroke="#FFFFFF" strokeWidth="1.5" fill="none" />
            <Path d="M12 7v5l3 3" stroke="#FFFFFF" strokeWidth="1.5" strokeLinecap="round" fill="none" />
          </Svg>
        </TouchableOpacity>
      </View>
      <View style={{ flex: 0.5 }} />
      <Text style={styles.heading}>{statusText}</Text>
      <Text style={styles.subheading}>{subText}</Text>
      <View style={{ flex: 1 }} />
      <View style={styles.circleWrapper}>
        <Animated.View style={[styles.outerRing, { transform: [{ scale: ringScale }], opacity: ringOpacity }]}>
          <Svg width={90} height={70} viewBox="0 0 90 70">
            <AnimatedRect x="5" width="6" height={barHeight(bar1, 45)} rx="3" fill="#B14EFF" />
            <AnimatedRect x="16" width="6" height={barHeight(bar2, 55)} rx="3" fill="#C77DFF" />
            <AnimatedRect x="27" width="6" height={barHeight(bar3, 40)} rx="3" fill="#9D4EDD" />
            <AnimatedRect x="38" width="6" height={barHeight(bar4, 65)} rx="3" fill="#D896FF" />
            <AnimatedRect x="49" width="6" height={barHeight(bar5, 48)} rx="3" fill="#B14EFF" />
            <AnimatedRect x="60" width="6" height={barHeight(bar6, 35)} rx="3" fill="#C77DFF" />
          </Svg>
        </Animated.View>
      </View>
      <View style={{ flex: 1 }} />
      <Animated.View style={{ transform: [{ scale: micScale }], alignSelf: 'center' }}>
        <TouchableOpacity style={[styles.micButton, isListening && styles.micButtonActive]} onPress={handleMicPress} disabled={isListening}>
          <Svg width={28} height={28} viewBox="0 0 24 24">
            <Path d="M12 15a3 3 0 003-3V6a3 3 0 00-6 0v6a3 3 0 003 3z" fill="#FFFFFF" />
            <Path d="M19 11a7 7 0 01-14 0M12 18v3" stroke="#FFFFFF" strokeWidth="1.8" strokeLinecap="round" fill="none" />
          </Svg>
        </TouchableOpacity>
      </Animated.View>
      <View style={{ flex: 0.3 }} />
      <View style={styles.bottomNav}>
        <View style={styles.navItem}>
          <Svg width={22} height={22} viewBox="0 0 24 24">
            <Rect x="2" y="9" width="3" height="6" rx="1.5" fill="#B14EFF" />
            <Rect x="7" y="5" width="3" height="14" rx="1.5" fill="#B14EFF" />
            <Rect x="12" y="2" width="3" height="20" rx="1.5" fill="#B14EFF" />
            <Rect x="17" y="7" width="3" height="10" rx="1.5" fill="#B14EFF" />
          </Svg>
          <Text style={styles.navLabelActive}>Listen</Text>
        </View>
        <TouchableOpacity style={styles.navItem} onPress={() => navigation.navigate('History')}>
          <Svg width={22} height={22} viewBox="0 0 24 24">
            <Circle cx="12" cy="12" r="9" stroke="#8A8691" strokeWidth="1.5" fill="none" />
            <Path d="M12 7v5l3 3" stroke="#8A8691" strokeWidth="1.5" strokeLinecap="round" fill="none" />
          </Svg>
          <Text style={styles.navLabelInactive}>History</Text>
        </TouchableOpacity>
      </View>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: { flex: 1, paddingHorizontal: 24, paddingTop: 60 },
  topRow: { flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center' },
  heading: { fontSize: 22, fontWeight: 'bold', color: '#FFFFFF', textAlign: 'center' },
  subheading: { fontSize: 14, color: '#9E9AA7', textAlign: 'center', marginTop: 6 },
  circleWrapper: { alignItems: 'center', justifyContent: 'center' },
  outerRing: { width: 260, height: 260, borderRadius: 130, borderWidth: 1.5, borderColor: '#7B2CBF', alignItems: 'center', justifyContent: 'center', backgroundColor: 'rgba(157, 78, 221, 0.06)' },
  micButton: { width: 70, height: 70, borderRadius: 35, backgroundColor: '#9D4EDD', alignItems: 'center', justifyContent: 'center' },
  micButtonActive: { backgroundColor: '#7B2CBF' },
  bottomNav: { flexDirection: 'row', justifyContent: 'space-around', paddingTop: 16, paddingBottom: 32, borderTopWidth: 1, borderTopColor: '#1E1626' },
  navItem: { alignItems: 'center' },
  navLabelActive: { color: '#B14EFF', fontSize: 12, marginTop: 4, fontWeight: '600' },
  navLabelInactive: { color: '#8A8691', fontSize: 12, marginTop: 4 },
});
