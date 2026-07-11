import React from 'react';
import { View, Text, StyleSheet, TouchableOpacity, Dimensions } from 'react-native';
import { LinearGradient } from 'expo-linear-gradient';
import Svg, { Path, Rect } from 'react-native-svg';

const { width } = Dimensions.get('window');

export default function WelcomeScreen({ navigation }) {
  return (
    <LinearGradient
      colors={['#0D0710', '#150A1F', '#0D0710']}
      style={styles.container}
    >
      {/* Soundwave Icon */}
      <View style={styles.iconContainer}>
        <Svg width={90} height={70} viewBox="0 0 90 70">
          <Rect x="5" y="25" width="8" height="20" rx="4" fill="#9D4EDD" />
          <Rect x="20" y="15" width="8" height="40" rx="4" fill="#B14EFF" />
          <Rect x="35" y="0" width="8" height="70" rx="4" fill="#C77DFF" />
          <Rect x="50" y="10" width="8" height="50" rx="4" fill="#9D4EDD" />
          <Rect x="65" y="22" width="8" height="26" rx="4" fill="#7B2CBF" />
          <Rect x="80" y="30" width="8" height="10" rx="4" fill="#5A189A" />
        </Svg>
      </View>

      {/* App Name */}
      <View style={styles.titleRow}>
        <Text style={styles.titleWhite}>sound</Text>
        <Text style={styles.titlePurple}>Tag</Text>
      </View>

      {/* Tagline */}
      <View style={styles.taglineContainer}>
        <Text style={styles.taglineWhite}>Tag the sound.</Text>
        <Text style={styles.taglinePurple}>Find the moment.</Text>
      </View>

      {/* Subtitle */}
      <Text style={styles.subtitle}>
        Identify songs playing around you instantly and save them for later.
      </Text>

      {/* Spacer */}
      <View style={{ flex: 1 }} />

      {/* Decorative flowing wave lines */}
      <View style={styles.waveContainer}>
        <Svg width={width - 40} height={100} viewBox="0 0 335 100">
          <Path
            d="M0,50 Q40,10 80,50 T160,50 T240,50 T320,50"
            stroke="#7B2CBF"
            strokeWidth="2"
            fill="none"
            opacity="0.5"
          />
          <Path
            d="M0,60 Q40,25 80,60 T160,60 T240,60 T320,60"
            stroke="#9D4EDD"
            strokeWidth="2"
            fill="none"
            opacity="0.7"
          />
          <Path
            d="M0,70 Q40,40 80,70 T160,70 T240,70 T320,70"
            stroke="#C77DFF"
            strokeWidth="2"
            fill="none"
            opacity="0.4"
          />
        </Svg>
      </View>

      {/* Buttons */}
      <TouchableOpacity style={styles.getStartedButton} onPress={() => navigation?.navigate('Listen')}>
        <Text style={styles.getStartedText}>Get Started</Text>
      </TouchableOpacity>

      <TouchableOpacity style={styles.loginButton}>
        <Text style={styles.loginText}>Log In</Text>
      </TouchableOpacity>

      <Text style={styles.fineprint}>
        By continuing, you agree to our{' '}
        <Text style={styles.link}>Terms of Service</Text> and{' '}
        <Text style={styles.link}>Privacy Policy</Text>.
      </Text>
    </LinearGradient>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
    paddingHorizontal: 24,
    paddingTop: 100,
    paddingBottom: 40,
    alignItems: 'center',
  },
  iconContainer: {
    marginBottom: 20,
  },
  titleRow: {
    flexDirection: 'row',
    marginBottom: 24,
  },
  titleWhite: {
    fontSize: 40,
    fontWeight: 'bold',
    color: '#FFFFFF',
  },
  titlePurple: {
    fontSize: 40,
    fontWeight: 'bold',
    color: '#B14EFF',
  },
  taglineContainer: {
    alignItems: 'center',
    marginBottom: 16,
  },
  taglineWhite: {
    fontSize: 26,
    fontWeight: '600',
    color: '#FFFFFF',
    textAlign: 'center',
  },
  taglinePurple: {
    fontSize: 26,
    fontWeight: '600',
    color: '#B14EFF',
    textAlign: 'center',
  },
  subtitle: {
    fontSize: 14,
    color: '#9E9AA7',
    textAlign: 'center',
    paddingHorizontal: 20,
    lineHeight: 20,
  },
  waveContainer: {
    marginBottom: 20,
  },
  getStartedButton: {
    backgroundColor: '#9D4EDD',
    width: width - 48,
    paddingVertical: 16,
    borderRadius: 30,
    alignItems: 'center',
    marginBottom: 12,
  },
  getStartedText: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: 'bold',
  },
  loginButton: {
    backgroundColor: '#1E1626',
    width: width - 48,
    paddingVertical: 16,
    borderRadius: 30,
    alignItems: 'center',
    marginBottom: 20,
  },
  loginText: {
    color: '#FFFFFF',
    fontSize: 17,
    fontWeight: '600',
  },
  fineprint: {
    fontSize: 12,
    color: '#8A8691',
    textAlign: 'center',
    paddingHorizontal: 10,
  },
  link: {
    color: '#B14EFF',
    textDecorationLine: 'underline',
  },
});