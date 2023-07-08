import logging

from spotify_recommender_api.model.song import Song
from spotify_recommender_api.request_handler import RequestHandler, BASE_URL
from spotify_recommender_api.model.playlist.base_playlist import BasePlaylist

class Playlist(BasePlaylist):

    @staticmethod
    def get_song_count(playlist_id: str) -> int:
        playlist_res = RequestHandler.get_request(url=f'{BASE_URL}/playlists/{playlist_id}')

        return playlist_res.json()["tracks"]["total"]

    @staticmethod
    def get_playlist_name(playlist_id: str) -> str:
        playlist = RequestHandler.get_request(url=f'{BASE_URL}/playlists/{playlist_id}').json()

        return playlist['name']


    def get_playlist_from_web(self) -> 'list[Song]':
        songs = []
        total_song_count = self.get_song_count(playlist_id=self.playlist_id)

        for offset in range(0, total_song_count, 100):
            logging.info(f'Songs mapped: {offset}/{total_song_count}')

            playlist_songs = RequestHandler.get_request(url=f'{BASE_URL}/playlists/{self.playlist_id}/tracks?limit=100&{offset=!s}')

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

