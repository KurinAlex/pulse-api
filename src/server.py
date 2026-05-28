import os
from collections import Counter
from typing import Annotated

import requests
from fastapi import Depends, FastAPI, Path, Query, Response
from ytmusicapi import YTMusic

from models import HistoryItem, Song
from util import bytes_to_jpeg

app = FastAPI()


def ytmusic_client() -> YTMusic:
    auth = {
        "accept": "*/*",
        "authorization": os.getenv("YT_AUTHORIZATION"),
        "cookie": os.getenv("YT_COOKIE"),
        "content-type": "application/json",
        "x-goog-authuser": "0",
        "x-origin": "https://music.youtube.com",
    }
    return YTMusic(auth)


YTMusicDep = Annotated[YTMusic, Depends(ytmusic_client)]


@app.get("/last-played")
def get_last_played(client: YTMusicDep):
    history_data = client.get_history()
    if not history_data:
        return {"error": "No history found"}

    song = HistoryItem.model_validate(history_data[0])

    data = {
        "title": song.title,
        "artist": song.artists_str,
        "duration": song.duration,
        "videoId": song.videoId,
    }
    return data


@app.get("/played-today")
def get_played_today(
    client: YTMusicDep, top: Annotated[int | None, Query(ge=0)] = None
):
    history_data = client.get_history()
    history = [HistoryItem.model_validate(item) for item in history_data]
    today_songs = [item for item in history if item.played == "Today"]

    artists_counter = Counter()
    for song in today_songs:
        artists_counter.update([artist.name for artist in song.artists])

    if top is not None:
        top_artists = artists_counter.most_common(top)
        other_artists = (artists_counter - Counter(dict(top_artists)))
        other = sum(other_artists.values())

        artists_counter = Counter(dict(top_artists))
        if other > 0:
            artists_counter["Other"] = other

    return {"total_count": len(today_songs), "artists_count": artists_counter}


@app.get("/thumbnail/{video_id}")
def get_thumbnail(
    client: YTMusicDep,
    video_id: Annotated[str, Path(min_length=1)],
    width: Annotated[int | None, Query(gt=0, le=2000)] = None,
    height: Annotated[int | None, Query(gt=0, le=2000)] = None,
):
    song_data = client.get_song(video_id)
    song = Song.model_validate(song_data)
    thumbnails = song.videoDetails.thumbnail.thumbnails
    if not thumbnails:
        return Response(status_code=404, content="Thumbnail not found")

    url = max(thumbnails, key=lambda t: t.width).url
    response = requests.get(url)
    if response.status_code != 200:
        return Response(status_code=502, content="Failed to fetch thumbnail")

    image_data = bytes_to_jpeg(response.content, width, height)
    return Response(
        content=image_data,
        media_type=response.headers.get("content-type", "image/jpeg"),
    )
