// ==========================================================================
// Tubify Application Controller
// A polished, human-designed personal music organizer.
// ==========================================================================

(() => {
  'use strict';

  // State Container
  const state = {
    currentView: 'home',
    accessToken: localStorage.getItem('spotify_access_token') || null,
    refreshToken: localStorage.getItem('spotify_refresh_token') || null,
    defaultBehavior: localStorage.getItem('tubify_default_behavior') || 'ask',
    ytData: null,
    matchedTrack: null,
    candidates: [],
    selectedMood: '',
    recommendation: null,
    userPlaylists: [],
  };

  // DOM Elements: Navigation
  const navBtns = document.querySelectorAll('.nav-btn');
  const views = {
    home: document.getElementById('viewHome'),
    history: document.getElementById('viewHistory'),
    settings: document.getElementById('viewSettings'),
  };
  const authBtn = document.getElementById('authBtn');
  const authLabel = document.getElementById('authLabel');

  // DOM Elements: Home Stages
  const landingStage = document.getElementById('landingStage');
  const analyzeForm = document.getElementById('analyzeForm');
  const urlInput = document.getElementById('urlInput');
  const analyzeSubmitBtn = document.getElementById('analyzeSubmitBtn');

  // Inline Progress
  const analysisProgress = document.getElementById('analysisProgress');
  const progressMessage = document.getElementById('progressMessage');
  const dotYt = document.getElementById('dotYt');
  const dotSpot = document.getElementById('dotSpot');
  const dotMood = document.getElementById('dotMood');

  // Song Match Stage
  const songStage = document.getElementById('songStage');
  const trackArtwork = document.getElementById('trackArtwork');
  const trackTitle = document.getElementById('trackTitle');
  const trackArtist = document.getElementById('trackArtist');
  const trackMeta = document.getElementById('trackMeta');
  const useTrackBtn = document.getElementById('useTrackBtn');
  const toggleCandidatesBtn = document.getElementById('toggleCandidatesBtn');
  const candidateList = document.getElementById('candidateList');

  // Mood Stage
  const moodStage = document.getElementById('moodStage');
  const customVibeInput = document.getElementById('customVibeInput');
  const moodChipGroup = document.getElementById('moodChipGroup');
  const autoDecideBtn = document.getElementById('autoDecideBtn');
  const confirmMoodBtn = document.getElementById('confirmMoodBtn');

  // Recommendation & Permission Stage
  const recommendStage = document.getElementById('recommendStage');
  const recVibeHeader = document.getElementById('recVibeHeader');
  const recTargetPlaylist = document.getElementById('recTargetPlaylist');
  const recReason = document.getElementById('recReason');
  const recSubtleMatch = document.getElementById('recSubtleMatch');
  const recAlternativesWrapper = document.getElementById('recAlternativesWrapper');
  const altChips = document.getElementById('altChips');

  const confirmExistingBlock = document.getElementById('confirmExistingBlock');
  const createMissingBlock = document.getElementById('createMissingBlock');
  const confirmPlName = document.getElementById('confirmPlName');
  const missingPlName = document.getElementById('missingPlName');
  const miniArtwork = document.getElementById('miniArtwork');
  const miniTitle = document.getElementById('miniTitle');
  const miniArtist = document.getElementById('miniArtist');
  const cancelAddBtn = document.getElementById('cancelAddBtn');
  const submitAddBtn = document.getElementById('submitAddBtn');
  const chooseAnotherBtn = document.getElementById('chooseAnotherBtn');
  const createAndAddBtn = document.getElementById('createAndAddBtn');

  // Success Stage
  const successStage = document.getElementById('successStage');
  const successTitle = document.getElementById('successTitle');
  const successArtist = document.getElementById('successArtist');
  const successPlaylist = document.getElementById('successPlaylist');
  const openSpotifyBtn = document.getElementById('openSpotifyBtn');
  const addAnotherBtn = document.getElementById('addAnotherBtn');

  // History & Settings Elements
  const historyList = document.getElementById('historyList');
  const historyEmpty = document.getElementById('historyEmpty');
  const settingsConnLabel = document.getElementById('settingsConnLabel');
  const settingsAuthBtn = document.getElementById('settingsAuthBtn');
  const clearHistoryBtn = document.getElementById('clearHistoryBtn');
  const radioBehaviors = document.querySelectorAll('input[name="defaultBehavior"]');

  // Modal
  const choosePlaylistModal = document.getElementById('choosePlaylistModal');
  const modalPlaylistList = document.getElementById('modalPlaylistList');
  const modalCloseBtn = document.getElementById('modalCloseBtn');
  const toastContainer = document.getElementById('toastContainer');

  // ==========================================================================
  // Helper: Friendly Toast
  // ==========================================================================
  function showToast(message, type = 'info') {
    const el = document.createElement('div');
    el.className = `toast toast-${type}`;
    el.textContent = message;
    toastContainer.appendChild(el);
    setTimeout(() => {
      el.style.opacity = '0';
      el.style.transform = 'translateY(8px)';
      setTimeout(() => el.remove(), 250);
    }, 4000);
  }

  // Convert technical errors to polite human messages
  function humanizeError(err) {
    const msg = (err && err.message) || String(err || '');
    if (msg.includes('401') || msg.includes('token') || msg.includes('expired')) {
      return 'Spotify connection expired. Please reconnect.';
    }
    if (msg.includes('404') || msg.includes('private') || msg.includes('unavailable')) {
      return 'Video could not be accessed. Please ensure the link is public.';
    }
    if (msg.includes('Invalid YouTube URL')) {
      return 'Please enter a valid YouTube video link.';
    }
    if (msg.includes('already_exists')) {
      return 'This track is already in your playlist.';
    }
    return msg || 'Something went wrong. Please try again.';
  }

  // ==========================================================================
  // Navigation & View Routing
  // ==========================================================================
  function switchView(viewName) {
    state.currentView = viewName;
    navBtns.forEach((btn) => {
      btn.classList.toggle('active', btn.dataset.view === viewName);
    });
    Object.keys(views).forEach((k) => {
      views[k].classList.toggle('active', k === viewName);
      views[k].classList.toggle('hidden', k !== viewName);
    });

    if (viewName === 'history') {
      loadHistory();
    } else if (viewName === 'settings') {
      updateSettingsUI();
    }
  }

  navBtns.forEach((btn) => {
    btn.addEventListener('click', () => switchView(btn.dataset.view));
  });

  // ==========================================================================
  // Auth Lifecycle
  // ==========================================================================
  function checkUrlForAuthTokens() {
    const params = new URLSearchParams(window.location.search);
    const token = params.get('access_token');
    const refresh = params.get('refresh_token');

    if (token) {
      state.accessToken = token;
      localStorage.setItem('spotify_access_token', token);
      if (refresh) {
        state.refreshToken = refresh;
        localStorage.setItem('spotify_refresh_token', refresh);
      }
      showToast('Spotify connected.', 'success');
      window.history.replaceState({}, document.title, window.location.pathname);
    }
    updateAuthDisplay();
  }

  function updateAuthDisplay() {
    const isConnected = Boolean(state.accessToken);
    if (isConnected) {
      authBtn.className = 'status-btn connected';
      authLabel.textContent = 'Spotify connected';
      settingsConnLabel.textContent = 'Connected to Spotify';
      settingsAuthBtn.textContent = 'Disconnect';
      fetchUserPlaylists();
    } else {
      authBtn.className = 'status-btn disconnected';
      authLabel.textContent = 'Connect Spotify';
      settingsConnLabel.textContent = 'Disconnected';
      settingsAuthBtn.textContent = 'Connect Spotify';
    }
  }

  authBtn.addEventListener('click', handleAuthClick);
  settingsAuthBtn.addEventListener('click', handleAuthClick);

  function handleAuthClick() {
    if (state.accessToken) {
      // Disconnect
      state.accessToken = null;
      state.refreshToken = null;
      localStorage.removeItem('spotify_access_token');
      localStorage.removeItem('spotify_refresh_token');
      updateAuthDisplay();
      showToast('Disconnected from Spotify.', 'info');
    } else {
      window.location.href = '/auth/spotify/login';
    }
  }

  async function fetchUserPlaylists() {
    if (!state.accessToken) return;
    try {
      const res = await fetch('/spotify/playlists', {
        headers: { Authorization: `Bearer ${state.accessToken}` },
      });
      if (res.ok) {
        const data = await res.json();
        state.userPlaylists = data.playlists || [];
      }
    } catch (_) {
      // Quiet background failure
    }
  }

  // ==========================================================================
  // Inline Progress Helpers
  // ==========================================================================
  function setProgressState(phase) {
    analysisProgress.classList.remove('hidden');
    if (phase === 1) {
      progressMessage.textContent = 'Finding song';
      dotYt.innerHTML = '● <span class="step-label">YouTube</span>';
      dotYt.className = 'step-indicator active';
      dotSpot.innerHTML = '○ <span class="step-label">Spotify</span>';
      dotSpot.className = 'step-indicator';
      dotMood.innerHTML = '○ <span class="step-label">Mood</span>';
      dotMood.className = 'step-indicator';
    } else if (phase === 2) {
      progressMessage.textContent = 'Matching song';
      dotYt.innerHTML = '● <span class="step-label">YouTube</span>';
      dotYt.className = 'step-indicator complete';
      dotSpot.innerHTML = '● <span class="step-label">Spotify</span>';
      dotSpot.className = 'step-indicator active';
      dotMood.innerHTML = '○ <span class="step-label">Mood</span>';
      dotMood.className = 'step-indicator';
    } else if (phase === 3) {
      progressMessage.textContent = 'Preparing recommendation';
      dotYt.innerHTML = '● <span class="step-label">YouTube</span>';
      dotYt.className = 'step-indicator complete';
      dotSpot.innerHTML = '● <span class="step-label">Spotify</span>';
      dotSpot.className = 'step-indicator complete';
      dotMood.innerHTML = '● <span class="step-label">Mood</span>';
      dotMood.className = 'step-indicator active';
    }
  }

  function hideProgress() {
    analysisProgress.classList.add('hidden');
  }

  // ==========================================================================
  // Stage 1: Analyze YouTube URL
  // ==========================================================================
  analyzeForm.addEventListener('submit', async (e) => {
    e.preventDefault();
    const url = urlInput.value.trim();
    if (!url) return;

    analyzeSubmitBtn.disabled = true;
    setProgressState(1);

    // Hide subsequent stages during fresh search
    songStage.classList.add('hidden');
    moodStage.classList.add('hidden');
    recommendStage.classList.add('hidden');
    successStage.classList.add('hidden');

    try {
      // 1. YouTube metadata extraction
      const ytRes = await fetch('/analyze', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ youtube_url: url }),
      });

      if (!ytRes.ok) {
        const err = await ytRes.json();
        throw new Error(err.detail || 'Could not analyze YouTube video.');
      }

      state.ytData = await ytRes.json();

      // 2. Spotify Matching
      setProgressState(2);
      const searchRes = await fetch('/spotify/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          title: state.ytData.title,
          artist: state.ytData.artist,
          access_token: state.accessToken,
        }),
      });

      if (!searchRes.ok) {
        const err = await searchRes.json();
        throw new Error(err.detail || 'Spotify search failed.');
      }

      const searchData = await searchRes.json();
      if (!searchData.matched || !searchData.track) {
        throw new Error(`No match found on Spotify for "${state.ytData.title}".`);
      }

      state.matchedTrack = searchData.track;
      state.candidates = searchData.candidates || [];

      // Complete progress & reveal song card
      hideProgress();
      renderSongCard(state.matchedTrack, state.candidates);

      songStage.classList.remove('hidden');
      songStage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
      hideProgress();
      showToast(humanizeError(err), 'error');
    } finally {
      analyzeSubmitBtn.disabled = false;
    }
  });

  function renderSongCard(track, candidates) {
    trackArtwork.src = track.album_art || state.ytData.thumbnail_url || '';
    trackTitle.textContent = track.title;
    trackArtist.textContent = track.artist;
    trackMeta.textContent = `Spotify match · ${Math.round(track.confidence * 100)}% confidence`;

    // Candidate list setup
    if (candidates && candidates.length > 1) {
      toggleCandidatesBtn.classList.remove('hidden');
      candidateList.innerHTML = '';
      candidates.forEach((cand) => {
        const item = document.createElement('div');
        item.className = 'candidate-item';
        item.innerHTML = `
          <div>
            <div class="cand-title">${cand.title}</div>
            <div class="cand-artist">${cand.artist} · ${cand.album}</div>
          </div>
          <span class="cand-conf">${Math.round(cand.confidence * 100)}%</span>
        `;
        item.addEventListener('click', () => {
          state.matchedTrack = cand;
          renderSongCard(cand, candidates);
          candidateList.classList.add('hidden');
          showToast(`Selected "${cand.title}"`, 'info');
        });
        candidateList.appendChild(item);
      });
    } else {
      toggleCandidatesBtn.classList.add('hidden');
      candidateList.classList.add('hidden');
    }
  }

  toggleCandidatesBtn.addEventListener('click', () => {
    candidateList.classList.toggle('hidden');
  });

  // ==========================================================================
  // Stage 2: Confirm Track -> Mood Interaction
  // ==========================================================================
  useTrackBtn.addEventListener('click', () => {
    moodStage.classList.remove('hidden');
    moodStage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  });

  // Mood Chips Selection
  moodChipGroup.querySelectorAll('.mood-chip').forEach((chip) => {
    chip.addEventListener('click', () => {
      moodChipGroup.querySelectorAll('.mood-chip').forEach((c) => c.classList.remove('active'));
      chip.classList.add('active');
      state.selectedMood = chip.dataset.mood;
      customVibeInput.value = '';
    });
  });

  customVibeInput.addEventListener('input', () => {
    if (customVibeInput.value.trim()) {
      moodChipGroup.querySelectorAll('.mood-chip').forEach((c) => c.classList.remove('active'));
      state.selectedMood = customVibeInput.value.trim();
    }
  });

  autoDecideBtn.addEventListener('click', () => {
    moodChipGroup.querySelectorAll('.mood-chip').forEach((c) => c.classList.remove('active'));
    customVibeInput.value = '';
    state.selectedMood = '';
    generateRecommendation();
  });

  confirmMoodBtn.addEventListener('click', () => {
    generateRecommendation();
  });

  // ==========================================================================
  // Stage 3: Recommendation
  // ==========================================================================
  async function generateRecommendation() {
    confirmMoodBtn.disabled = true;

    const payload = {
      title: state.matchedTrack.title,
      artist: state.matchedTrack.artist,
      user_mood: state.selectedMood || null,
      access_token: state.accessToken,
    };

    try {
      const res = await fetch('/recommend', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Could not generate recommendation.');
      }

      state.recommendation = await res.json();
      renderRecommendation(state.recommendation);

      recommendStage.classList.remove('hidden');
      recommendStage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
      showToast(humanizeError(err), 'error');
    } finally {
      confirmMoodBtn.disabled = false;
    }
  }

  function renderRecommendation(rec) {
    recVibeHeader.textContent = `Feels like: ${rec.ai_mood}`;
    recTargetPlaylist.textContent = rec.recommended_playlist;
    recReason.textContent = rec.explanation || "Matches the mood and rhythm of this track.";
    recSubtleMatch.textContent = `${Math.round(rec.confidence * 100)}% match`;

    // Mini song preview
    miniArtwork.src = state.matchedTrack.album_art || state.ytData.thumbnail_url || '';
    miniTitle.textContent = state.matchedTrack.title;
    miniArtist.textContent = state.matchedTrack.artist;

    // Alternative pills
    if (rec.alternatives && rec.alternatives.length > 0) {
      recAlternativesWrapper.classList.remove('hidden');
      altChips.innerHTML = '';
      rec.alternatives.forEach((alt) => {
        const pill = document.createElement('button');
        pill.type = 'button';
        pill.className = 'alt-pill';
        pill.textContent = alt.playlist;
        pill.addEventListener('click', () => {
          rec.recommended_playlist = alt.playlist;
          rec.playlist_exists = alt.playlist_exists;
          rec.playlist_id = alt.playlist_id;
          rec.confidence = alt.confidence;
          renderRecommendation(rec);
        });
        altChips.appendChild(pill);
      });
    } else {
      recAlternativesWrapper.classList.add('hidden');
    }

    // Toggle Permission Block State (Exists vs. Missing)
    if (rec.playlist_exists) {
      confirmExistingBlock.classList.remove('hidden');
      createMissingBlock.classList.add('hidden');
      confirmPlName.textContent = rec.recommended_playlist;
    } else {
      confirmExistingBlock.classList.add('hidden');
      createMissingBlock.classList.remove('hidden');
      missingPlName.textContent = rec.recommended_playlist;
    }
  }

  cancelAddBtn.addEventListener('click', () => {
    recommendStage.classList.add('hidden');
  });

  // Choose another playlist modal
  chooseAnotherBtn.addEventListener('click', () => {
    openChoosePlaylistModal();
  });

  function openChoosePlaylistModal() {
    modalPlaylistList.innerHTML = '';
    if (!state.userPlaylists || state.userPlaylists.length === 0) {
      modalPlaylistList.innerHTML = '<p style="color:var(--text-subtle);padding:10px 0;">No playlists found in your library.</p>';
    } else {
      state.userPlaylists.forEach((pl) => {
        const item = document.createElement('div');
        item.className = 'modal-playlist-item';
        item.textContent = pl.name;
        item.addEventListener('click', () => {
          state.recommendation.recommended_playlist = pl.name;
          state.recommendation.playlist_id = pl.id;
          state.recommendation.playlist_exists = true;
          renderRecommendation(state.recommendation);
          choosePlaylistModal.classList.add('hidden');
        });
        modalPlaylistList.appendChild(item);
      });
    }
    choosePlaylistModal.classList.remove('hidden');
  }

  modalCloseBtn.addEventListener('click', () => {
    choosePlaylistModal.classList.add('hidden');
  });

  // ==========================================================================
  // Stage 4: Execute Add to Spotify
  // ==========================================================================
  submitAddBtn.addEventListener('click', () => executeAddTrack(false));
  createAndAddBtn.addEventListener('click', () => executeAddTrack(true));

  async function executeAddTrack(isCreating) {
    if (!state.accessToken) {
      showToast('Please connect your Spotify account first.', 'error');
      return;
    }

    const btn = isCreating ? createAndAddBtn : submitAddBtn;
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = 'Saving...';

    const payload = {
      track_uri: state.matchedTrack.spotify_uri,
      song_id: state.matchedTrack.spotify_track_id,
      song_title: state.matchedTrack.title,
      artist: state.matchedTrack.artist,
      playlist_name: state.recommendation.recommended_playlist,
      playlist_id: state.recommendation.playlist_id,
      create_if_missing: isCreating,
      user_mood: state.selectedMood || null,
      ai_mood: state.recommendation.ai_mood,
      recommended_playlist: state.recommendation.recommended_playlist,
      access_token: state.accessToken,
    };

    try {
      const res = await fetch('/organize/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        const err = await res.json();
        throw new Error(err.detail || 'Failed to add song to Spotify.');
      }

      const result = await res.json();
      renderSuccess(result);

      recommendStage.classList.add('hidden');
      successStage.classList.remove('hidden');
      successStage.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    } catch (err) {
      showToast(humanizeError(err), 'error');
    } finally {
      btn.disabled = false;
      btn.textContent = originalText;
    }
  }

  function renderSuccess(res) {
    successTitle.textContent = state.matchedTrack.title;
    successArtist.textContent = state.matchedTrack.artist;
    successPlaylist.textContent = res.playlist_name;
    openSpotifyBtn.href = res.playlist_url || res.spotify_track_url || 'https://open.spotify.com';
  }

  addAnotherBtn.addEventListener('click', () => {
    urlInput.value = '';
    songStage.classList.add('hidden');
    moodStage.classList.add('hidden');
    recommendStage.classList.add('hidden');
    successStage.classList.add('hidden');
    window.scrollTo({ top: 0, behavior: 'smooth' });
    urlInput.focus();
  });

  // ==========================================================================
  // View 2: History Loader
  // ==========================================================================
  async function loadHistory() {
    try {
      const res = await fetch('/organize/history');
      if (!res.ok) return;
      const data = await res.json();
      renderHistoryList(data.history || []);
    } catch (_) {
      // Quiet fail
    }
  }

  function renderHistoryList(items) {
    if (!items || items.length === 0) {
      historyEmpty.classList.remove('hidden');
      historyList.innerHTML = '';
      return;
    }

    historyEmpty.classList.add('hidden');
    historyList.innerHTML = '';

    items.forEach((item) => {
      const el = document.createElement('a');
      el.className = 'history-row';
      el.href = `https://open.spotify.com/track/${item.song_id}`;
      el.target = '_blank';
      el.rel = 'noopener';

      const dateStr = item.created_at ? formatRelativeDate(item.created_at) : '';

      el.innerHTML = `
        <div class="history-track-part">
          <span class="hist-title">${item.song_title}</span>
          <span class="hist-artist">${item.artist}</span>
        </div>
        <div class="history-meta-part">
          <span class="hist-pill">${item.selected_playlist}</span>
          <span class="hist-pill">${item.ai_mood}</span>
          <span class="hist-date">${dateStr}</span>
        </div>
      `;
      historyList.appendChild(el);
    });
  }

  function formatRelativeDate(isoStr) {
    const d = new Date(isoStr);
    const now = new Date();
    const diffDays = Math.floor((now - d) / (1000 * 60 * 60 * 24));
    if (diffDays === 0) return 'Today';
    if (diffDays === 1) return 'Yesterday';
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  }

  // ==========================================================================
  // View 3: Settings Manager
  // ==========================================================================
  function updateSettingsUI() {
    radioBehaviors.forEach((r) => {
      r.checked = r.value === state.defaultBehavior;
    });
  }

  radioBehaviors.forEach((radio) => {
    radio.addEventListener('change', () => {
      state.defaultBehavior = radio.value;
      localStorage.setItem('tubify_default_behavior', radio.value);
      showToast('Preference saved.', 'info');
    });
  });

  clearHistoryBtn.addEventListener('click', async () => {
    if (!confirm('Are you sure you want to clear your local taste history?')) return;
    try {
      const res = await fetch('/organize/history', { method: 'DELETE' });
      if (res.ok) {
        showToast('Local taste history cleared.', 'success');
        if (state.currentView === 'history') {
          loadHistory();
        }
      }
    } catch (_) {
      showToast('Could not clear history.', 'error');
    }
  });

  // Initialization
  checkUrlForAuthTokens();
})();
