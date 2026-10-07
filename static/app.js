// Tubify State Machine
const state = {
  accessToken: localStorage.getItem("spotify_access_token") || null,
  refreshToken: localStorage.getItem("spotify_refresh_token") || null,
  isDemoMode: localStorage.getItem("tubify_demo_mode") === "true",
  ytSong: null,
  matchedTrack: null,
  candidates: [],
  selectedMood: null,
  recommendation: null,
  userPlaylists: [],
};

// DOM References
const authStatus = document.getElementById("authStatus");
const authBtn = document.getElementById("authBtn");
const demoModeToggle = document.getElementById("demoModeToggle");
const urlForm = document.getElementById("urlForm");
const youtubeUrl = document.getElementById("youtubeUrl");
const analyzeBtn = document.getElementById("analyzeBtn");
const analyzeSpinner = document.getElementById("analyzeSpinner");

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
const trackAudio = document.getElementById("trackAudio");
const audioPreviewWrapper = document.getElementById("audioPreviewWrapper");
const candidatesContainer = document.getElementById("candidatesContainer");
const candidatesList = document.getElementById("candidatesList");
const toggleCandidatesBtn = document.getElementById("toggleCandidatesBtn");
const confirmMatchBtn = document.getElementById("confirmMatchBtn");

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
const manualPlaylistSelect = document.getElementById("manualPlaylistSelect");
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
const toastContainer = document.getElementById("toastContainer");

// -----------------------------------------------------------------
// Toast Notifications
// -----------------------------------------------------------------

function showToast(message, type = "info") {
  const toast = document.createElement("div");
  toast.className = `toast toast-${type}`;
  toast.textContent = message;
  toastContainer.appendChild(toast);
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4500);
}

// -----------------------------------------------------------------
// Initialization & Auth
// -----------------------------------------------------------------

function init() {
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
    showToast("Spotify connected successfully!", "success");
    window.history.replaceState({}, document.title, window.location.pathname);
  }

  updateAuthUI();
  updateDemoModeUI();
  fetchHistory();
  setupSampleChips();
  if (state.accessToken && !state.isDemoMode) {
    fetchUserPlaylists();
  }
}

