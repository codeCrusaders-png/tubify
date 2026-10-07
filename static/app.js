// Application State
const state = {
  accessToken: localStorage.getItem("spotify_access_token") || null,
  refreshToken: localStorage.getItem("spotify_refresh_token") || null,
  ytSong: null,
  matchedTrack: null,
  selectedMood: null,
  recommendation: null,
};

// DOM Elements
const authStatus = document.getElementById("authStatus");
const authBtn = document.getElementById("authBtn");
const urlForm = document.getElementById("urlForm");
const youtubeUrl = document.getElementById("youtubeUrl");
const analyzeBtn = document.getElementById("analyzeBtn");
const errorBanner = document.getElementById("errorBanner");

// Sections
const songMatchSection = document.getElementById("songMatchSection");
const moodSection = document.getElementById("moodSection");
const recommendSection = document.getElementById("recommendSection");
const resultSection = document.getElementById("resultSection");

// Song Match Elements
const ytThumbnail = document.getElementById("ytThumbnail");
const ytTitle = document.getElementById("ytTitle");
const ytArtist = document.getElementById("ytArtist");
const ytChannel = document.getElementById("ytChannel");
const ytDuration = document.getElementById("ytDuration");
const spotCover = document.getElementById("spotCover");
const spotTitle = document.getElementById("spotTitle");
const spotArtist = document.getElementById("spotArtist");
const spotAlbum = document.getElementById("spotAlbum");
const spotConfidencePill = document.getElementById("spotConfidencePill");
const confirmMatchBtn = document.getElementById("confirmMatchBtn");
const candidatesContainer = document.getElementById("candidatesContainer");
const candidatesList = document.getElementById("candidatesList");

// Mood Elements
const moodChips = document.getElementById("moodChips");
const customMoodInput = document.getElementById("customMoodInput");
const aiDecideBtn = document.getElementById("aiDecideBtn");
const recommendBtn = document.getElementById("recommendBtn");

// Recommendation Elements
const recPlaylistName = document.getElementById("recPlaylistName");
const recAiMood = document.getElementById("recAiMood");
const recUserMood = document.getElementById("recUserMood");
const recConfidence = document.getElementById("recConfidence");
const recExplanation = document.getElementById("recExplanation");
const playlistStatusNotice = document.getElementById("playlistStatusNotice");
const recAlternativesContainer = document.getElementById("recAlternativesContainer");
const recAlternativesList = document.getElementById("recAlternativesList");
const cancelRecBtn = document.getElementById("cancelRecBtn");
const confirmAddBtn = document.getElementById("confirmAddBtn");

// Result Elements
const resSong = document.getElementById("resSong");
const resArtist = document.getElementById("resArtist");
const resAiMood = document.getElementById("resAiMood");
const resUserMood = document.getElementById("resUserMood");
const resPlaylist = document.getElementById("resPlaylist");
const resConfidence = document.getElementById("resConfidence");
const openSpotifyLink = document.getElementById("openSpotifyLink");
const organizeAnotherBtn = document.getElementById("organizeAnotherBtn");

// History Elements
const refreshHistoryBtn = document.getElementById("refreshHistoryBtn");
const historyTable = document.getElementById("historyTable");
const emptyHistoryMsg = document.getElementById("emptyHistoryMsg");
const historyBody = document.getElementById("historyBody");

// -----------------------------------------------------------------
// Initialization & Authentication Handling
// -----------------------------------------------------------------

