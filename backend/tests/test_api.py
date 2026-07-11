"""
Integration tests for the API endpoints.
Uses httpx AsyncClient against the FastAPI app with a test database.
"""
import io
import pytest
import soundfile as sf
import numpy as np
from httpx import AsyncClient, ASGITransport

from app.main import app


def make_wav_bytes(freq=440.0, duration=6.0, sr=22050) -> bytes:
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    signal = 0.5 * np.sin(2 * np.pi * freq * t)
    buf = io.BytesIO()
    sf.write(buf, signal.astype(np.float32), sr, format="WAV")
    return buf.getvalue()


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


class TestHealthCheck:
    @pytest.mark.asyncio
    async def test_health_returns_ok(self, client):
        resp = await client.get("/health")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ok"


class TestAuthFlow:
    @pytest.mark.asyncio
    async def test_register_and_login(self, client):
        register_resp = await client.post("/auth/register", json={
            "email": "test@example.com",
            "username": "testuser",
            "password": "supersecret123",
        })
        assert register_resp.status_code in (201, 409)  # 409 if re-run

        login_resp = await client.post("/auth/login", json={
            "email": "test@example.com",
            "password": "supersecret123",
        })
        assert login_resp.status_code == 200
        body = login_resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    @pytest.mark.asyncio
    async def test_login_with_wrong_password_fails(self, client):
        resp = await client.post("/auth/login", json={
            "email": "nonexistent@example.com",
            "password": "wrongpassword",
        })
        assert resp.status_code == 401


class TestSongIngestion:
    @pytest.mark.asyncio
    async def test_create_song_with_audio(self, client):
        wav_bytes = make_wav_bytes(freq=523.25, duration=8.0)
        resp = await client.post(
            "/songs",
            data={
                "title": "Test Song",
                "artist": "Test Artist",
                "album": "Test Album",
                "release_year": "2024",
            },
            files={"audio_file": ("song.wav", wav_bytes, "audio/wav")},
        )
        assert resp.status_code == 201
        body = resp.json()
        assert body["title"] == "Test Song"
        assert body["fingerprint_count"] > 0
        return body["id"]

    @pytest.mark.asyncio
    async def test_create_song_rejects_empty_audio(self, client):
        resp = await client.post(
            "/songs",
            data={"title": "Empty", "artist": "Nobody"},
            files={"audio_file": ("empty.wav", b"", "audio/wav")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_get_nonexistent_song_404(self, client):
        resp = await client.get("/songs/00000000-0000-0000-0000-000000000000")
        assert resp.status_code == 404


class TestRecognition:
    @pytest.mark.asyncio
    async def test_recognize_with_no_matching_song(self, client):
        wav_bytes = make_wav_bytes(freq=999.0, duration=6.0)
        resp = await client.post(
            "/recognize",
            files={"file": ("clip.wav", wav_bytes, "audio/wav")},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "matched" in body

    @pytest.mark.asyncio
    async def test_recognize_rejects_unsupported_content_type(self, client):
        resp = await client.post(
            "/recognize",
            files={"file": ("clip.txt", b"not audio", "text/plain")},
        )
        assert resp.status_code == 415

    @pytest.mark.asyncio
    async def test_recognize_rejects_empty_file(self, client):
        resp = await client.post(
            "/recognize",
            files={"file": ("clip.wav", b"", "audio/wav")},
        )
        assert resp.status_code == 400

    @pytest.mark.asyncio
    async def test_full_ingest_then_recognize_flow(self, client):
        """End-to-end: ingest a song, then recognize an excerpt of it."""
        sr = 22050
        freq = 392.0
        full_audio = 0.5 * np.sin(
            2 * np.pi * freq * np.linspace(0, 12, sr * 12, endpoint=False)
        )
        buf_full = io.BytesIO()
        sf.write(buf_full, full_audio.astype(np.float32), sr, format="WAV")

        ingest_resp = await client.post(
            "/songs",
            data={"title": "E2E Song", "artist": "E2E Artist"},
            files={"audio_file": ("full.wav", buf_full.getvalue(), "audio/wav")},
        )
        assert ingest_resp.status_code == 201

        excerpt = full_audio[sr * 3 : sr * 9]
        buf_excerpt = io.BytesIO()
        sf.write(buf_excerpt, excerpt.astype(np.float32), sr, format="WAV")

        recognize_resp = await client.post(
            "/recognize",
            files={"file": ("excerpt.wav", buf_excerpt.getvalue(), "audio/wav")},
        )
        assert recognize_resp.status_code == 200
        body = recognize_resp.json()
        assert body["matched"] is True
        assert body["song"]["title"] == "E2E Song"


class TestFavoritesRequireAuth:
    @pytest.mark.asyncio
    async def test_add_favorite_without_auth_fails(self, client):
        resp = await client.post(
            "/favorites",
            json={"song_id": "00000000-0000-0000-0000-000000000000"},
        )
        assert resp.status_code == 401

    @pytest.mark.asyncio
    async def test_get_favorites_without_auth_fails(self, client):
        resp = await client.get("/favorites")
        assert resp.status_code == 401


class TestHistoryRequiresAuth:
    @pytest.mark.asyncio
    async def test_get_history_without_auth_fails(self, client):
        resp = await client.get("/history")
        assert resp.status_code == 401
