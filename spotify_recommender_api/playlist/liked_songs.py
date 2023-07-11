import logging

from typing import Union
from spotify_recommender_api.model.song import Song
from spotify_recommender_api.requests.api_handler import APIHandler
from spotify_recommender_api.playlist.base_playlist import BasePlaylist

class LikedSongs(BasePlaylist):

    def __init__(self, user_id: str) -> None:
        super().__init__(f"{self.user_id}'s Liked Songs")
        self.user_id = user_id

    def __post_init__(self) -> None:
        super().__post_init__()
        self.playlist_name = f"{self.user_id}'s Liked Songs"

    @staticmethod
    def get_song_count(playlist_id: Union[str, None] = None) -> int:
        return APIHandler.get_liked_songs_count()

    @staticmethod
    def get_playlist_name(playlist_id: Union[str, None] = None) -> str:
        return "User's Liked Songs"


    def get_playlist_from_web(self) -> 'list[Song]':
        songs = []
        total_song_count = self.get_song_count()

        for offset in range(0, total_song_count, 50):
            logging.info(f'Songs mapped: {offset}/{total_song_count}')

            playlist_songs = APIHandler.liked_songs(limit=50, offset=offset)

            for song in playlist_songs.json()["items"]:
                song_id, name, popularity, artists, added_at = Song.song_data(song=song)

                song_genres = Song.get_song_genres(artists=artists)

                danceability, loudness, energy, instrumentalness, tempo, valence = Song.query_audio_features(song_id=song_id)

                songs.append(
                    Song(
                        name=name,
                        id=song_id,
                        tempo=tempo,
                        energy=energy,
                        valence=valence,
                        added_at=added_at,
                        loudness=loudness,
                        genres=song_genres,
                        popularity=popularity,
                        danceability=danceability,
                        instrumentalness=instrumentalness,
                        artists=[artist.name for artist in artists],
                    )
                )

        logging.info(f'Songs mapping complete: {total_song_count}/{total_song_count}')

        return songs