function initAuth() {
  // Check URL parameters for OAuth redirect tokens
  const urlParams = new URLSearchParams(window.location.search);
  const token = urlParams.get("access_token");
  const refresh = urlParams.get("refresh_token");

  if (token) {
    state.accessToken = token;
    localStorage.setItem("spotify_access_token", token);
    if (refresh) {
      state.refreshToken = refresh;
      localStorage.setItem("spotify_refresh_token", refresh);
    }
    // Clean URL
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  updateAuthUI();
  fetchHistory();
}

function updateAuthUI() {
  if (state.accessToken) {
    authStatus.textContent = "Spotify Connected";
    authStatus.className = "auth-badge connected";
    authBtn.textContent = "Disconnect";
    authBtn.onclick = () => {
      localStorage.removeItem("spotify_access_token");
      localStorage.removeItem("spotify_refresh_token");
      state.accessToken = null;
      state.refreshToken = null;
      updateAuthUI();
    };
  } else {
    authStatus.textContent = "Spotify Disconnected";
    authStatus.className = "auth-badge disconnected";
    authBtn.textContent = "Connect Spotify";
    authBtn.onclick = () => {
      window.location.href = "/auth/spotify/login";
    };
  }
}

// -----------------------------------------------------------------
// Error Banner
// -----------------------------------------------------------------

function showError(message) {
  errorBanner.textContent = message;
  errorBanner.classList.remove("hidden");
  setTimeout(() => {
    errorBanner.classList.add("hidden");
  }, 6000);
}

// -----------------------------------------------------------------
// Step 1: URL Analyze & Spotify Search
// -----------------------------------------------------------------

urlForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = youtubeUrl.value.trim();
  if (!url) return;

  errorBanner.classList.add("hidden");
  analyzeBtn.disabled = true;
  analyzeBtn.querySelector(".btn-text").textContent = "Analyzing...";

  try {
    // 1. Analyze YouTube Video
    const ytRes = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ youtube_url: url }),
    });

    if (!ytRes.ok) {
      const err = await ytRes.json();
      throw new Error(err.detail || "Failed to extract YouTube metadata.");
    }

    state.ytSong = await ytRes.json();
    renderYouTubeCard(state.ytSong);

    // 2. Search Spotify Track
    const searchRes = await fetch("/spotify/search", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        title: state.ytSong.title,
        artist: state.ytSong.artist,
        access_token: state.accessToken,
      }),
    });

    if (!searchRes.ok) {
      const err = await searchRes.json();
      throw new Error(err.detail || "Spotify track search failed.");
    }

    const searchData = await searchRes.json();
    if (!searchData.matched || !searchData.track) {
      throw new Error(`No matching track found on Spotify for "${state.ytSong.title}" by ${state.ytSong.artist}.`);
    }

    state.matchedTrack = searchData.track;
    renderSpotifyCard(state.matchedTrack, searchData.candidates);

    songMatchSection.classList.remove("hidden");
    moodSection.classList.add("hidden");
    recommendSection.classList.add("hidden");
    resultSection.classList.add("hidden");
    songMatchSection.scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    showError(err.message);
  } finally {
    analyzeBtn.disabled = false;
    analyzeBtn.querySelector(".btn-text").textContent = "Analyze Video";
  }
});

function renderYouTubeCard(song) {
  ytThumbnail.src = song.thumbnail_url || "";
  ytTitle.textContent = song.title;
  ytArtist.textContent = song.artist;
  ytChannel.textContent = song.channel;
  ytDuration.textContent = song.duration;
}

function renderSpotifyCard(track, candidates = []) {
  spotCover.src = track.album_art || "";
  spotTitle.textContent = track.title;
  spotArtist.textContent = track.artist;
  spotAlbum.textContent = track.album;
  spotConfidencePill.textContent = `Match Confidence: ${Math.round(track.confidence * 100)}%`;

  if (track.confidence < 0.85 && candidates.length > 1) {
    candidatesContainer.classList.remove("hidden");
    candidatesList.innerHTML = "";
    candidates.forEach((cand) => {
      const item = document.createElement("div");
      item.className = "candidate-item";
      item.innerHTML = `
        <div>
          <strong>${cand.title}</strong> - ${cand.artist} <small>(${cand.album})</small>
        </div>
        <span class="confidence-pill">${Math.round(cand.confidence * 100)}%</span>
      `;
      item.onclick = () => {
        state.matchedTrack = cand;
        renderSpotifyCard(cand, candidates);
      };
      candidatesList.appendChild(item);
    });
  } else {
    candidatesContainer.classList.add("hidden");
  }
}

