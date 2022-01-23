from requests import get, post, delete
import pandas as pd
from sensitive import *
from auth import get_auth
import operator
import json
from functools import reduce



class SpotifyAPI:
    def __init__(self, playlist_id, user_id, playlist_url):
        self.__playlist_id = playlist_id
        self.__user_id = user_id
        self.__playlist_url = playlist_url
        self.__auth_token = get_auth(CLIENT_ID, CLIENT_SECRET)
        self.__headers = {"Accept": "application/json",
                          "Content-Type": "application/json", "Authorization": self.__auth_token}
        self.__artists = []
        self.__songs = []

    def __get_total_song_count(self):
        playlist_res = get(
            f'https://api.spotify.com/v1/playlists/{self.__playlist_id}', headers=self.__headers)
        return playlist_res.json()["tracks"]["total"]

    def __add_genres(self, list, genres):
        for genre in genres:
            if genre not in list:
                list.append(genre)

        return list

    def __get_song_genres(self, song):
        genres = []
        for artist in song["track"]["artists"]:
            id = artist["id"]
            if id not in self.__artists:
                artist_genres_res = get(
                    f'https://api.spotify.com/v1/artists/{id}', headers=self.__headers)
                try:
                    artist_genres = artist_genres_res.json()["genres"]
                except Exception:
                    print(artist_genres_res.json())
                genres = self.__add_genres(genres, artist_genres)
                self.__artists[artist["name"]] = artist_genres
            else:
                genres = self.__add_genres(genres, self.__artists[id])

        return genres

    def __song_data(self, song):
        return song["track"]['id'], song["track"]['name'], song["track"]['popularity'], [artist["name"] for artist in song["track"]["artists"]]

    def get_playlist_items(self):
        self.__all_genres = []
        for offset in range(0, self.__get_total_song_count(), 100):
            all_genres_res = get(
                f'https://api.spotify.com/v1/playlists/{self.__playlist_id}/tracks?limit=100&offset={offset}', headers=self.__headers)
            for song in all_genres_res.json()["items"]:
                (id, name, popularity, artist), song_genres = self.__song_data(
                    song), self.__get_song_genres(song)
                self.__songs.append({"id": id, "name": name, "artists": artist,
                                     "popularity": popularity, "genres": song_genres})
                self.__all_genres = self.__add_genres(self.__all_genres, song_genres)

    def playlist_adjustments(self):
        songs = self.__songs[-self.__get_total_song_count():]
        playlist = pd.DataFrame(data=songs, columns=[
                        'id', 'name', 'artists', 'popularity', 'genres'])
        self.__playlist = playlist

    def playlist_to_csv(self):
        df = pd.DataFrame(data=[{'artists':self.__artists, 'songs':self.__songs, 'all_genres':self.__all_genres}], columns=['artists', 'songs', 'all_genres'])

        df.to_parquet('./.spotify-recommender-util/util.parquet')

        self.__playlist.drop_duplicates(keep='first').to_csv('playlist.csv', header=True, index=None)



    def get_playlist_from_csv(self):
        df = pd.read_parquet('./.spotify-recommender-util/util.parquet')

        self.__artists, self.__songs, self.__all_genres = list(map(lambda arr: arr if type(arr) == 'str' else eval(arr), df['artists'][0], df['songs'][0], df['all_genres'][0]))

        self.__all_artists = list(self.__artists.keys())
        self.__playlist = pd.read_csv('playlist.csv')


    def __genres_indexed(self, genres):
        indexed = []
        for all_genres_x in self.__all_genres:

            continue_outer = False
            for genre in genres:
                index = all_genres_x == genre
                if index:
                    continue_outer = True
                    indexed.append(int(True))
                    break

            if continue_outer:
                continue

            indexed.append(int(False))

        return indexed


    def __artists_indexed(self, artists):
        indexed = []
        for all_artists_x in self.__all_artists:

            continue_outer = False
            for genre in artists:
                index = all_artists_x == genre
                if index:
                    continue_outer = True
                    indexed.append(int(True))
                    break

            if continue_outer:
                continue

            indexed.append(int(False))

        return indexed

    def __knn_prepared_data(self, df):
        df = df[['id', 'name', 'genres', 'artists',
                'popularity', 'genres_indexed', 'artists_indexed']]
        list = []
        for index in range(len(df['id'])):
            list.append({'id': df['id'][index], 'name': df['name'][index], 'genres': df['genres'][index], 'artists': df['artists'][index],
                        'popularity': df['popularity'][index], 'genres_indexed': df['genres_indexed'][index], 'artists_indexed': df['artists_indexed'][index]})

        self.__song_dict = list

    def __compute_distance(self, a, b):
        genres_distance = self.__list_distance(a['genres_indexed'], b['genres_indexed'])
        artists_distance = self.__list_distance(a['artists_indexed'], b['artists_indexed'])
        popularity_distance = abs(a['popularity'] - b['popularity'])
        return genres_distance + artists_distance * 0.4 + (popularity_distance * 0.005)

    def __list_distance(self, a, b):
        distance = 0
        for item_a, item_b in list(zip(a, b)):
            if item_a != item_b:
                if int(item_a) == 1:
                    distance += 0.4
                else:
                    distance += 0.2
            else:
                if int(item_a) == 1:
                    distance -= 0.4

        return distance

    def __get_neighbors(self, song, K):
        distances = []
        for song_index, song_value in enumerate(self.__song_dict):
            if (song_index != song):
                dist = self.__compute_distance(self.__song_dict[song], song_value)
                distances.append((song_index, dist))
        distances.sort(key=operator.itemgetter(1))
        neighbors = []
        for x in range(K):
            neighbors.append([*distances[x]])
        return neighbors


    def get_recommendations_for_song(self, song_name, K = 50):
        self.__song_name = song_name
        if K > 100:
            print('K limit exceded. Maximum value for K is 100')
            K = 100
        item = self.__playlist[[self.__playlist['name'][x] ==
                        song_name for x in range(len(self.__playlist['name']))]]
        index = item.index[0]
        self.__neighbors = self.__get_neighbors(index, K)
        print(self.__song_dict[index]['name'], self.__song_dict[index]['artists'],
            self.__song_dict[index]['genres'], self.__song_dict[index]['popularity'])
        for neighbor, index in zip(self.__neighbors, range(1, K + 1)):
            print(
                f'{index}. {self.__song_dict[neighbor[0]]["name"]} \t {self.__song_dict[neighbor[0]]["artists"]} \t {self.__song_dict[neighbor[0]]["genres"]} \t {self.__song_dict[neighbor[0]]["popularity"]} \t {neighbor[1]}')
    
    def playlist_exists(self, name):
        request = get('https://api.spotify.com/v1/me/playlists', headers=self.__headers).json()

        playlists = list(map(lambda playlist: (playlist['id'], playlist['name']), request['items']))

        for playlist in playlists:
            if playlist[1] == name:
                return playlist[0]
            
        return False

    def __create_playlist(self):
        playlist_name = f"{self.__song_name!r} Related"
        new_id = ""
        playlist_id_found = self.playlist_exists(playlist_name)
        if playlist_id_found:
            new_id = playlist_id_found
            
            playlist_tracks = list(map(lambda track: {'uri': track['track']['uri']}, get(f'https://api.spotify.com/v1/playlists/{new_id}/tracks', headers=self.__headers).json()['items']))

            delete_json = delete(f'https://api.spotify.com/v1/playlists/{new_id}/tracks',  headers=self.__headers, data=json.dumps({"tracks": playlist_tracks})).json()
            print(delete_json)
        else:
            data = {"name": playlist_name, "description": f"Songs related to {self.__song_name!r}", "public": False}
            playlist_creation = post(f'https://api.spotify.com/v1/users/{self.__user_id}/playlists', headers=self.__headers, data=json.dumps(data))
            new_id = playlist_creation.json()['id']
        return new_id


    def build_playlist(self):
        item = self.__playlist[[self.__playlist['name'][x] == self.__song_name for x in range(len(self.__playlist['name']))]]
        index = item.index[0]
        song_uris = f'spotify:track:{self.__song_dict[index]["id"]}'
        for neighbor in self.__neighbors:
            song_uris += f',spotify:track:{self.__song_dict[neighbor]["id"]}'

        add_songs_req = post(f'https://api.spotify.com/v1/playlists/{self.__create_playlist()}/tracks?uris={song_uris}', headers=self.__headers, data=json.dumps({}))
        add_songs_req.json()

    def __get_genres(self, genres):
        all_genres = genres[0][:]

        for index in range(1, len(genres)):
            for i in range(0, len(all_genres)):
                all_genres[i] = all_genres[i] or genres[index][i]

        return all_genres

        
    def __get_artists(self, artists):
        all_artists = artists[0][:]

        for index in range(1, len(artists)):
            for i in range(0, len(all_artists)):
                all_artists[i] = all_artists[i] or artists[index][i]

        return all_artists

    def __get_mid_term_top_5(self):
        top_5 = get('https://api.spotify.com/v1/me/top/tracks?time_range=medium_term&limit=5', headers=self.__headers).json()
        top_5_songs = list(filter(lambda song: song['name'] in list(self.__playlist['name']), list(map(lambda song: {'name': song['name'], 'genres': self.__get_song_genres(song), 'artists': list(map(lambda artist: artist['name'],song['artists'])), 'popularity': song['popularity']},top_5['items']))))

        return top_5_songs

    def __prepare_fav_data(self):
        top_5_songs = self.__get_mid_term_top_5()
        temp_genres = list(reduce(lambda acc, x: acc + list(set(x['genres']) - set(acc)), top_5_songs, []))
        temp_artists = list(reduce(lambda acc, x: acc + list(set(x['artists']) - set(acc)), top_5_songs, []))
        latest_fav = {'id': "", 'name': "Latest Favorites", 'genres': temp_genres, 'artists': temp_artists}

        latest_fav['genres_indexed'] = self.__get_genres(list(map(lambda song: self.__genres_indexed(song['genres']), top_5_songs)))

        latest_fav['artists_indexed'] = self.__get_artists(list(map(lambda song: self.__artists_indexed(song['artists']), top_5_songs)))

        latest_fav['popularity'] = int(reduce(lambda acc, song: acc + int(song['popularity']), top_5_songs, 0) / len(top_5_songs))

        return latest_fav

    def __end_prepared_fav_data(self):
        if len(self.__song_dict) == len(self.__songs):
            self.__song_dict.append(self.__prepare_fav_data())
        elif len(self.__song_dict) == len(self.__songs) + 1:
            self.__song_dict.pop()
            self.__song_dict.append(self.____prepare_fav_data())
        else:
            raise Exception("error in lists indexes")