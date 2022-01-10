# spotify-api

<img src='https://storage.googleapis.com/pr-newsroom-wp/1/2018/11/Spotify_Logo_CMYK_Green.png' width='60%'>

## Context
This script, in jupyter notebook format for organization purposes, applies the technique called K Nearest Neighbours to find the 50 closest songs to either one chosen or one of the users top 5(short term), all within a specific Spotify playlist, and creates a new playlist with those songs in the user's library, using their genres, artists and overall popularity

## DISCLAIMER ##
Not fit for direct use since some information such as client id, client secret, auth token (changes each hour or less) with the right scopes, playlist id and user id, all of which are in a .env, have to be informed in order for the Spotify Web API to work properly