// -----------------------------------------------------------------
// Step 2: Confirm Match & Show Mood Selection
// -----------------------------------------------------------------

confirmMatchBtn.addEventListener("click", () => {
  moodSection.classList.remove("hidden");
  moodSection.scrollIntoView({ behavior: "smooth" });
});

// Mood chip toggles
moodChips.querySelectorAll(".chip").forEach((chip) => {
  chip.addEventListener("click", () => {
    moodChips.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    chip.classList.add("active");
    state.selectedMood = chip.dataset.mood;
    customMoodInput.value = "";
  });
});

customMoodInput.addEventListener("input", () => {
  if (customMoodInput.value.trim()) {
    moodChips.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
    state.selectedMood = customMoodInput.value.trim();
  }
});

aiDecideBtn.addEventListener("click", () => {
  moodChips.querySelectorAll(".chip").forEach((c) => c.classList.remove("active"));
  customMoodInput.value = "";
  state.selectedMood = null; // AI Decide
  triggerRecommendation();
});

recommendBtn.addEventListener("click", () => {
  triggerRecommendation();
});

// -----------------------------------------------------------------
// Step 3: Playlist Recommendation
// -----------------------------------------------------------------

async function triggerRecommendation() {
  const payload = {
    title: state.matchedTrack.title,
    artist: state.matchedTrack.artist,
    user_mood: state.selectedMood,
    access_token: state.accessToken,
  };

  try {
    const res = await fetch("/recommend", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to generate recommendation.");
    }

    state.recommendation = await res.json();
    renderRecommendation(state.recommendation);

    recommendSection.classList.remove("hidden");
    recommendSection.scrollIntoView({ behavior: "smooth" });
  } catch (err) {
    showError(err.message);
  }
}

function renderRecommendation(rec) {
  recPlaylistName.textContent = rec.recommended_playlist;
  recAiMood.textContent = rec.ai_mood;
  recUserMood.textContent = rec.user_mood;
  recConfidence.textContent = `${Math.round(rec.confidence * 100)}%`;
  recExplanation.textContent = rec.explanation;

  if (rec.playlist_exists) {
    playlistStatusNotice.className = "banner banner-info";
    playlistStatusNotice.textContent = `✓ Playlist '${rec.recommended_playlist}' exists in your Spotify library.`;
    confirmAddBtn.textContent = `Add to "${rec.recommended_playlist}"`;
  } else {
    playlistStatusNotice.className = "banner banner-info";
    playlistStatusNotice.textContent = `✦ Playlist '${rec.recommended_playlist}' does not exist yet. It will be created for you upon confirmation.`;
    confirmAddBtn.textContent = `Create "${rec.recommended_playlist}" & Add Track`;
  }

  // Alternatives
  if (rec.alternatives && rec.alternatives.length > 0) {
    recAlternativesContainer.classList.remove("hidden");
    recAlternativesList.innerHTML = "";
    rec.alternatives.forEach((alt) => {
      const pill = document.createElement("div");
      pill.className = "alt-pill";
      pill.textContent = `${alt.playlist} (${Math.round(alt.confidence * 100)}%)`;
      pill.onclick = () => {
        state.recommendation.recommended_playlist = alt.playlist;
        state.recommendation.playlist_exists = alt.playlist_exists;
        state.recommendation.playlist_id = alt.playlist_id;
        state.recommendation.confidence = alt.confidence;
        renderRecommendation(state.recommendation);
      };
      recAlternativesList.appendChild(pill);
    });
  } else {
    recAlternativesContainer.classList.add("hidden");
  }
}