function updateAuthUI() {
  if (state.isDemoMode) {
    authStatus.textContent = "Demo Mock Active";
    authStatus.className = "auth-badge connected";
    authBtn.textContent = "Use Real Spotify";
    authBtn.onclick = () => toggleDemoMode(false);
  } else if (state.accessToken) {
    authStatus.textContent = "Spotify Connected";
    authStatus.className = "auth-badge connected";
    authBtn.textContent = "Disconnect";
    authBtn.onclick = () => {
      localStorage.removeItem("spotify_access_token");
      localStorage.removeItem("spotify_refresh_token");
      state.accessToken = null;
      state.refreshToken = null;
      updateAuthUI();
      showToast("Disconnected from Spotify.", "info");
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

function toggleDemoMode(forceVal) {
  state.isDemoMode = forceVal !== undefined ? forceVal : !state.isDemoMode;
  localStorage.setItem("tubify_demo_mode", state.isDemoMode);
  updateDemoModeUI();
  updateAuthUI();
  showToast(
    state.isDemoMode
      ? "Demo mode active! You can test the entire workflow with simulated Spotify data."
      : "Demo mode disabled. Live Spotify API will be used.",
    "info"
  );
}

function updateDemoModeUI() {
  if (state.isDemoMode) {
    demoModeToggle.classList.add("active");
  } else {
    demoModeToggle.classList.remove("active");
  }
}

demoModeToggle.addEventListener("click", () => toggleDemoMode());

// Quick sample links
function setupSampleChips() {
  document.querySelectorAll(".sample-chip").forEach((chip) => {
    chip.addEventListener("click", () => {
      youtubeUrl.value = chip.dataset.url;
      urlForm.dispatchEvent(new Event("submit"));
    });
  });
}

// -----------------------------------------------------------------
// Step 1: Analyze Video & Spotify Search
// -----------------------------------------------------------------

urlForm.addEventListener("submit", async (e) => {
  e.preventDefault();
  const url = youtubeUrl.value.trim();
  if (!url) return;

  analyzeBtn.disabled = true;
  analyzeSpinner.classList.remove("hidden");
  analyzeBtn.querySelector(".btn-text").textContent = "Analyzing...";

  try {
    // 1. YouTube metadata extraction
    const ytRes = await fetch("/analyze", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ youtube_url: url }),
    });

    if (!ytRes.ok) {
      const err = await ytRes.json();
      throw new Error(err.detail || "Failed to extract YouTube video information.");
    }

    state.ytSong = await ytRes.json();
    renderYouTubeCard(state.ytSong);

    // 2. Spotify Track Search
    if (state.isDemoMode) {
      // Simulated Demo Track
      state.matchedTrack = {
        spotify_track_id: state.ytSong.video_id,
        spotify_uri: `spotify:track:${state.ytSong.video_id}`,
        title: state.ytSong.title,
        artist: state.ytSong.artist,
        album: `${state.ytSong.artist} - Single`,
        album_art: state.ytSong.thumbnail_url,
        spotify_url: `https://open.spotify.com/track/${state.ytSong.video_id}`,
        preview_url: null,
        confidence: 0.94,
      };
      state.candidates = [state.matchedTrack];
    } else {
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
        // Fallback to demo mode suggestion if credentials missing
        if (err.detail && err.detail.includes("credentials")) {
          showToast("Spotify API keys not configured. Switched to Demo Mode automatically!", "info");
          toggleDemoMode(true);
          return urlForm.dispatchEvent(new Event("submit"));
        }
        throw new Error(err.detail || "Spotify search failed.");
      }

      const searchData = await searchRes.json();
      if (!searchData.matched || !searchData.track) {
        throw new Error(`No matching track found on Spotify for "${state.ytSong.title}" by ${state.ytSong.artist}.`);
      }

      state.matchedTrack = searchData.track;
      state.candidates = searchData.candidates || [];
    }

    renderSpotifyCard(state.matchedTrack, state.candidates);

    songMatchSection.classList.remove("hidden");
    moodSection.classList.add("hidden");
    recommendSection.classList.add("hidden");
    resultSection.classList.add("hidden");
    songMatchSection.scrollIntoView({ behavior: "smooth" });

  } catch (err) {
    showToast(err.message, "error");
  } finally {
    analyzeBtn.disabled = false;
    analyzeSpinner.classList.add("hidden");
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
  spotCover.src = track.album_art || state.ytSong.thumbnail_url || "";
  spotTitle.textContent = track.title;
  spotArtist.textContent = track.artist;
  spotAlbum.textContent = track.album;
  spotConfidencePill.textContent = `Match Confidence: ${Math.round(track.confidence * 100)}%`;

  // Audio preview player
  if (track.preview_url) {
    audioPreviewWrapper.classList.remove("hidden");
    trackAudio.src = track.preview_url;
  } else {
    audioPreviewWrapper.classList.add("hidden");
    trackAudio.pause();
  }

  // Populate candidates
  if (candidates.length > 1) {
    toggleCandidatesBtn.classList.remove("hidden");
    candidatesList.innerHTML = "";
    candidates.forEach((cand) => {
      const item = document.createElement("div");
      item.className = "candidate-item";
      item.innerHTML = `
        <div>
          <strong>${cand.title}</strong> - ${cand.artist} <small style="color:var(--text-muted)">(${cand.album})</small>
        </div>
        <span class="confidence-pill">${Math.round(cand.confidence * 100)}%</span>
      `;
      item.onclick = () => {
        state.matchedTrack = cand;
        renderSpotifyCard(cand, candidates);
        candidatesContainer.classList.add("hidden");
        showToast(`Switched match to "${cand.title}"`, "info");
      };
      candidatesList.appendChild(item);
    });
  } else {
    toggleCandidatesBtn.classList.add("hidden");
    candidatesContainer.classList.add("hidden");
  }
}

toggleCandidatesBtn.addEventListener("click", () => {
  candidatesContainer.classList.toggle("hidden");
});

// -----------------------------------------------------------------
// Step 2: Confirm Match & Show Mood Selection
// -----------------------------------------------------------------

confirmMatchBtn.addEventListener("click", () => {
  moodSection.classList.remove("hidden");
  moodSection.scrollIntoView({ behavior: "smooth" });
});

// Mood chips
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
  state.selectedMood = null;
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
    access_token: state.isDemoMode ? null : state.accessToken,
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
    showToast(err.message, "error");
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
    playlistStatusNotice.textContent = `✓ Playlist '${rec.recommended_playlist}' found in your library. Ready to add.`;
    confirmAddBtn.textContent = `Add to "${rec.recommended_playlist}"`;
  } else {
    playlistStatusNotice.className = "banner banner-info";
    playlistStatusNotice.textContent = `✦ Playlist '${rec.recommended_playlist}' does not exist in your library yet. It will be created upon confirmation.`;
    confirmAddBtn.textContent = `Create "${rec.recommended_playlist}" & Add Track`;
  }

  // Populate manual override dropdown
  populatePlaylistDropdown(rec.recommended_playlist);

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
        showToast(`Selected alternative '${alt.playlist}'`, "info");
      };
      recAlternativesList.appendChild(pill);
    });
  } else {
    recAlternativesContainer.classList.add("hidden");
  }
}

