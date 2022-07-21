import os
import re
import operator
import datetime
import pandas as pd
import seaborn as sns
from dateutil import tz
from functools import reduce
import matplotlib.pyplot as plt
import spotify_recommender_api.util as util
from spotify_recommender_api.sensitive import *
from spotify_recommender_api.authentication import get_auth
pd.options.mode.chained_assignment = None
sns.set()

class SpotifyAPI:
    """
    ### Spotify API is the Class that provides access to the playlists recommendations
    """

    def __get_playlist_from_csv(self):
        """
        Function that creates the playlist variable from a CSV file previouusly created by this same API

        """
        df = pd.read_parquet('./.spotify-recommender-util/util.parquet')

        self.__artists, self.__songs, self.__all_genres = list(map(lambda arr: arr if type(
            arr) != 'str' else eval(arr), [df['artists'][0], df['songs'][0], df['all_genres'][0]]))

        self.__playlist = pd.read_csv('playlist.csv')

    def __get_playlist(self):
        """
        General purpose function to get the playlist, either from CSV or web requests

        """
        answer = input(
            'Do you want to get the playlist data via CSV saved previously or read from spotify, *which will take a few minutes* depending on the playlist size (csv/web)? ')
        while answer.lower() not in ['csv', 'web', 'parquet']:
            answer = input("Please select a valid response: ")
        if answer.lower() == 'csv':
            self.__get_playlist_from_csv()
            return False

        return True

    def __get_song_genres(self, song):
        """
        Function that gets all the genres for a given song

        Parameters:
          song: the song dictionary
        """
        genres = []
        song_artists = song["track"]["artists"] if 'track' in list(song.keys()) else song["artists"]
        for artist in song_artists:
            id = artist["id"]
            if id not in self.__artists:
                artist_genres_res = util.get_request(url=f'https://api.spotify.com/v1/artists/{id}', headers=self.__headers)
                try:
                    artist_genres = artist_genres_res.json()["genres"]
                except Exception as e:
                    print(f'{e = }')
                    print(artist_genres_res.json())
                genres = util.add_items_to_list(items=genres, item_list=artist_genres)
                self.__artists[artist["name"]] = artist_genres
            else:
                genres = util.add_items_to_list(items=genres, item_list=self.__artists[id])

        return genres

    def __get_playlist_items(self):
        """
        Function that gets the items (songs) inside the playlist

        # Note
        Ran automatically but can last as long as 2.5 seconds for each song (can be worse depending on the network connection) inside of te playlist, not because it is compute demanding but because it needs to do a up to a bunch of http requests per song, which can take a while

        """
        self.__all_genres = []
        try:
            for offset in range(0, util.get_total_song_count(playlist_id=self.__playlist_id, headers=self.__headers), 100):
                all_genres_res = util.get_request(
                    headers=self.__headers,
                    url=f'https://api.spotify.com/v1/playlists/{self.__playlist_id}/tracks?limit=100&{offset=}'
                )
                for song in all_genres_res.json()["items"]:
                    (id, name, popularity, artist, added_at), song_genres = util.song_data(song=song), self.__get_song_genres(song)
                    song['id'] = id
                    danceability, energy, instrumentalness, tempo, valence = self.__query_audio_features(song=song)
                    self.__songs.append({
                        "id": id,
                        "name": name,
                        "artists": artist,
                        "popularity": popularity,
                        "genres": song_genres,
                        "added_at": added_at,
                        "danceability": danceability,
                        "energy": energy,
                        "instrumentalness": instrumentalness,
                        "tempo": tempo,
                        "valence": valence
                    })
                    self.__all_genres = util.add_items_to_list(items=song_genres, item_list=self.__all_genres)
        except KeyError:
            raise ValueError('Invalid Auth Token, try again with a valid one')

    def __playlist_adjustments(self):
        """
        Function that does a bunch of adjustments to the overall formatting of the playlist, before making it visible

        """
        try:
            songs = self.__songs[-util.get_total_song_count(playlist_id=self.__playlist_id, headers=self.__headers):]
        except KeyError:
            raise ValueError('Invalid Auth Token, try again with a valid one')
        self.__all_artists = list(self.__artists.keys())
        playlist = pd.DataFrame(data=list(songs))

        playlist["genres_indexed"] = [util.item_list_indexed(items=eval(playlist["genres"][x]) if type(
            playlist["genres"][x]) == 'str' else playlist["genres"][x], all_items=self.__all_genres) for x in range(len(playlist["genres"]))]
        playlist["artists_indexed"] = [util.item_list_indexed(items=eval(playlist["artists"][x]) if type(
            playlist["artists"][x]) == 'str' else playlist["artists"][x], all_items=self.__all_artists) for x in range(len(playlist["artists"]))]
        playlist['id'] = playlist["id"].astype(str)
        playlist['name'] = playlist["name"].astype(str)
        playlist['popularity'] = playlist["popularity"].astype(int)
        playlist['added_at'] = pd.to_datetime(playlist["added_at"])
        playlist['danceability'] = playlist["danceability"].astype(float)
        playlist['energy'] = playlist["energy"].astype(float)
        playlist['instrumentalness'] = playlist["instrumentalness"].astype(float)
        playlist['tempo'] = playlist["tempo"].astype(float)
        playlist['valence'] = playlist["valence"].astype(float)
        self.__playlist = playlist


    def __query_audio_features(self, song: pd.Series) -> 'list[float]':
        """Queries the audio features for a given song and returns the ones that match the recommendations within this package

        Args:
            song (pd.Series): song containing its base information

        Returns:
            list[float]: list with the audio features for the given song
        """

        id = song['id']

        audio_features = util.get_request(
            url=f'https://api.spotify.com/v1/audio-features/{id}',
            headers=self.__headers
        ).json()

        return [audio_features['danceability'], audio_features['energy'], audio_features['instrumentalness'], audio_features['tempo'], audio_features['valence']]


    def __init__(self, auth_token, user_id, playlist_id=None, playlist_url=None):
        """
        # Spotify API is the Class that provides access to the playlists recommendations

        # Parameters
        - auth_token: The authentication token for the Spotify API, base64 encoded string that allows the use of the API's functionalities
        - playlist_id: The playlist ID hash in Spotify
        - playlist_url: The url used while sharing the playlist
        - user_id: The user ID, visible in the Spotify profile account settings

        # It will trigger most of the API functions and can take a good while to complete
        """
        if not auth_token:
            raise ValueError('auth_token is required')
        self.__user_id = user_id
        self.__auth_token = auth_token
        self.__headers = {
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "Authorization": self.__auth_token
                    }
        self.__artists = {}
        self.__songs = []
        self.__deny_favorites = False

        if playlist_id:
            self.__playlist_id = playlist_id
        else:
            if not playlist_url:
                raise ValueError(
                    'Either the playlist url or its id must be specified')
            self.__playlist_id = util.playlist_url_to_id(url=playlist_url)
            self.__playlist_url = playlist_url

        if self.__get_playlist():
            self.__get_playlist_items()

        self.__playlist_adjustments()

        self.__knn_prepared_data()
        self.__prepare_favorites_playlist()

    def playlist_to_csv(self):
        """
        # Function to convert playlist to CSV format
        # Really useful if the package is being used in a .py file since it is not worth it to use it directly through web requests everytime even more when the playlist has not changed since last package usage
        """
        if not os.path.exists('./.spotify-recommender-util'):
            os.mkdir('./.spotify-recommender-util')
        df = pd.DataFrame(data=[{'artists': self.__artists, 'songs': self.__songs,
                        'all_genres': self.__all_genres}], columns=['artists', 'songs', 'all_genres'])

        df.to_parquet('./.spotify-recommender-util/util.parquet')

        playlist = self.__playlist[['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'energy', 'instrumentalness', 'tempo', 'valence']]

        playlist.to_csv('playlist.csv')

    def __knn_prepared_data(self):
        """
        Function to prepare the data for the algorithm which calculates the distances between the songs

        # Note
        It will make a copy of the playlist to a list, to avoid changing the original DataFrame playlist
        And also leave it in an easier to iterate over format
        """
        data = self.__playlist[
            [
                'id',
                'name',
                'genres',
                'artists',
                'popularity',
                'added_at',
                'danceability',
                'energy',
                'instrumentalness',
                'tempo',
                'valence',
                'genres_indexed',
                'artists_indexed'
            ]
        ]

        array = []

        for (
            id,
            name,
            genres,
            artists,
            popularity,
            added_at,
            danceability,
            energy,
            instrumentalness,
            tempo,
            valence,
            genres_indexed,
            artists_indexed
        ) in zip(
            data['id'],
            data['name'],
            data['genres'],
            data['artists'],
            data['popularity'],
            data['added_at'],
            data['danceability'],
            data['energy'],
            data['instrumentalness'],
            data['tempo'],
            data['valence'],
            data['genres_indexed'],
            data['artists_indexed']
        ):
            array.append(
                {
                    'id': id,
                    'name': name,
                    'genres': genres,
                    'artists': artists,
                    'popularity': popularity,
                    'added_at': added_at,
                    'danceability': danceability,
                    'energy': energy,
                    'instrumentalness': instrumentalness,
                    'tempo': tempo,
                    'valence': valence,
                    'genres_indexed': genres_indexed,
                    'artists_indexed': artists_indexed
                }
            )

        self.__song_dict = array

    def __get_neighbors(self, song: str, K: int, song_dict: list, type: str = None):
        """
        Function thats using the distance calculated above, returns the K nearest neighbors for a given song


        # Parameters
         - song: song's index in the songs list
         - K: desired number K of neighbors to be returned
         - song_dict: the list of songs
        """
        distances = []

        for song_index, song_value in enumerate(song_dict):
            if song_index != song:
                dist = util.compute_distance(a=song_dict[song], b=song_value, artist_recommendation='artist' in type)
                distances.append((song_index, dist))

        distances.sort(key=operator.itemgetter(1))
        neighbors = []
        for x in range(K):
            neighbors.append([*distances[x]])

        return neighbors

    def __get_index_for_song(self, song):
        """
        Function that returns the index of a given song in the list of songs

        # Parameters
         - song: song name
        """
        if song not in list(self.__playlist['name']):
            # print(self.__playlist['name'])
            raise ValueError(f'Playlist does not contain the song {song!r}')
        item = self.__playlist[[self.__playlist['name'][x] ==
                                song for x in range(len(self.__playlist['name']))]]
        index = item.index[0]
        return index


    def __build_playlist(self, type: str, uris: str):
        """Function that builds the contents of a playlist

        Note:
        This function will change the user's library by filling the previously created empty playlist

        Args:
            type (str): the type of the playlist being created
            uris (str): string containing all song uris in the format the Spotify API expects
        """
        add_songs_req = util.post_request(url=f'https://api.spotify.com/v1/playlists/{util.create_playlist(type=type, headers=self.__headers, user_id=self.__user_id, additional_info=self.__song_name if type == "song" else self.__artist_name if "artist" in type else None)}/tracks?{uris=!s}', headers=self.__headers, data={})
        add_songs_req.json()

    def __write_playlist(self, type, K, additional_info=None):
        """
        Function that writes a new playlist with the recommendations for the given type
        type: the type of the playlist being created ('song', 'short', 'medium'):
         - 'song': a playlist related to a song
         - 'short': a playlist related to the short term favorites for that given user
         - 'medium': a playlist related to the medium term favorites for that given user

        # Note:
        This function will change the user's library by either creating a new plalylist or overriding the existing one

        # Parameters
         - type: the type of the playlist being created
         - K: desired number K of neighbors to be returned
         - additional_info (optional): the song name when the type is 'song'


        """
        if K > 99 and all([x not in type for x in ['most-listened', 'artist']]):
            print('K limit exceded. Maximum value for K is 99')
            K = 99
        elif K < 1:
            raise ValueError('Value for K must be between 1 and 99')
        uris = ''
        if type == 'song':
            index = self.__get_index_for_song(additional_info)
            uris = f'spotify:track:{self.__song_dict[index]["id"]}'
            for neighbor in self.__get_recommendations('song', additional_info, K)['id']:
                uris += f',spotify:track:{neighbor}'

        elif type in ['medium', 'short']:
            ids = self.__medium_fav['id'] if type == 'medium' else self.__short_fav['id']
            for neighbor in ids:
                uris += f',spotify:track:{neighbor}'

            uris = uris[1:]

        elif any([x in type for x in ['most-listened', 'artist']]):
            ids = additional_info
            for song in ids:
                uris += f',spotify:track:{song}'

            uris = uris[1:]

        else:
            raise ValueError('Invalid type')

        self.__build_playlist(type=type, uris=uris)

    def get_recommendations_for_song(
            self,
            K: int,
            song: str,
            generate_csv: bool = False,
            with_distance: bool = False,
            build_playlist: bool = False,
            generate_parquet: bool = False,
            print_base_caracteristics: bool = False
        ) -> pd.DataFrame:
        """
        Playlist which centralises the actions for a recommendation made for a given song

        # Parameters
         - song(str): The desired song name
         - K(int): desired number K of neighbors to be returned
         - with_distance (bool): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the closet songs
         - generate_csv (bool): Whether to generate a CSV file containing the recommended playlist
         - generate_parquet (bool): Whether to generate a parquet file containing the recommended playlist
         - build_playlist (bool): Whether to build the playlist to the user's library
         - print_base_caracteristics (bool): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm

        # Note
        The build_playlist option when set to True will change the user's library

        """
        try:
            if K > 99:
                print('K limit exceded. Maximum value for K is 99')
                K = 99
            elif K < 1:
                raise ValueError('Value for K must be between 1 and 99')

            self.__song_name = song
            df = self.__get_recommendations('song', song, K)
            playlist_name = f'{song} Related'

            if print_base_caracteristics:
                index = self.__get_index_for_song(song)
                caracteristics = self.__song_dict[index]
                name, genres, artists, popularity, _, danceability, energy, instrumentalness, tempo, valence = list(caracteristics.values())[1:11]
                print(f'{name = }')
                print(f'{artists = }')
                print(f'{genres = }')
                print(f'{popularity = }')
                print(f'{danceability = }')
                print(f'{energy = }')
                print(f'{instrumentalness = }')
                print(f'{tempo = }')
                print(f'{valence = }')

            if generate_csv:
                df.to_csv(f'{playlist_name}.csv')

            if generate_parquet:
                df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

            if build_playlist:
                self.__write_playlist('song', K, additional_info=song)

            if with_distance:
                return df

            return df.drop(columns=['distance'])
        except ValueError as e:
            print(e)

    def __get_desired_dict_fields(self, index, song_dict: list = None):
        """
        Function that returns the usual fields for a given song

        # Parameters
         - index: The index of the song inside the song list

        """
        if song_dict is None:
            song_dict = self.__song_dict

        dict = song_dict[index]
        desired_fields = [
            dict['id'],
            dict['name'],
            dict['artists'],
            dict['genres'],
            dict['popularity'],
            dict['added_at'],
            dict['danceability'],
            dict['energy'],
            dict['instrumentalness'],
            dict['tempo'],
            dict['valence']
        ]

        return desired_fields

    def __song_list_to_df(self, neighbors: list, song_dict: list = None):
        """
        Function that returns DataFrame representation of the list of neighbor songs

        # Parameters
         - neighbors: list of a given song's neighbors

        """
        data = list(
            map(lambda x: list(self.__get_desired_dict_fields(x[0], song_dict=song_dict) + [x[1]]), neighbors))

        return pd.DataFrame(data=data, columns=['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'energy', 'instrumentalness', 'tempo', 'valence', 'distance'])

    def __get_recommendations(self, type, info, K=51):
        """
        General purpose function to get recommendations for any type supported by the package

        # Parameters
         - info: the changed song_dict list if the type is short or medium or else it is the name of the song to get recommendations from
         - K: desired number K of neighbors to be returned
         - type: the type of the playlist being created ('song', 'short', 'medium'), meaning:

            --- 'song': a playlist related to a song

            --- 'short': a playlist related to the short term favorites for that given user

            --- 'medium': a playlist related to the medium term favorites for that given user

            --- 'artist-related': a playlist related to a specific artist


        """
        index = 0
        if type == 'song':
            index = self.__get_index_for_song(info)
        elif type in ['medium', 'short', 'artist-related']:
            index = len(info) - 1
        else:
            raise ValueError('Type does not correspond to a valid option')
        song_dict = self.__song_dict if type == 'song' else info
        neighbors = self.__get_neighbors(song=index, K=K, song_dict=song_dict, type=type)
        return self.__song_list_to_df(neighbors, song_dict=song_dict)

    def __get_genres(self, genres):
        """
        Function to unite all the genres from different songs into one list of genres


        # Parameters
         - genres: the list of lists of genres from the different songs
        """
        try:
            all_genres = genres[0][:]
        except IndexError:
            self.__deny_favorites = True
            raise ValueError(
                'Playlist chosen does not correspond to any of the users favorite songs')

        for index in range(1, len(genres)):
            for i in range(0, len(all_genres)):
                all_genres[i] = all_genres[i] or genres[index][i]

        return all_genres

    def __get_artists(self, artists):
        """
        Function to unite all the artists from different songs into one list of artists


        # Parameters
         - artists: the list of lists of artists from the different songs
        """
        try:
            all_artists = artists[0][:]
        except IndexError:
            raise ValueError(
                'Playlist chosen does not correspond to any of the users favorite songs')

        for index in range(1, len(artists)):
            for i in range(0, len(all_artists)):
                all_artists[i] = all_artists[i] or artists[index][i]

        return all_artists

    def __get_top_5(self, time_range='medium'):
        """
        Function that gets and initially formats the top 5 songs in a given time_range

        # Parameters
         - time_range: The time range to get the top 5 songs from ('medium', 'short')
        """
        if time_range not in ['medium', 'short']:
            raise ValueError(
                'time_range must be either medium_term or short_term')
        top_5 = util.get_request(url=f'https://api.spotify.com/v1/me/top/tracks?{time_range=!s}_term&limit=5', headers=self.__headers).json()
        top_5_songs = list(
            map(lambda song: {
                'name': song['name'],
                'genres': self.__get_song_genres(song),
                'artists': list(
                    map(lambda artist: artist['name'], song['artists'])
                ),
                'popularity': song['popularity'],
                'danceability': self.__playlist.drop_duplicates('id').loc[self.__playlist.drop_duplicates('id')['id'] == song['id'], 'danceability'],
                'energy': self.__playlist.drop_duplicates('id').loc[self.__playlist.drop_duplicates('id')['id'] == song['id'], 'danceability'],
                'instrumentalness': self.__playlist.drop_duplicates('id').loc[self.__playlist.drop_duplicates('id')['id'] == song['id'], 'instrumentalness'],
                'tempo': self.__playlist.drop_duplicates('id').loc[self.__playlist.drop_duplicates('id')['id'] == song['id'], 'tempo'],
                'valence': self.__playlist.drop_duplicates('id').loc[self.__playlist.drop_duplicates('id')['id'] == song['id'], 'valence']
            }, list(
                filter(lambda song: song['name'] in list(self.__playlist['name']), top_5['items'])
            ))
        )

        return top_5_songs

    def __find_recommendations_to_songs(self, base_songs: 'list[dict[str, ]]', subset_name: str):
        """Generates a song format record from a list of songs, with all the information the "song-based" recommendation needs

        Args:
            base_songs (list[dict[str, Any]]): List of base songs
            subset_name (str): Name of thihs subset of songs (barely seen, unless the dataframe is printed with this record in it)

        Returns:
            dict[str, Any]: New song fomat record with the information gathered from the list of base songs
        """
        temp_genres = list(reduce(lambda acc, x: acc + list(set(x['genres']) - set(acc)), base_songs, []))

        temp_artists = list(reduce(lambda acc, x: acc + list(set(x['artists']) - set(acc)), base_songs, []))

        latest_fav = {'id': "", 'name': subset_name, 'genres': temp_genres, 'artists': temp_artists}

        latest_fav['genres_indexed'] = self.__get_genres(list(map(lambda song: util.item_list_indexed(song['genres'], all_items=self.__all_genres), base_songs)))

        latest_fav['artists_indexed'] = self.__get_artists(list(map(lambda song: util.item_list_indexed(song['artists'], all_items=self.__all_artists), base_songs)))

        latest_fav['popularity'] = int(round(reduce(lambda acc, song: acc + int(song['popularity']), base_songs, 0) / len(base_songs)))

        latest_fav['danceability'] = float(reduce(lambda acc, song: acc + float(song['danceability']), base_songs, 0) / len(base_songs))

        latest_fav['energy'] = float(reduce(lambda acc, song: acc + float(song['energy']), base_songs, 0) / len(base_songs))

        latest_fav['instrumentalness'] = float(reduce(lambda acc, song: acc + float(song['instrumentalness']), base_songs, 0) / len(base_songs))

        latest_fav['tempo'] = float(reduce(lambda acc, song: acc + float(song['tempo']), base_songs, 0) / len(base_songs))

        latest_fav['valence'] = float(reduce(lambda acc, song: acc + float(song['valence']), base_songs, 0) / len(base_songs))

        return latest_fav

    def __prepare_fav_data(self, term):
        """
        Function that expands on the formatting of the top_5 some time_range favorites

        # Parameters
         - time_range: The time range to get the top 5 songs from ('medium', 'short')
        """
        top_5_songs = self.__get_top_5(term)

        return self.__find_recommendations_to_songs(
            base_songs=top_5_songs,
            subset_name="Recent-ish Favorites" if term == 'medium' else "Latest Favorites"
        )


    def __end_prepared_fav_data(self, type):
        """
        Final preparation for favorite data before getting visible

        """
        song_dict = self.__song_dict[:]
        fav = self.__prepare_fav_data(type)
        song_dict.append(fav)
        return song_dict

    def get_playlist(self):
        """
        Function that returns the playlist as pandas DataFrame with the needed human readable columns
        """
        return self.__playlist[['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'energy', 'instrumentalness', 'tempo', 'valence']]

    def get_short_term_favorites_playlist(self, with_distance: bool = False, generate_csv: bool = False, generate_parquet: bool = False, build_playlist: bool = False):
        """
        Playlist which centralises the actions for a recommendation made for top 5 songs short term

        # Parameters
         - with_distance (bool): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the closet songs
         - generate_csv (bool): Whether to generate a CSV file containing the recommended playlist
         - generate_parquet (bool): Whether to generate a parquet file containing the recommended playlist
         - build_playlist (bool): Whether to build the playlist to the user's library

        # Note
        The build_playlist option when set to True will change the user's library

        """
        if self.__deny_favorites:
            print("The chosen playlist does not contain the user's favorite songs")
            return
        df = self.__short_fav
        playlist_name = 'Latest Favorites'
        if generate_csv:
            df.to_csv(f'{playlist_name}.csv')
        if generate_parquet:
            df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

        if build_playlist:
            self.__write_playlist('short', 51)

        if with_distance:
            return df

        return df.drop(columns=['distance'])

    def get_medium_term_favorites_playlist(self, with_distance: bool = False, generate_csv: bool = False, generate_parquet: bool = False, build_playlist: bool = False):
        """
        Playlist which centralises the actions for a recommendation made for top 5 songs medium term

        # Parameters
         - with_distance (bool): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since  it does not obey any actual unit, it is just a mathematical value to determine the closet songs
         - generate_csv (bool): Whether to generate a CSV file containing the recommended playlist
         - generate_parquet (bool): Whether to generate a parquet file containing the recommended playlist
         - build_playlist (bool): Whether to build the playlist to the user's library

        # Note
        The build_playlist option when set to True will change the user's library

        """
        if self.__deny_favorites:
            print("The chosen playlist does not contain the user's favorite songs")
            return
        df = self.__medium_fav
        playlist_name = 'Recent-ish Favorites'
        if generate_csv:
            df.to_csv(f'{playlist_name}.csv')
        if generate_parquet:
            df.to_parquet(f'{playlist_name}.parquet', compression='snappy')

        if build_playlist:
            self.__write_playlist('medium', 51)

        if with_distance:
            return df

        return df.drop(columns=['distance'])

    def __prepare_favorites_playlist(self):
        """
        Automatic creation of both the favorites related recommendations
        """
        try:
            self.__short_fav = self.__get_recommendations(
                'short',  self.__end_prepared_fav_data('short'))
            self.__medium_fav = self.__get_recommendations(
                'medium',  self.__end_prepared_fav_data('medium'))
        except ValueError:
            return

    def get_most_listened(self, time_range: str = 'long', K: int = 50, build_playlist: bool = False):
        """Function that creates the most-listened songs playlist for a given period of time in the users profile

        Args:
            time_range (str, optional): time range ('long', 'medium', 'short'). Defaults to 'long'.
            K (int, optional): Number of the most listened songs to return. Defaults to 50.

        Raises:
            ValueError: time range does not correspond to a valid time range ('long', 'medium', 'short')
            ValueError: K number of songs must be between 1 and 100


        Returns:
            pd.DataFrame: pandas DataFrame containing the top K songs in the time range
        """
        if time_range not in ['long', 'medium', 'short']:
            raise ValueError(
                'time_range must be long, medium or short')

        if K > 100 or K < 1:
            raise ValueError('K must be between 1 and 100')

        top = util.get_request(url=f'https://api.spotify.com/v1/me/top/tracks?{time_range=!s}_term&limit={K}', headers=self.__headers).json()

        top_songs = list(map(lambda song: {'id': song['id'], 'name': song['name'], 'genres': self.__get_song_genres(song), 'artists': list(map(
            lambda artist: artist['name'], song['artists'])), 'popularity': song['popularity']}, top['items']))

        if build_playlist:
            self.__write_playlist(
                f'most-listened-{time_range}', K, additional_info=list(map(lambda x: x['id'], top_songs)))

        return pd.DataFrame(data=list(map(lambda x: {'name': x['name'], 'genres': x['genres'], 'artists': x['artists'], 'popularity': x['popularity']}, top_songs)), columns=['name', 'artists', 'genres', 'popularity'])

    def update_all_generated_playlists(self, K: int = None):
        """Update all package generated playlists in batch

        Args:
            K (int, optional): Number of songs in the new playlists, if not set, defaults to the number of songs already in the playlist. Defaults to None.
        """
        total_playlist_count = util.get_request(url=f'https://api.spotify.com/v1/me/playlists?limit=1', headers=self.__headers).json()['total']
        playlists = []
        for offset in range(0, total_playlist_count, 50):
            request = util.get_request(url=f'https://api.spotify.com/v1/me/playlists?limit=50&{offset=!s}',  headers=self.__headers).json()

            playlists += list(map(lambda playlist: (playlist['id'], playlist['name'], playlist['tracks']['total']), request['items']))

        for id, name, total_tracks in playlists:
            try:
                if K is not None:
                    total_tracks = K
                if re.match(r"\'(.*?)\' Related", name) or re.match(r'\"(.*?)\" Related', name):
                    song_name = name.replace(" Related", '')[1:-1]
                    self.__song_name = song_name
                    self.__write_playlist(type='song', K=total_tracks - 1, additional_info=song_name)

                elif re.match(r"\'(.*?)\' Mix", name) or re.match(r'\"(.*?)\" Mix', name):
                    artist_name = name.replace(" Mix", '')[1:-1]
                    self.__artist_name = artist_name
                    self.artist_specific_playlist(
                        K=total_tracks,
                        build_playlist=True,
                        artist_name=artist_name,
                        complete_with_similar=True,
                        _auto=True
                    )

                elif re.match(r"This once was \'(.*?)\'", name) or re.match(r'This once was \"(.*?)\"', name):
                    artist_name = name.replace("This once was ", '')[1:-1]
                    self.__artist_name = artist_name
                    self.artist_specific_playlist(
                        K=total_tracks,
                        build_playlist=True,
                        artist_name=artist_name,
                        complete_with_similar=False,
                        _auto=True
                    )

                elif name in ['Long Term Most-listened Tracks', 'Medium Term Most-listened Tracks', 'Short Term Most-listened Tracks']:
                    self.get_most_listened(time_range=name.split(" ")[0].lower(), K=total_tracks, build_playlist=True)

                elif name == 'Recent-ish Favorites':
                    self.__write_playlist(type='medium', K=total_tracks)

                elif name == 'Latest Favorites':
                    self.__write_playlist(type='short', K=total_tracks)

            except ValueError as e:
                print(
                    f"Unfortunately we couldn't update a playlist because\n {e}")

    def __get_datetime_by_time_range(self, time_range: str = 'all_time'):
        """Calculates the datetime that corresponds to the given time range before the current date

        Args:
            time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.

        Raises:
            ValueError: If the time_range parameter is not valid the error is raised.

        Returns:
            datetime.datetime: Datetime of the specified time_range before the current date
        """
        if time_range not in ['all_time', 'month', 'trimester', 'semester', 'year']:
            raise ValueError('time_range must be one of the following: "all_time", "month", "trimester", "semester", "year"')

        now = datetime.datetime.now(tz=tz.gettz('UTC'))
        date_options = {
            'all_time': datetime.datetime(year=2000, month=1, day=1, hour=0, minute=0, second=0, microsecond=0, tzinfo=tz.gettz('UTC')),
            'month': now - datetime.timedelta(days=30),
            'trimester': now - datetime.timedelta(days=90),
            'semester': now - datetime.timedelta(days=180),
            'year': now - datetime.timedelta(days=365),
        }

        return date_options[time_range]

    def __list_to_count_dict(self, dictionary: dict, item: str) -> dict:
        """Tranforms a list of strings into a dictionary which has the strings as keys and the amount they appear as values

        ## Note\n
        ## This function is to be used in conjunction with a reduce function
        ## Note

        Args:
            dictionary (dict): Dictionary to be created / updated
            item (str): new item from the list
        """
        if item in dictionary.keys():
            dictionary[item] += 1
        else:
            dictionary[item] = 1

        return dictionary

    def __value_dict_to_value_and_percentage_dict(self, dictionary: 'dict[str, int]') -> 'dict[dict[str, float]]':
        """Transforms a dictionary containing only values for a given key into a dictionary containing the values and the total percentage of that key

        Args:
            dictionary (dict): dictionary with only the values for each

        Returns:
            dict[dict[str, float]]: new dictionary with values and total percentages
        """
        dictionary = {key: {'value': value, 'percentage': round(value / dictionary['total'], 5)} for key, value in dictionary.items()}

        return dictionary

    def __plot_bar_chart(self, df: pd.DataFrame, chart_title: str = None, top: int = 10, plot_max: bool = True):
        """Plot a bar Chart with the top values from the dictionary

        Args:
            df (pd.DataFrame): DataFrame to plotthat contains the data
            chart_title (str, optional): label of the chart. Defaults to None
            top (int, optional): numbers of values to be in the chart. Defaults to 10
        """

        if plot_max:
            df = df[df['name'] != ''][0:top + 1]
        else:
            print(f'Total number of songs: {df["number of songs"][0]}')
            df = df[df['name'] != ''][1:top + 1]

        plt.figure(figsize=(15,10))

        sns.color_palette('bright')

        sns.barplot(x='name', y='number of songs', data=df, label=chart_title)

        plt.xticks(
            rotation=45,
            horizontalalignment='right',
            fontweight='light',
            fontsize='x-large'
        )

        plt.show()

    def get_playlist_trending_genres(self, time_range: str = 'all_time', plot_top: 'int|bool' = False) -> pd.DataFrame:
        """Calculates the amount of times each genre was spotted in the playlist, and can plot a bar chart to represent this information

        Args:
            time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.
            plot_top(int|bool , optional): the number of top genres to be plotted. Must be 5, 10, 15 or False. No chart will be plotted if set to False. Defaults to False.

        Raises:
            ValueError: If the time_range parameter is not valid the error is raised.
            ValueError: If plot_top parameter is not valid the error is raised.

        Returns:
            pd.DataFrame: The dictionary that contains how many times each genre was spotted in the playlist in the given time range.
        """
        if time_range not in ['all_time', 'month', 'trimester', 'semester', 'year']:
            raise ValueError('time_range must be one of the following: "all_time", "month", "trimester", "semester", "year"')

        if plot_top not in [5, 10, 15, False]:
            raise ValueError('plot_top must be one of the following: 5, 10, 15 or False')

        playlist = self.__playlist[self.__playlist['added_at'] > self.__get_datetime_by_time_range(time_range=time_range)]

        if not len(playlist):
            print(f"No songs added to the playlist in the time range {time_range} ")
            return None

        genres = list(reduce(lambda x, y: list(x) + list(y), playlist['genres'], []))

        genres_dict = dict(reduce(lambda x, y: self.__list_to_count_dict(dictionary=x, item=y), genres, {}))

        genres_dict['total'] = len(playlist['genres'])

        genres_dict = dict(sorted(genres_dict.items(), key=lambda x: x[1], reverse=True))

        genres_dict = self.__value_dict_to_value_and_percentage_dict(dictionary=genres_dict)

        dictionary = {'name': [], 'number of songs': [], 'rate': []}

        for key, value in genres_dict.items():
            dictionary['name'].append(key)
            dictionary['number of songs'].append(value['value'])
            dictionary['rate'].append(value['percentage'])

        df = pd.DataFrame(data=dictionary, columns=['name', 'number of songs', 'rate'])

        if plot_top:
            self.__plot_bar_chart(df=df, top=plot_top, plot_max=reduce(lambda x, y: x + y, df['rate'][1:4], 0) >= 0.50)

        return df

    def get_playlist_trending_artists(self, time_range: str = 'all_time', plot_top: 'int|bool' = False) -> pd.DataFrame:
        """Calculates the amount of times each artist was spotted in the playlist, and can plot a bar chart to represent this information

        Args:
            time_range (str, optional): Time range that represents how much of the playlist will be considered for the trend. Can be one of the following: 'all_time', 'month', 'trimester', 'semester', 'year'. Defaults to 'all_time'.
            plot_top(int|bool , optional): the number of top genres to be plotted. No chart will be plotted if set to False. Defaults to False.

        Raises:
            ValueError: If the time_range parameter is not valid the error is raised.

        Returns:
            pd.DataFrame: The dictionary that contains how many times each artist was spotted in the playlist in the given time range.
        """
        if time_range not in ['all_time', 'month', 'trimester', 'semester', 'year']:
            raise ValueError('time_range must be one of the following: "all_time", "month", "trimester", "semester", "year"')

        playlist = self.__playlist[self.__playlist['added_at'] > self.__get_datetime_by_time_range(time_range=time_range)]

        if not len(playlist):
            print(f"No songs added to the playlist in the time range {time_range} ")
            return None

        artists = list(reduce(lambda x, y: list(x) + list(y), playlist['artists'], []))

        artists_dict = dict(reduce(lambda x, y: self.__list_to_count_dict(dictionary=x, item=y), artists, {}))

        artists_dict['total'] = len(playlist['artists'])

        artists_dict = dict(sorted(artists_dict.items(), key=lambda x: x[1], reverse=True))

        artists_dict = self.__value_dict_to_value_and_percentage_dict(dictionary=artists_dict)

        dictionary = {'name': [], 'number of songs': [], 'rate': []}

        for key, value in artists_dict.items():
            dictionary['name'].append(key)
            dictionary['number of songs'].append(value['value'])
            dictionary['rate'].append(value['percentage'])

        df = pd.DataFrame(data=dictionary, columns=['name', 'number of songs', 'rate'])

        if plot_top:
            self.__plot_bar_chart(df=df, top=plot_top, plot_max=reduce(lambda x, y: x + y, df['rate'][1:4], 0) >= 0.50)

        return df

    def artist_specific_playlist(self, artist_name: str, K: int = 50, complete_with_similar: bool = False, build_playlist: bool = False, print_base_caracteristics: bool = False, with_distance: bool = False, _auto: bool = False) -> pd.DataFrame:
        """Function that generates DataFrame containing only a specific artist songs, with the possibility of completing it with the closest songs to that artist

        Args:
            artist_name (str): The name of the artist
            K (int, optional): Maximum number of songs. Defaults to 50.
            complete_with_similar (bool, optional): Flag to complete the list of songs with songs that are similar to that artist, until the K number is reached. Defaults to False.
            build_playlist (bool, optional): Whether to build the playlist to the user's library. Defaults to False.
            print_base_caracteristics (bool, optional): Whether to print the base / informed song information, in order to check why such predictions were made by the algorithm. ONLY TAKES EFFECT IF complete_with_similar == True AND K > NUMBER OF SONGS WITH THAT ARTIST. Defaults to False.
            with_distance (bool, optional): Whether to allow the distance column to the DataFrame returned, which will have no actual value for most use cases, since it does not obey any actual unit, it is just a mathematical value to determine the closet songs. ONLY TAKES EFFECT IF complete_with_similar == True AND K > NUMBER OF SONGS WITH THAT ARTIST. Defaults to False.

        Raises:
            ValueError: Value for K must be between 1 and 100
            ValueError: The artist_name specified is not valid

        Returns:
            pd.DataFrame: DataFrame containing the new playlist based on the artist
        """
        if not (1 <= K <= 100):
            raise ValueError('Value for K must be between 1 and 100')

        artist_songs = self.__playlist[self.__playlist['artists'].str.contains(artist_name, regex=False)]

        if not len(artist_songs):
            raise ValueError(f'{artist_name = } does not exist in the playlist')

        self.__artist_name = artist_name

        columns = ['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'energy', 'instrumentalness', 'tempo', 'valence']

        if len(artist_songs) < K:
            if complete_with_similar:
                artist_songs_record_song_dict = list(map(lambda x: {'id': '', 'name': x['name'], 'artists': x['artists'], 'genres': x['genres'], 'artists_indexed': x['artists_indexed'], 'genres_indexed': x['genres_indexed'], 'popularity': x['popularity'], 'added_at': x['added_at'], 'danceability': x['danceability'], 'energy': x['energy'], 'instrumentalness': x['instrumentalness'], 'tempo': x['tempo'], 'valence': x['valence']}, list(filter(lambda x: artist_name in x['artists'], self.__song_dict))))
                artist_songs_record = self.__find_recommendations_to_songs(base_songs=artist_songs_record_song_dict, subset_name=f"{artist_name} Mix")

                song_dict = list(map(lambda x: {'id': x['id'], 'name': x['name'], 'artists': x['artists'], 'genres': x['genres'], 'artists_indexed': x['artists_indexed'], 'genres_indexed': x['genres_indexed'], 'popularity': x['popularity'], 'added_at': x['added_at'], 'danceability': x['danceability'], 'energy': x['energy'], 'instrumentalness': x['instrumentalness'], 'tempo': x['tempo'], 'valence': x['valence']}, list(filter(lambda x: artist_name not in x['artists'], self.__song_dict))))
                song_dict.append(artist_songs_record)

                mix_songs = self.__get_recommendations('artist-related', song_dict, K=K-len(artist_songs))

                ids = artist_songs['id'].append(mix_songs['id'])

                if with_distance:
                    df = artist_songs[columns]

                    columns.append('distance')

                    df['distance'] = pd.to_numeric(0)

                    df = df[columns].append(mix_songs[columns])

                else:
                    df = artist_songs[columns].append(mix_songs[columns])

                if print_base_caracteristics and not _auto:
                    name = artist_songs_record['name']
                    genres = artist_songs_record['genres']
                    artists = artist_songs_record['artists']
                    popularity = artist_songs_record['popularity']
                    danceability = artist_songs_record['danceability']
                    energy = artist_songs_record['energy']
                    instrumentalness = artist_songs_record['instrumentalness']
                    tempo = artist_songs_record['tempo']
                    valence = artist_songs_record['valence']
                    print(f'{name = }')
                    print(f'{artists = }')
                    print(f'{genres = }')
                    print(f'{popularity = }')
                    print(f'{danceability = }')
                    print(f'{energy = }')
                    print(f'{instrumentalness = }')
                    print(f'{tempo = }')
                    print(f'{valence = }')


            else:
                if not _auto:
                    print(f'Playlist has only {len(artist_songs)} songs')
                    print(f'To fill the {K = } number of songs, consider using the flag complete_with_similar')
                ids = artist_songs['id']
                df = artist_songs[columns]

        else:
            ids = artist_songs['id']
            df = artist_songs[columns]

        if build_playlist:
            self.__write_playlist(
                K=K,
                type=f'artist{"-related" if len(artist_songs) < K and complete_with_similar else ""}',
                additional_info=ids
            )

        return df.reset_index(drop=True)

    def audio_features_extraordinary_songs(self) -> 'dict[str, dict]':
        """Returns a dictionary with the maximum and minimum values for each audio feature used in the package

        Note:
            Although there are many more audio features available in Spotify Web API, these were the only ones needed to provide the best fitting recommendations within this package

        Note:
            The Audio features are:
            - danceability: Danceability describes how suitable a track is for dancing based on a combination of musical elements including tempo, rhythm stability, beat strength, and overall regularity. A value of 0.0 is least danceable and 1.0 is most danceable.
            - energy: Energy is a measure from 0.0 to 1.0 and represents a perceptual measure of intensity and activity. Typically, energetic tracks feel fast, loud, and noisy. For example, death metal has high energy, while a Bach prelude scores low on the scale. Perceptual features contributing to this attribute include dynamic range, perceived loudness, timbre, onset rate, and general entropy.
            - instrumentalness: Predicts whether a track contains no vocals. "Ooh" and "aah" sounds are treated as instrumental in this context. Rap or spoken word tracks are clearly "vocal". The closer the instrumentalness value is to 1.0, the greater likelihood the track contains no vocal content
            - tempo: The overall estimated tempo of a track in beats per minute (BPM). In musical terminology, tempo is the speed or pace of a given piece and derives directly from the average beat duration.
            - valence: A measure from 0.0 to 1.0 describing the musical positiveness conveyed by a track. Tracks with high valence sound more positive (e.g. happy, cheerful, euphoric), while tracks with low valence sound more negative (e.g. sad, depressed, angry).

        Returns:
            dict[str, dict]: The dictionary with the maximum and minimum values for each audio feature used in the package
        """
        df = self.__playlist[['id', 'name', 'artists', 'genres', 'popularity', 'added_at', 'danceability', 'energy', 'instrumentalness', 'tempo', 'valence']]

        df_danceability = df.sort_values('danceability', ascending=True)
        df_energy = df.sort_values('energy', ascending=True)
        df_instrumentalness = df.sort_values('instrumentalness', ascending=True)
        df_tempo = df.sort_values('tempo', ascending=True)
        df_valence = df.sort_values('valence', ascending=True)
        max_danceability = df_danceability.tail(n=1).reset_index(drop=True)
        min_danceability = df_danceability.head(n=1).reset_index(drop=True)
        max_energy = df_energy.tail(n=1).reset_index(drop=True)
        min_energy = df_energy.head(n=1).reset_index(drop=True)
        max_instrumentalness = df_instrumentalness.tail(n=1).reset_index(drop=True)
        min_instrumentalness = df_instrumentalness.head(n=1).reset_index(drop=True)
        max_tempo = df_tempo.tail(n=1).reset_index(drop=True)
        min_tempo = df_tempo.head(n=1).reset_index(drop=True)
        max_valence = df_valence.tail(n=1).reset_index(drop=True)
        min_valence = df_valence.head(n=1).reset_index(drop=True)

        return {
            'max_danceability': {
                'id': max_danceability['id'][0],
                'name': max_danceability['name'][0],
                'genres': max_danceability['genres'][0],
                'artists': max_danceability['artists'][0],
                'popularity': max_danceability['popularity'][0],
                'added_at': max_danceability['added_at'][0],
                'danceability': max_danceability['danceability'][0],
                'energy': max_danceability['energy'][0],
                'instrumentalness': max_danceability['instrumentalness'][0],
                'tempo': max_danceability['tempo'][0],
                'valence': max_danceability['valence'][0]
            },
            'min_danceability': {
                'id': min_danceability['id'][0],
                'name': min_danceability['name'][0],
                'genres': min_danceability['genres'][0],
                'artists': min_danceability['artists'][0],
                'popularity': min_danceability['popularity'][0],
                'added_at': min_danceability['added_at'][0],
                'danceability': min_danceability['danceability'][0],
                'energy': min_danceability['energy'][0],
                'instrumentalness': min_danceability['instrumentalness'][0],
                'tempo': min_danceability['tempo'][0],
                'valence': min_danceability['valence'][0]
            },
            'max_energy': {
                'id': max_energy['id'][0],
                'name': max_energy['name'][0],
                'genres': max_energy['genres'][0],
                'artists': max_energy['artists'][0],
                'popularity': max_energy['popularity'][0],
                'added_at': max_energy['added_at'][0],
                'danceability': max_energy['danceability'][0],
                'energy': max_energy['energy'][0],
                'instrumentalness': max_energy['instrumentalness'][0],
                'tempo': max_energy['tempo'][0],
                'valence': max_energy['valence'][0]
            },
            'min_energy': {
                'id': min_energy['id'][0],
                'name': min_energy['name'][0],
                'genres': min_energy['genres'][0],
                'artists': min_energy['artists'][0],
                'popularity': min_energy['popularity'][0],
                'added_at': min_energy['added_at'][0],
                'danceability': min_energy['danceability'][0],
                'energy': min_energy['energy'][0],
                'instrumentalness': min_energy['instrumentalness'][0],
                'tempo': min_energy['tempo'][0],
                'valence': min_energy['valence'][0]
            },
            'max_instrumentalness': {
                'id': max_instrumentalness['id'][0],
                'name': max_instrumentalness['name'][0],
                'genres': max_instrumentalness['genres'][0],
                'artists': max_instrumentalness['artists'][0],
                'popularity': max_instrumentalness['popularity'][0],
                'added_at': max_instrumentalness['added_at'][0],
                'danceability': max_instrumentalness['danceability'][0],
                'energy': max_instrumentalness['energy'][0],
                'instrumentalness': max_instrumentalness['instrumentalness'][0],
                'tempo': max_instrumentalness['tempo'][0],
                'valence': max_instrumentalness['valence'][0]
            },
            'min_instrumentalness': {
                'id': min_instrumentalness['id'][0],
                'name': min_instrumentalness['name'][0],
                'genres': min_instrumentalness['genres'][0],
                'artists': min_instrumentalness['artists'][0],
                'popularity': min_instrumentalness['popularity'][0],
                'added_at': min_instrumentalness['added_at'][0],
                'danceability': min_instrumentalness['danceability'][0],
                'energy': min_instrumentalness['energy'][0],
                'instrumentalness': min_instrumentalness['instrumentalness'][0],
                'tempo': min_instrumentalness['tempo'][0],
                'valence': min_instrumentalness['valence'][0]
            },
            'max_tempo': {
                'id': max_tempo['id'][0],
                'name': max_tempo['name'][0],
                'genres': max_tempo['genres'][0],
                'artists': max_tempo['artists'][0],
                'popularity': max_tempo['popularity'][0],
                'added_at': max_tempo['added_at'][0],
                'danceability': max_tempo['danceability'][0],
                'energy': max_tempo['energy'][0],
                'instrumentalness': max_tempo['instrumentalness'][0],
                'tempo': max_tempo['tempo'][0],
                'valence': max_tempo['valence'][0]
            },
            'min_tempo': {
                'id': min_tempo['id'][0],
                'name': min_tempo['name'][0],
                'genres': min_tempo['genres'][0],
                'artists': min_tempo['artists'][0],
                'popularity': min_tempo['popularity'][0],
                'added_at': min_tempo['added_at'][0],
                'danceability': min_tempo['danceability'][0],
                'energy': min_tempo['energy'][0],
                'instrumentalness': min_tempo['instrumentalness'][0],
                'tempo': min_tempo['tempo'][0],
                'valence': min_tempo['valence'][0]
            },
            'max_valence': {
                'id': max_valence['id'][0],
                'name': max_valence['name'][0],
                'genres': max_valence['genres'][0],
                'artists': max_valence['artists'][0],
                'popularity': max_valence['popularity'][0],
                'added_at': max_valence['added_at'][0],
                'danceability': max_valence['danceability'][0],
                'energy': max_valence['energy'][0],
                'instrumentalness': max_valence['instrumentalness'][0],
                'tempo': max_valence['tempo'][0],
                'valence': max_valence['valence'][0]
            },
            'min_valence': {
                'id': min_valence['id'][0],
                'name': min_valence['name'][0],
                'genres': min_valence['genres'][0],
                'artists': min_valence['artists'][0],
                'popularity': min_valence['popularity'][0],
                'added_at': min_valence['added_at'][0],
                'danceability': min_valence['danceability'][0],
                'energy': min_valence['energy'][0],
                'instrumentalness': min_valence['instrumentalness'][0],
                'tempo': min_valence['tempo'][0],
                'valence': min_valence['valence'][0]
            },
        }


def start_api(user_id, *, playlist_url=None, playlist_id=None):
    """Function that prepares for and initializes the API

    ## Note:
    Internet Connection is required

    Args:
        user_id: the id of user, present in the user account profile
        playlist_url(str, optional, keyword-argument only): the url for the playlist, which is visible when trying to share it. Defaults to None.
        playlist_id (str, optional, keyword-argument only): the id of the playlist, an unique big hash which identifies the playlist. Defaults to None.

    Raises:
        ValueError: at least one of the playlist related arguments have to be specified
        ValueError: when asked to input the auth token, in case it is not valid, an error is raised

    Returns:
        SpotifyAPI: The instance of the SpotifyAPI class

    ## Note:
    Although both the playlist_url and playlist_id are optional, informing at least one of them is required, though the choice is up to you
    """

    if not playlist_url and not playlist_id:
        raise ValueError(
            'It is necessary to specify a playlist either with playlist id or playlist url')
    if playlist_url and not playlist_id:
        playlist_id = False
    if playlist_id and not playlist_url:
        playlist_url = False

    get_auth()
    auth_token = input('Paste here the auth token: ')
    while not auth_token:
        auth_token = input('Enter a valid auth token: ')

    auth_token = f'Bearer {auth_token}'

    return SpotifyAPI(auth_token=auth_token, playlist_id=playlist_id, user_id=user_id, playlist_url=playlist_url)
