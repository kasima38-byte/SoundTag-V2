from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import requests
import os
import traceback
from datetime import datetime

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

AUDD_API_TOKEN = "test"
DB_PATH = "soundtag.db"


def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS songs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            artist TEXT,
            album TEXT,
            release_date TEXT,
            genre TEXT,
            spotify_url TEXT,
            preview_url TEXT,
            album_art TEXT,
            timestamp TEXT,
            is_favorite INTEGER DEFAULT 0
        )
    """)
    conn.commit()
    conn.close()


init_db()


@app.get("/")
def root():
    return {"status": "soundTag backend is running"}


@app.post("/recognize")
async def recognize_song(file: UploadFile = File(...)):
    try:
        audio_bytes = await file.read()
        print(f"Received audio file: {len(audio_bytes)} bytes")

        response = requests.post(
            "https://api.audd.io/",
            data={"api_token": AUDD_API_TOKEN, "return": "spotify,apple_music"},
            files={"file": audio_bytes},
        )
        result = response.json()
        print(f"AudD response: {result}")

        if result.get("status") != "success" or not result.get("result"):
            return {"found": False, "message": "No match found"}

        song = result["result"]
        title = song.get("title", "Unknown")
        artist = song.get("artist", "Unknown")
        album = song.get("album", "")
        release_date = song.get("release_date", "")
        genre = ""
        spotify_url = ""

        spotify_data = song.get("spotify")
        if spotify_data:
            spotify_url = spotify_data.get("external_urls", {}).get("spotify", "")

        preview_url = ""
        album_art = None
        apple_data = song.get("apple_music")
        if apple_data:
            preview_data = apple_data.get("previews", [])
            if preview_data:
                preview_url = preview_data[0].get("url", "")
            artwork = apple_data.get("artwork", {})
            if artwork:
                art_url = artwork.get("url", "")
                if art_url:
                    album_art = art_url.replace("{w}", "500").replace("{h}", "500")
            genre_names = apple_data.get("genreNames", [])
            if genre_names:
                genre = genre_names[0]

        # Fallback to Spotify data if Apple Music didn't have it
        if spotify_data:
            if not preview_url:
                preview_url = spotify_data.get("preview_url", "") or ""
            if not album_art:
                images = spotify_data.get("album", {}).get("images", [])
                if images:
                    album_art = images[0].get("url")

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO songs (title, artist, album, release_date, genre, spotify_url, preview_url, album_art, timestamp) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (title, artist, album, release_date, genre, spotify_url, preview_url, album_art, datetime.now().isoformat()),
        )
        conn.commit()
        song_id = cursor.lastrowid
        conn.close()

        return {
            "found": True,
            "song": {
                "id": song_id,
                "title": title,
                "artist": artist,
                "album": album,
                "year": release_date[:4] if release_date else "",
                "genre": genre or "-",
                "bpm": "-",
                "key": "-",
                "spotify_url": spotify_url,
                "albumArt": album_art,
                "previewUrl": preview_url,
            },
        }

    except Exception as e:
        print("=== ERROR IN /recognize ===")
        traceback.print_exc()
        print("=== END ERROR ===")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/history")
def get_history():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM songs ORDER BY timestamp DESC")
    rows = cursor.fetchall()
    conn.close()
    return {"songs": [dict(row) for row in rows]}


@app.post("/favorite/{song_id}")
def toggle_favorite(song_id: int):
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT is_favorite FROM songs WHERE id = ?", (song_id,))
    row = cursor.fetchone()
    if not row:
        conn.close()
        raise HTTPException(status_code=404, detail="Song not found")
    new_value = 0 if row[0] else 1
    cursor.execute("UPDATE songs SET is_favorite = ? WHERE id = ?", (new_value, song_id))
    conn.commit()
    conn.close()
    return {"is_favorite": bool(new_value)}