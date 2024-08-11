// Get modal element
const modal = document.getElementById("apiModal");
const startApiBtn = document.getElementById("startApiBtn");
const closeBtn = document.querySelector(".close");

const playlistUrlCheckbox = document.getElementById("PlaylistUrl");
const likedSongsCheckbox = document.getElementById("LikedSongs");
const playlistIdCheckbox = document.getElementById("PlaylistID");
const userIdCheckbox = document.getElementById("UserID");

const playlistUrlText = document.getElementById("PlaylistUrlText");
const playlistIdText = document.getElementById("PlaylistIDText");
const userIdText = document.getElementById("UserIDText");

function updateCheckboxes() {
    const isUserIdChecked = userIdCheckbox.checked;
    const isPlaylistIdChecked = playlistIdCheckbox.checked;
    const isLikedSongsChecked = likedSongsCheckbox.checked;
    const isPlaylistUrlChecked = playlistUrlCheckbox.checked;

    if (isPlaylistUrlChecked) {
        playlistUrlText.disabled = false;
        likedSongsCheckbox.checked = false;
        playlistIdCheckbox.checked = false;
        likedSongsCheckbox.disabled = true;
        playlistIdCheckbox.disabled = true;
        playlistIdText.style.display = "none";
        playlistUrlText.style.display = "flex";
        playlistIdCheckbox.style.cursor = "not-allowed";
        likedSongsCheckbox.style.cursor = "not-allowed";
    }
    else if (isPlaylistIdChecked) {
        playlistIdText.disabled = false;
        likedSongsCheckbox.checked = false;
        playlistUrlCheckbox.checked = false;
        likedSongsCheckbox.disabled = true;
        playlistUrlCheckbox.disabled = true;
        playlistIdText.style.display = "flex";
        playlistUrlText.style.display = "none";
        likedSongsCheckbox.style.cursor = "not-allowed";
        playlistUrlCheckbox.style.cursor = "not-allowed";
    }
    else if (isLikedSongsChecked) {
        playlistIdCheckbox.checked = false;
        playlistUrlCheckbox.checked = false;
        playlistIdCheckbox.disabled = true;
        playlistUrlCheckbox.disabled = true;
        playlistIdText.style.display = "none";
        playlistUrlText.style.display = "none";
        playlistIdCheckbox.style.cursor = "not-allowed";
        playlistUrlCheckbox.style.cursor = "not-allowed";
    }
    else {
        playlistUrlText.disabled = true;
        playlistIdText.disabled = true;
        userIdText.disabled = true;
        likedSongsCheckbox.disabled = false;
        playlistIdCheckbox.disabled = false;
        userIdCheckbox.disabled = false;
        playlistUrlCheckbox.disabled = false;
        playlistIdText.style.display = "none";
        playlistUrlText.style.display = "none";
        likedSongsCheckbox.style.cursor = "text";
        playlistIdCheckbox.style.cursor = "text";
        playlistUrlCheckbox.style.cursor = "text";
    }

    userIdText.disabled = !isUserIdChecked;
    userIdText.style.display = isUserIdChecked ? "flex" : "none";

}

// Event listeners
playlistUrlCheckbox.addEventListener("change", updateCheckboxes);
likedSongsCheckbox.addEventListener("change", updateCheckboxes);
playlistIdCheckbox.addEventListener("change", updateCheckboxes);
userIdCheckbox.addEventListener("change", updateCheckboxes);

// Show modal
startApiBtn.onclick = function() {
    modal.style.display = "flex";
}

// Close modal
closeBtn.onclick = function() {
    modal.style.display = "none";
}

// Close modal when clicking outside
window.onclick = function(event) {
    if (event.target == modal) {
        modal.style.display = "none";
    }
}