cancelRecBtn.addEventListener("click", () => {
  recommendSection.classList.add("hidden");
});

// -----------------------------------------------------------------
// Step 4: Confirm & Add to Spotify
// -----------------------------------------------------------------

confirmAddBtn.addEventListener("click", async () => {
  if (!state.accessToken) {
    showError("Please connect your Spotify account using the button at the top to add songs.");
    return;
  }

  confirmAddBtn.disabled = true;
  confirmAddBtn.textContent = "Adding...";

  const payload = {
    track_uri: state.matchedTrack.spotify_uri,
    song_id: state.matchedTrack.spotify_track_id,
    song_title: state.matchedTrack.title,
    artist: state.matchedTrack.artist,
    playlist_name: state.recommendation.recommended_playlist,
    playlist_id: state.recommendation.playlist_id,
    create_if_missing: !state.recommendation.playlist_exists,
    user_mood: state.selectedMood,
    ai_mood: state.recommendation.ai_mood,
    recommended_playlist: state.recommendation.recommended_playlist,
    access_token: state.accessToken,
  };

  try {
    const res = await fetch("/organize/add", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || "Failed to add song to Spotify.");
    }

    const data = await res.json();
    renderResult(data);

    recommendSection.classList.add("hidden");
    resultSection.classList.remove("hidden");
    resultSection.scrollIntoView({ behavior: "smooth" });
    fetchHistory();
  } catch (err) {
    showError(err.message);
  } finally {
    confirmAddBtn.disabled = false;
  }
});

function renderResult(data) {
  resSong.textContent = state.matchedTrack.title;
  resArtist.textContent = state.matchedTrack.artist;
  resAiMood.textContent = state.recommendation.ai_mood;
  resUserMood.textContent = state.selectedMood || "Auto (AI Decision)";
  resPlaylist.textContent = data.playlist_name;
  resConfidence.textContent = `${Math.round(state.recommendation.confidence * 100)}%`;

  if (data.already_exists) {
    document.getElementById("resultSubtitle").textContent = "Song was already in this playlist (duplicate prevented). History updated!";
  } else {
    document.getElementById("resultSubtitle").textContent = "Song added to your playlist and your taste profile has been updated!";
  }

  openSpotifyLink.href = data.playlist_url || data.spotify_track_url || "#";
}

organizeAnotherBtn.addEventListener("click", () => {
  youtubeUrl.value = "";
  songMatchSection.classList.add("hidden");
  moodSection.classList.add("hidden");
  recommendSection.classList.add("hidden");
  resultSection.classList.add("hidden");
  window.scrollTo({ top: 0, behavior: "smooth" });
});

// -----------------------------------------------------------------
// History Management
// -----------------------------------------------------------------

async function fetchHistory() {
  try {
    const res = await fetch("/organize/history");
    if (!res.ok) return;
    const data = await res.json();
    renderHistory(data.history || []);
  } catch (err) {
    console.error("Failed to load taste history:", err);
  }
}

function renderHistory(records) {
  if (!records || records.length === 0) {
    emptyHistoryMsg.classList.remove("hidden");
    historyTable.classList.add("hidden");
    return;
  }

  emptyHistoryMsg.classList.add("hidden");
  historyTable.classList.remove("hidden");
  historyBody.innerHTML = "";

  records.forEach((r) => {
    const row = document.createElement("tr");
    const dateFormatted = r.created_at ? new Date(r.created_at).toLocaleDateString() : "-";
    row.innerHTML = `
      <td><strong>${r.song_title}</strong></td>
      <td>${r.artist}</td>
      <td>${r.user_mood || "Auto"}</td>
      <td>${r.ai_mood}</td>
      <td><span class="confidence-pill">${r.selected_playlist}</span></td>
      <td>${dateFormatted}</td>
    `;
    historyBody.appendChild(row);
  });
}

refreshHistoryBtn.addEventListener("click", fetchHistory);

// Start
initAuth();
