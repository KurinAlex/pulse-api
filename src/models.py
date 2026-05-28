from pydantic import BaseModel, computed_field


class Artist(BaseModel):
    name: str


class Thumbnail(BaseModel):
    url: str
    width: int
    height: int


class Thumbnails(BaseModel):
    thumbnails: list[Thumbnail]


class VideoDetails(BaseModel):
    thumbnail: Thumbnails


class Song(BaseModel):
    videoDetails: VideoDetails


class HistoryItem(BaseModel):
    videoId: str
    title: str
    artists: list[Artist]
    duration_seconds: int
    played: str

    @computed_field
    @property
    def duration(self) -> str:
        minutes = self.duration_seconds // 60
        seconds = self.duration_seconds % 60
        return f"{minutes}:{seconds:02d}"

    @computed_field
    @property
    def artists_str(self) -> str:
        return ", ".join(artist.name for artist in self.artists)