function populatePlaylistDropdown(recommendedName) {
  manualPlaylistSelect.innerHTML = `<option value="">-- Use "${recommendedName}" --</option>`;
  if (state.userPlaylists && state.userPlaylists.length > 0) {
    state.userPlaylists.forEach((pl) => {
      const opt = document.createElement("option");
      opt.value = pl.name;
      opt.textContent = `${pl.name} (${pl.total_tracks} tracks)`;
      opt.dataset.id = pl.id;
      manualPlaylistSelect.appendChild(opt);
    });
  }
}

manualPlaylistSelect.addEventListener("change", () => {
  const chosenName = manualPlaylistSelect.value;
  if (!chosenName) return;

  const chosenOpt = manualPlaylistSelect.options[manualPlaylistSelect.selectedIndex];
  state.recommendation.recommended_playlist = chosenName;
  state.recommendation.playlist_exists = true;
  state.recommendation.playlist_id = chosenOpt.dataset.id || null;
  state.recommendation.confidence = 0.99;
  state.recommendation.explanation = `Manually selected by user.`;
  renderRecommendation(state.recommendation);
});

cancelRecBtn.addEventListener("click", () => {
  recommendSection.classList.add("hidden");
});

// -----------------------------------------------------------------
// Step 4: Confirm & Add to Spotify
// -----------------------------------------------------------------

confirmAddBtn.addEventListener("click", async () => {
  if (!state.accessToken && !state.isDemoMode) {
    showToast("Please connect your Spotify account using the button at the top to add songs, or toggle Demo Mode.", "error");
    return;
  }

  confirmAddBtn.disabled = true;
  confirmAddBtn.textContent = "Adding...";

  if (state.isDemoMode) {
    // Simulated add in demo mode
    setTimeout(() => {
      const simulatedResult = {
        success: true,
        already_exists: false,
        message: "Simulated track added in Demo Mode.",
        playlist_name: state.recommendation.recommended_playlist,
        playlist_id: "demo_playlist_id",
        playlist_url: state.matchedTrack.spotify_url,
        spotify_track_url: state.matchedTrack.spotify_url,
      };
      renderResult(simulatedResult);
      recommendSection.classList.add("hidden");
      resultSection.classList.remove("hidden");
      resultSection.scrollIntoView({ behavior: "smooth" });
      confirmAddBtn.disabled = false;
      showToast("Song organized successfully in Demo Mode!", "success");
    }, 600);
    return;
  }

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
    showToast(`Added to "${data.playlist_name}"!`, "success");
  } catch (err) {
    showToast(err.message, "error");
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
// History & User Playlists
// -----------------------------------------------------------------

async function fetchUserPlaylists() {
  try {
    const res = await fetch("/spotify/playlists", {
      headers: { Authorization: `Bearer ${state.accessToken}` },
    });
    if (res.ok) {
      const data = await res.json();
      state.userPlaylists = data.playlists || [];
    }
  } catch (err) {
    console.warn("Could not fetch user playlists:", err);
  }
}

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
      <td><span class="badge" style="background:#232834;color:#cbd5e1;position:static">${r.ai_mood}</span></td>
      <td><span class="confidence-pill">${r.selected_playlist}</span></td>
      <td style="color:var(--text-muted);font-family:var(--font-mono);font-size:0.75rem">${dateFormatted}</td>
    `;
    historyBody.appendChild(row);
  });
}

refreshHistoryBtn.addEventListener("click", () => {
  fetchHistory();
  showToast("Taste history refreshed.", "info");
});

// Start
init();
