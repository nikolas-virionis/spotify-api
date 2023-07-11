import logging
import spotify_recommender_api.util as util

from spotify_recommender_api.model.song import Song
from spotify_recommender_api.playlist.base_playlist import BasePlaylist
from spotify_recommender_api.requests.api_handler import PlaylistHandler

class Playlist(BasePlaylist):

    def __init__(self, user_id: str, playlist_id: str) -> None:
        super().__init__(user_id, playlist_id)

    def __post_init__(self) -> None:
        return super().__post_init__()

    @staticmethod
    def get_song_count(playlist_id: str) -> int:
        return PlaylistHandler.get_playlist_total_song_count(playlist_id=playlist_id)

    @staticmethod
    def get_playlist_name(playlist_id: str) -> str:
        return util.get_base_playlist_name(playlist_id=playlist_id)

    def get_playlist_from_web(self) -> 'list[Song]':
        songs = []
        total_song_count = self.get_song_count(playlist_id=self.playlist_id)

        for offset in range(0, total_song_count, 100):
            logging.info(f'Songs mapped: {offset}/{total_song_count}')

            playlist_songs = PlaylistHandler.playlist_songs(playlist_id=self.playlist_id, limit=100, offset=offset)

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

