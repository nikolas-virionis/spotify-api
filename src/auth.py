import webbrowser

def get_auth():
    print('In order to get the authentication code that allows everything to work nicely, you have to get to the spotify console and set the OAuth token scopes (powers) as follow, then you click onto the token then ctrl + A, to select it all, then crtl + C to copy it, then provide it to the class constructor and its all set\n')
    scope = 'playlist-modify-private playlist-read-private user-library-read user-library-modify user-top-read\n'
    
    print(scope)
    answer = input("Ready to be redirected to get the token (y/n)? ")
    while answer.lower() not in ['y', 'n']:
        answer = input("Please select a valid response: ")
    if answer.lower() == 'y':
        webbrowser.open('https://developer.spotify.com/console/get-artist/')
    else:
        print('In order to get the token and use this lib, it is necessary to get the auth token')

