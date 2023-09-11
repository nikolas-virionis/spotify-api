from spotify_recommender_api.song.song import Song


class SongUtil:
    """Class for utility methods regarding song operations"""

    @staticmethod
    def _build_song_objects(recommendations: dict, dict_key: str = 'tracks') -> 'list[Song]':
        """Builds a list of Song objects from the recommendations data.

        Args:
            recommendations (dict): Recommendations data.
            dict_key (str, optional): Key to access the song data in the recommendations dictionary. Defaults to 'tracks'.

        Returns:
            list[Song]: List of Song objects.
        """
        songs = []

        for song in recommendations[dict_key]:
            song_id, name, popularity, artists, _ = Song.song_data(song=song)
            song_genres = Song.get_song_genres(artists=artists)

            danceability, loudness, energy, instrumentalness, tempo, valence = Song.query_audio_features(song_id=song_id)

            vader_sentiment_analysis = Song.vader_sentiment_analysis(song_name=name, artist_name=artists[0].name)

            songs.append(
                Song(
                    name=name,
                    id=song_id,
                    tempo=tempo,
                    energy=energy,
                    valence=valence,
                    loudness=loudness,
                    genres=song_genres,
                    popularity=popularity,
                    danceability=danceability,
                    instrumentalness=instrumentalness,
                    lyrics=vader_sentiment_analysis['lyrics'],
                    artists=[artist.name for artist in artists],
                    vader_sentiment=vader_sentiment_analysis['vader_sentiment'],
                )
            )

        return songs
