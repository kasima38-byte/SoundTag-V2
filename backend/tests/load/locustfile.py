"""
Load test for SoundTag's recognition pipeline using Locust.

Run with:
    locust -f locustfile.py --host=http://localhost:8000

Then open http://localhost:8089 to configure concurrent users and ramp-up.

This simulates the real-world load pattern: bursts of concurrent
/recognize calls, occasional /history and /favorites reads, mimicking
a mobile app's actual traffic shape rather than hammering one endpoint.
"""
import io
import random

import numpy as np
import soundfile as sf
from locust import HttpUser, task, between, events


def generate_test_clip(duration=7.0, sr=22050) -> bytes:
    """Generate a synthetic audio clip to simulate a recognition query.
    Mixes a few sine tones to create a more complex spectrum than a pure tone,
    closer to what real music produces."""
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    freqs = random.sample([220, 330, 440, 550, 660, 880], k=3)
    signal = sum(0.3 * np.sin(2 * np.pi * f * t) for f in freqs)
    signal += np.random.normal(0, 0.02, signal.shape)  # light noise floor
    buf = io.BytesIO()
    sf.write(buf, signal.astype(np.float32), sr, format="WAV")
    return buf.getvalue()


# Pre-generate a small pool of clips so we're not doing CPU-heavy
# synthesis on every single request during the load test itself.
CLIP_POOL = [generate_test_clip() for _ in range(10)]


class SoundTagUser(HttpUser):
    wait_time = between(2, 8)  # mimics real users pausing between identifications

    def on_start(self):
        self.token = None
        # 30% of simulated users are logged in
        if random.random() < 0.3:
            self._register_and_login()

    def _register_and_login(self):
        suffix = random.randint(100000, 999999)
        email = f"loadtest{suffix}@example.com"
        password = "loadtest12345"
        self.client.post("/auth/register", json={
            "email": email,
            "username": f"loadtest{suffix}",
            "password": password,
        })
        resp = self.client.post("/auth/login", json={"email": email, "password": password})
        if resp.status_code == 200:
            self.token = resp.json()["access_token"]

    def _auth_headers(self):
        return {"Authorization": f"Bearer {self.token}"} if self.token else {}

    @task(10)
    def recognize_song(self):
        clip = random.choice(CLIP_POOL)
        self.client.post(
            "/recognize",
            files={"file": ("clip.wav", clip, "audio/wav")},
            headers=self._auth_headers(),
            name="/recognize",
        )

    @task(2)
    def view_history(self):
        if self.token:
            self.client.get("/history", headers=self._auth_headers(), name="/history")

    @task(1)
    def view_favorites(self):
        if self.token:
            self.client.get("/favorites", headers=self._auth_headers(), name="/favorites")

    @task(1)
    def health_check(self):
        self.client.get("/health", name="/health")


@events.test_start.add_listener
def on_test_start(environment, **kwargs):
    print("=" * 60)
    print("SoundTag Load Test Starting")
    print("Target: recognition under 3s @ p95, even at peak concurrency")
    print("=" * 60)


@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    stats = environment.stats.get("/recognize", "POST")
    if stats:
        print("\n--- /recognize summary ---")
        print(f"Requests: {stats.num_requests}")
        print(f"Failures: {stats.num_failures}")
        print(f"p50: {stats.get_response_time_percentile(0.5)}ms")
        print(f"p95: {stats.get_response_time_percentile(0.95)}ms")
        print(f"p99: {stats.get_response_time_percentile(0.99)}ms")
        target_met = stats.get_response_time_percentile(0.95) < 3000
        print(f"\n3-second p95 target: {'PASS' if target_met else 'FAIL'}")
