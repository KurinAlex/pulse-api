import os
from collections import Counter
from pathlib import Path
from typing import Annotated

import fastapi
import requests
from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Response,
    UploadFile,
    status,
)
from fastapi.responses import PlainTextResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from ytmusicapi import YTMusic

from src.models import HistoryItem, Song
from src.util import bytes_to_jpeg, save_to_jpeg

TMP_PATH = Path(__file__).parent / "tmp"
TMP_PATH.mkdir(exist_ok=True)
IMAGE_FILE = TMP_PATH / "image.jpg"

security = HTTPBearer()


def verify_token(
    credentials: Annotated[HTTPAuthorizationCredentials, Depends(security)],
):
    """
    Dependency function to validate the incoming API token.
    """
    token = credentials.credentials
    if token != os.getenv("API_TOKEN"):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing API Token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return token


app = FastAPI(dependencies=[Depends(verify_token)])


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


@app.get("/last-played", response_class=PlainTextResponse)
def get_last_played(client: YTMusicDep):
    history_data = client.get_history()
    if not history_data:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND, content="History not found"
        )

    song = HistoryItem.model_validate(history_data[0])
    response = f"{song.title}\n{song.artists_str}\n{song.duration}\n{song.videoId}"
    return response


@app.get("/played-today", response_class=PlainTextResponse)
def get_played_today(
    client: YTMusicDep, top: Annotated[int | None, fastapi.Query(ge=0)] = None
):
    history_data = client.get_history()
    history = [HistoryItem.model_validate(item) for item in history_data]
    today_songs = [item for item in history if item.played == "Today"]

    artists_counter = Counter()
    for song in today_songs:
        artists_counter.update([artist.name for artist in song.artists])

    if top is not None:
        top_artists = artists_counter.most_common(top)
        other_artists = artists_counter - Counter(dict(top_artists))
        other = sum(other_artists.values())

        artists_counter = Counter(dict(top_artists))
        if other > 0:
            artists_counter["Other"] = other

    artists_string = "\n".join(f"{a}\n{c}" for a, c in artists_counter.items())
    return f"{len(today_songs)}\n{artists_string}"


@app.get("/thumbnail/{video_id}")
def get_thumbnail(
    client: YTMusicDep,
    video_id: Annotated[str, fastapi.Path(min_length=1)],
    width: Annotated[int | None, fastapi.Query(gt=0, le=2000)] = None,
    height: Annotated[int | None, fastapi.Query(gt=0, le=2000)] = None,
):
    song_data = client.get_song(video_id)
    song = Song.model_validate(song_data)
    thumbnails = song.videoDetails.thumbnail.thumbnails
    if not thumbnails:
        return Response(
            status_code=status.HTTP_404_NOT_FOUND, content="Thumbnail not found"
        )

    url = max(thumbnails, key=lambda t: t.width).url
    response = requests.get(url)
    if response.status_code != status.HTTP_200_OK:
        return Response(
            status_code=status.HTTP_502_BAD_GATEWAY, content="Failed to fetch thumbnail"
        )

    image_data = bytes_to_jpeg(response.content, width, height)
    return Response(
        content=image_data,
        media_type="image/jpeg",
    )


@app.get("/picture")
def get_picture(
    width: Annotated[int | None, fastapi.Query(gt=0, le=2000)] = None,
    height: Annotated[int | None, fastapi.Query(gt=0, le=2000)] = None,
):
    if not IMAGE_FILE.exists():
        return Response(
            status_code=status.HTTP_404_NOT_FOUND, content="Image not found"
        )

    image_data = bytes_to_jpeg(IMAGE_FILE.read_bytes(), width, height)
    return Response(
        content=image_data,
        media_type="image/jpeg",
    )


@app.post("/picture")
async def upload_picture(file: UploadFile):
    if file.content_type not in [
        "image/jpeg",
        "image/png",
        "image/jpg",
        "image/webp",
        "image/bmp",
        "image/tiff",
    ]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file type. Only JPEG and PNG are allowed.",
        )

    save_to_jpeg(file.file, IMAGE_FILE)
    return Response(
        status_code=status.HTTP_201_CREATED, content="Image uploaded successfully"
    )
