const link = document.querySelector("#auth_button")

fetch("./assets/security/spotify.json")
    .then(response => response.json())
    .then(({client_id, redirect_uri, scope}) => {
        if (window.location.href.includes("localhost") || window.location.href.includes("127.0.0")) {
            redirect_uri =
                "http://127.0.0.1:5500/spotify-api/interface/authorization.html"
        }
        link.href = `https://accounts.spotify.com/authorize?client_id=${client_id}&response_type=code&redirect_uri=${redirect_uri}&scope=${scope}`
    })
