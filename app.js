/**
 * 샬롬 말씀 아카이브 검색 - Client-side Search, Filtering & Player Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // Data Store
  let allSermons = [];
  let filteredSermons = [];
  let displayedCount = 30; // Batch load size for UI performance
  const PAGE_SIZE = 30;

  // Playlist Data Store
  let allPlaylists = [];
  let filteredPlaylists = [];
  let activePlaylistId = null;

  // View Mode State
  let currentViewMode = 'list'; // 'card' | 'list'
  let currentTabMode = 'all'; // 'all' | 'playlists'

  // DOM Elements - Navigation Tabs
  const tabAllSermons = document.getElementById('tabAllSermons');
  const tabPlaylists = document.getElementById('tabPlaylists');
  const playlistTabBadge = document.getElementById('playlistTabBadge');
  const allSermonsView = document.getElementById('allSermonsView');
  const playlistsView = document.getElementById('playlistsView');

  // DOM Elements - All Sermons
  const btnViewCard = document.getElementById('btnViewCard');
  const btnViewList = document.getElementById('btnViewList');
  const searchInput = document.getElementById('searchInput');
  const clearSearchBtn = document.getElementById('clearSearchBtn');
  const startDateInput = document.getElementById('startDate');
  const endDateInput = document.getElementById('endDate');
  const ytOnlyFilter = document.getElementById('ytOnlyFilter');
  const presetBtns = document.querySelectorAll('.preset-btn');
  const resetFiltersBtn = document.getElementById('resetFiltersBtn');
  const sortOrderSelect = document.getElementById('sortOrder');

  const headerTotalCount = document.getElementById('totalCount');
  const matchedCountEl = document.getElementById('matchedCount');
  const activeFilterBadge = document.getElementById('activeFilterBadge');
  const sermonListEl = document.getElementById('sermonList');
  const loadingSpinner = document.getElementById('loadingSpinner');
  const paginationWrapper = document.getElementById('paginationWrapper');
  const loadMoreBtn = document.getElementById('loadMoreBtn');
  const remainingCountEl = document.getElementById('remainingCount');

  // DOM Elements - Playlists Mode
  const plTotalCount = document.getElementById('plTotalCount');
  const plSearchInput = document.getElementById('plSearchInput');
  const clearPlSearchBtn = document.getElementById('clearPlSearchBtn');
  const playlistItemsList = document.getElementById('playlistItemsList');
  const activePlTitle = document.getElementById('activePlTitle');
  const activePlMeta = document.getElementById('activePlMeta');
  const activePlShareBtn = document.getElementById('activePlShareBtn');
  const activePlYtLink = document.getElementById('activePlYtLink');
  const plVideoSearchInput = document.getElementById('plVideoSearchInput');
  const plSortOrder = document.getElementById('plSortOrder');
  const playlistVideoList = document.getElementById('playlistVideoList');





  // View Mode Toggle Listeners
  if (btnViewCard && btnViewList) {
    btnViewCard.addEventListener('click', () => {
      if (currentViewMode === 'card') return;
      currentViewMode = 'card';
      btnViewCard.classList.add('active');
      btnViewList.classList.remove('active');
      sermonListEl.classList.remove('list-view');
      renderSermons();
    });

    btnViewList.addEventListener('click', () => {
      if (currentViewMode === 'list') return;
      currentViewMode = 'list';
      btnViewList.classList.add('active');
      btnViewCard.classList.remove('active');
      sermonListEl.classList.add('list-view');
      renderSermons();
    });
  }

  // Audio Player Elements
  const audioPlayerBar = document.getElementById('audioPlayerBar');
  const globalAudio = document.getElementById('globalAudio');
  const playerTitle = document.getElementById('playerTitle');
  const playerMeta = document.getElementById('playerMeta');
  const btnPlayPause = document.getElementById('btnPlayPause');
  const btnRewind = document.getElementById('btnRewind');
  const btnForward = document.getElementById('btnForward');
  const btnMute = document.getElementById('btnMute');
  const btnClosePlayer = document.getElementById('btnClosePlayer');
  const currentTimeEl = document.getElementById('currentTime');
  const totalDurationEl = document.getElementById('totalDuration');
  const progressBarWrapper = document.getElementById('progressBarWrapper');
  const progressBarFill = document.getElementById('progressBarFill');
  const playerDownloadLink = document.getElementById('playerDownloadLink');

  // YouTube Modal Elements
  const youtubeModal = document.getElementById('youtubeModal');
  const modalVideoTitle = document.getElementById('modalVideoTitle');
  const youtubeIframe = document.getElementById('youtubeIframe');
  const closeModalBtn = document.getElementById('closeModalBtn');

  // Scripture Modal Elements
  const scriptureModal = document.getElementById('scriptureModal');
  const closeScriptureModalBtn = document.getElementById('closeScriptureModalBtn');
  const scriptureModalTitle = document.getElementById('scriptureModalTitle');
  const scriptureModalDate = document.getElementById('scriptureModalDate');
  const scriptureModalVerseBadge = document.getElementById('scriptureModalVerseBadge');
  const scriptureModalPassageText = document.getElementById('scriptureModalPassageText');
  const scriptureTextContent = document.getElementById('scriptureTextContent');

  // Active Audio State
  let currentPlayingId = null;

  // 1. Fetch Sermons JSON (with window.SERMONS_DATA fallback for file:// protocol)
  async function loadSermonData() {
    try {
      if (window.SERMONS_DATA && Array.isArray(window.SERMONS_DATA) && window.SERMONS_DATA.length > 0) {
        allSermons = window.SERMONS_DATA;
      } else {
        const response = await fetch('./sermons.json');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        allSermons = await response.json();
      }
      
      const totalFormatted = allSermons.length.toLocaleString();
      if (headerTotalCount) headerTotalCount.textContent = totalFormatted;
      const totalCountBadge = document.getElementById('totalCountBadge');
      if (totalCountBadge) totalCountBadge.textContent = totalFormatted;

      if (loadingSpinner) loadingSpinner.style.display = 'none';

      applyFilters();
    } catch (error) {
      console.error('Failed to load sermons data:', error);
      if (loadingSpinner) {
        loadingSpinner.innerHTML = `
          <i class="fa-solid fa-triangle-exclamation" style="color: #ef4444;"></i>
          <p>설교 데이터를 불러오는 데 실패했습니다.</p>
        `;
      }
    }
  }

  // Selected Year Preset State
  let currentPresetYear = 'all';


  // Helper: Normalize String for Space & Case Insensitive Matching
  function normalizeStr(str) {
    if (!str) return '';
    return str.toString().toLowerCase().replace(/\s+/g, '');
  }

  // 2. Filter & Sort Logic
  function applyFilters() {
    const query = normalizeStr(searchInput.value);
    const startDate = startDateInput.value;
    const endDate = endDateInput.value;
    const ytOnly = ytOnlyFilter ? ytOnlyFilter.checked : false;
    const sortOrder = sortOrderSelect.value;

    let isFiltered = false;
    if (query || startDate || endDate || ytOnly || (currentPresetYear && currentPresetYear !== 'all')) {
      isFiltered = true;
    }

    if (isFiltered) {
      activeFilterBadge.classList.remove('hidden');
    } else {
      activeFilterBadge.classList.add('hidden');
    }

    filteredSermons = allSermons.filter(sermon => {
      // YouTube Only Filter
      if (ytOnly && !sermon.youtube_url) {
        return false;
      }

      // Keyword match (Title or Scripture)
      if (query) {
        const titleMatch = normalizeStr(sermon.title).includes(query);
        const scriptureMatch = normalizeStr(sermon.scripture).includes(query);
        if (!titleMatch && !scriptureMatch) return false;
      }

      // Date Range Match
      const sermonDate = sermon.date || '';
      
      // Preset Year Priority
      if (currentPresetYear && currentPresetYear !== 'all') {
        if (!sermonDate.startsWith(currentPresetYear)) return false;
      } else {
        if (startDate && sermonDate < startDate) return false;
        if (endDate && sermonDate > endDate) return false;
      }

      return true;
    });

    // Sorting
    filteredSermons.sort((a, b) => {
      if (sortOrder === 'date-desc') {
        return (b.date || '').localeCompare(a.date || '') || b.id - a.id;
      } else if (sortOrder === 'date-asc') {
        return (a.date || '').localeCompare(b.date || '') || a.id - b.id;
      } else if (sortOrder === 'id-asc') {
        return a.id - b.id;
      }
      return 0;
    });

    // Reset pagination & render
    displayedCount = PAGE_SIZE;
    matchedCountEl.textContent = filteredSermons.length.toLocaleString();
    renderSermons();
  }


  // 3. Render Sermons (Card View & Detail List View)
  function renderSermons() {
    sermonListEl.innerHTML = '';

    if (filteredSermons.length === 0) {
      sermonListEl.innerHTML = `
        <div class="no-results">
          <i class="fa-solid fa-magnifying-glass"></i>
          <h3>검색 결과가 없습니다</h3>
          <p>다른 검색어나 날짜 범위를 선택해 보세요.</p>
        </div>
      `;
      paginationWrapper.classList.add('hidden');
      return;
    }

    const currentBatch = filteredSermons.slice(0, displayedCount);
    
    currentBatch.forEach(sermon => {
      const card = document.createElement('div');
      card.className = 'sermon-card';
      card.dataset.id = sermon.id;

      const youtubeBtnHtml = sermon.youtube_url
        ? `<button type="button" class="btn-media btn-youtube" data-yt="${sermon.youtube_url}" data-title="${sermon.title}">
             <i class="fa-brands fa-youtube"></i> 유튜브 보기
           </button>`
        : `<button type="button" class="btn-media btn-youtube disabled" title="유튜브 연결 준비 중">
             <i class="fa-brands fa-youtube"></i> 준비 중
           </button>`;

      const shareBtnHtml = `<button type="button" class="btn-media btn-share" data-id="${sermon.id}">
        <i class="fa-solid fa-share-nodes"></i> 공유
      </button>`;

      if (currentViewMode === 'card') {
        card.innerHTML = `
          <div>
            <div class="card-header">
              <span class="card-id-badge">#${sermon.id}</span>
              <span class="card-date"><i class="fa-regular fa-calendar"></i> ${sermon.date || '날짜 미상'}</span>
            </div>
            <h2 class="card-title">${escapeHtml(sermon.title)}</h2>
            <div class="card-scripture">
              <i class="fa-solid fa-book-open"></i> ${escapeHtml(sermon.scripture || '본문 구절 없음')}
            </div>
          </div>
          <div class="card-actions">
            <button type="button" class="btn-media btn-audio" data-mp3="${sermon.url}" data-id="${sermon.id}" data-title="${sermon.title}" data-meta="${sermon.date} | ${sermon.scripture}">
              <i class="fa-solid fa-headphones"></i> 오디오
            </button>
            ${youtubeBtnHtml}
            ${shareBtnHtml}
          </div>
        `;
      } else {
        // Detail - List View HTML
        card.innerHTML = `
          <div class="sermon-card-main">
            <div class="card-header">
              <span class="card-id-badge">#${sermon.id}</span>
              <span class="card-date"><i class="fa-regular fa-calendar"></i> ${sermon.date || '날짜 미상'}</span>
            </div>
            <div class="card-info-col">
              <h2 class="card-title">${escapeHtml(sermon.title)}</h2>
              <div class="card-scripture">
                <i class="fa-solid fa-book-open"></i> ${escapeHtml(sermon.scripture || '본문 구절 없음')}
              </div>
            </div>
          </div>
          <div class="card-actions">
            <button type="button" class="btn-media btn-audio" data-mp3="${sermon.url}" data-id="${sermon.id}" data-title="${sermon.title}" data-meta="${sermon.date} | ${sermon.scripture}">
              <i class="fa-solid fa-headphones"></i> 오디오
            </button>
            ${youtubeBtnHtml}
            ${shareBtnHtml}
          </div>
        `;
      }

      sermonListEl.appendChild(card);
    });

    // Pagination Button Logic
    if (displayedCount < filteredSermons.length) {
      paginationWrapper.classList.remove('hidden');
      remainingCountEl.textContent = (filteredSermons.length - displayedCount).toLocaleString();
    } else {
      paginationWrapper.classList.add('hidden');
    }
  }

  function escapeHtml(text) {
    if (!text) return '';
    return text.replace(/[&<>"']/g, function(m) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' }[m];
    });
  }

  // 4. Audio Player Controls
  function playAudio(mp3Url, id, title, meta) {
    if (currentPlayingId === id && !globalAudio.paused) {
      globalAudio.pause();
      return;
    }

    currentPlayingId = id;
    globalAudio.src = mp3Url;
    playerTitle.textContent = title;
    playerMeta.textContent = meta;
    playerDownloadLink.href = mp3Url;
    playerDownloadLink.setAttribute('download', `${title}.mp3`);

    audioPlayerBar.classList.remove('hidden');
    globalAudio.play().catch(e => console.error("Play error:", e));
    updatePlayPauseIcon();
  }

  function updatePlayPauseIcon() {
    if (globalAudio.paused) {
      btnPlayPause.innerHTML = '<i class="fa-solid fa-play"></i>';
    } else {
      btnPlayPause.innerHTML = '<i class="fa-solid fa-pause"></i>';
    }
  }

  function formatTime(seconds) {
    if (isNaN(seconds) || seconds < 0) return '00:00';
    const mins = Math.floor(seconds / 60);
    const secs = Math.floor(seconds % 60);
    return `${mins.toString().padStart(2, '0')}:${secs.toString().padStart(2, '0')}`;
  }

  // Audio Event Listeners
  btnPlayPause.addEventListener('click', () => {
    if (globalAudio.paused) {
      globalAudio.play();
    } else {
      globalAudio.pause();
    }
    updatePlayPauseIcon();
  });

  globalAudio.addEventListener('play', updatePlayPauseIcon);
  globalAudio.addEventListener('pause', updatePlayPauseIcon);

  globalAudio.addEventListener('timeupdate', () => {
    if (globalAudio.duration) {
      const pct = (globalAudio.currentTime / globalAudio.duration) * 100;
      progressBarFill.style.width = `${pct}%`;
      currentTimeEl.textContent = formatTime(globalAudio.currentTime);
      totalDurationEl.textContent = formatTime(globalAudio.duration);
    }
  });

  btnRewind.addEventListener('click', () => {
    globalAudio.currentTime = Math.max(0, globalAudio.currentTime - 10);
  });

  btnForward.addEventListener('click', () => {
    globalAudio.currentTime = Math.min(globalAudio.duration || 0, globalAudio.currentTime + 10);
  });

  progressBarWrapper.addEventListener('click', (e) => {
    const rect = progressBarWrapper.getBoundingClientRect();
    const pos = (e.clientX - rect.left) / rect.width;
    if (globalAudio.duration) {
      globalAudio.currentTime = pos * globalAudio.duration;
    }
  });

  btnMute.addEventListener('click', () => {
    globalAudio.muted = !globalAudio.muted;
    btnMute.innerHTML = globalAudio.muted
      ? '<i class="fa-solid fa-volume-xmark"></i>'
      : '<i class="fa-solid fa-volume-high"></i>';
  });

  btnClosePlayer.addEventListener('click', () => {
    globalAudio.pause();
    audioPlayerBar.classList.add('hidden');
    currentPlayingId = null;
  });

  function openYouTubeTab(ytUrl) {
    if (!ytUrl) return;
    if (!globalAudio.paused) {
      globalAudio.pause();
    }
    window.open(ytUrl, '_blank');
  }

  // Toast Notification Helper
  let toastTimer = null;
  function showToast(message) {
    const toast = document.getElementById('toastNotification');
    const toastMessage = document.getElementById('toastMessage');
    if (!toast || !toastMessage) return;

    toastMessage.textContent = message;
    toast.classList.remove('hidden');

    if (toastTimer) clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      toast.classList.add('hidden');
    }, 2800);
  }

  // Share Modal Elements & Controls
  const shareModal = document.getElementById('shareModal');
  const closeShareModalBtn = document.getElementById('closeShareModalBtn');
  const shareModalTitle = document.getElementById('shareModalTitle');
  const shareModalMeta = document.getElementById('shareModalMeta');
  const shareMp3Option = document.getElementById('shareMp3Option');
  const shareYtOption = document.getElementById('shareYtOption');
  const shareMp3UrlText = document.getElementById('shareMp3UrlText');
  const shareYtUrlText = document.getElementById('shareYtUrlText');
  const btnCopyMp3 = document.getElementById('btnCopyMp3');
  const btnCopyYt = document.getElementById('btnCopyYt');

  let activeShareSermon = null;

  function openShareModal(sermon) {
    if (!sermon) return;
    activeShareSermon = sermon;

    shareModalTitle.textContent = sermon.title;
    shareModalMeta.textContent = `${sermon.date || '날짜 미상'} | ${sermon.scripture || '성경 구절 없음'}`;

    // MP3 URL
    shareMp3UrlText.textContent = sermon.url || 'MP3 URL 없음';
    btnCopyMp3.disabled = !sermon.url;

    // YouTube URL
    if (sermon.youtube_url) {
      shareYtUrlText.textContent = sermon.youtube_url;
      shareYtOption.classList.remove('disabled');
      btnCopyYt.disabled = false;
    } else {
      shareYtUrlText.textContent = '유튜브 영상이 연결되지 않음';
      shareYtOption.classList.add('disabled');
      btnCopyYt.disabled = true;
    }

    shareModal.classList.remove('hidden');
  }

  function closeShareModal() {
    if (shareModal) shareModal.classList.add('hidden');
    activeShareSermon = null;
  }

  if (closeShareModalBtn) {
    closeShareModalBtn.addEventListener('click', closeShareModal);
  }
  if (shareModal) {
    shareModal.addEventListener('click', (e) => {
      if (e.target === shareModal) closeShareModal();
    });
  }

  function copyMp3Url() {
    if (!activeShareSermon || !activeShareSermon.url) return;
    navigator.clipboard.writeText(activeShareSermon.url)
      .then(() => {
        showToast('MP3 오디오 URL이 클립보드에 복사되었습니다!');
        closeShareModal();
      })
      .catch(err => console.error('Copy failed:', err));
  }

  function copyYtUrl() {
    if (!activeShareSermon || !activeShareSermon.youtube_url) return;
    navigator.clipboard.writeText(activeShareSermon.youtube_url)
      .then(() => {
        showToast('YouTube 영상 URL이 클립보드에 복사되었습니다!');
        closeShareModal();
      })
      .catch(err => console.error('Copy failed:', err));
  }

  if (shareMp3Option) shareMp3Option.addEventListener('click', copyMp3Url);
  if (shareYtOption) shareYtOption.addEventListener('click', copyYtUrl);

  function openScriptureModal(sermon) {
    if (!sermon) return;
    scriptureModalTitle.textContent = sermon.title;
    scriptureModalDate.innerHTML = `<i class="fa-regular fa-calendar"></i> ${sermon.date || '날짜 미상'}`;
    scriptureModalVerseBadge.innerHTML = `<i class="fa-solid fa-book-open"></i> ${sermon.scripture || '본문 구절 없음'}`;
    scriptureModalPassageText.textContent = sermon.scripture || '개역개정 성경 본문';

    // Populate Scripture Verses Text (Inline Continuous Paragraph Flow)
    if (sermon.scripture_text) {
      const lines = sermon.scripture_text.split('\n');
      const htmlInline = lines.map(line => {
        const m = line.match(/^(\d+절)\s*(.*)$/);
        if (m) {
          return `<span class="verse-num">${escapeHtml(m[1])}</span>${escapeHtml(m[2])}`;
        }
        return escapeHtml(line);
      }).join(' ');
      scriptureTextContent.innerHTML = htmlInline;
    } else {
      scriptureTextContent.innerHTML = `
        <div style="text-align: center; color: var(--text-muted); padding: 1.5rem 0;">
          <i class="fa-solid fa-file-circle-exclamation" style="font-size: 2rem; margin-bottom: 0.5rem; color: var(--accent-gold);"></i>
          <p>해당 성경 구절 본문 텍스트가 준비 중입니다.</p>
          <small style="color: var(--text-sub); display: block; margin-top: 0.25rem;">(본문: ${escapeHtml(sermon.scripture || '정보 없음')})</small>
        </div>
      `;
    }

    // Modal Actions (Play Audio, YouTube & Share)
    const scriptureModalActions = document.getElementById('scriptureModalActions');
    const youtubeBtnHtml = sermon.youtube_url
      ? `<button type="button" class="btn-media btn-youtube" data-yt="${sermon.youtube_url}" data-title="${sermon.title}">
           <i class="fa-brands fa-youtube"></i> 유튜브 보기
         </button>`
      : `<button type="button" class="btn-media btn-youtube disabled" title="유튜브 연결 준비 중">
           <i class="fa-brands fa-youtube"></i> 준비 중
         </button>`;

    scriptureModalActions.innerHTML = `
      <button type="button" class="btn-media btn-audio" data-mp3="${sermon.url}" data-id="${sermon.id}" data-title="${sermon.title}" data-meta="${sermon.date} | ${sermon.scripture}">
        <i class="fa-solid fa-headphones"></i> 오디오
      </button>
      ${youtubeBtnHtml}
      <button type="button" class="btn-media btn-share" data-id="${sermon.id}">
        <i class="fa-solid fa-share-nodes"></i> 공유
      </button>
    `;

    scriptureModal.classList.remove('hidden');
  }

  function closeScriptureModal() {
    scriptureModal.classList.add('hidden');
  }

  if (closeScriptureModalBtn) {
    closeScriptureModalBtn.addEventListener('click', closeScriptureModal);
  }
  if (scriptureModal) {
    scriptureModal.addEventListener('click', (e) => {
      if (e.target === scriptureModal) closeScriptureModal();
    });
  }

  // Toast Notification
  function showToast(message) {
    const toast = document.getElementById('toastNotification');
    const msgEl = document.getElementById('toastMessage');
    if (!toast) return;
    if (msgEl) msgEl.textContent = message;
    toast.classList.remove('hidden');
    clearTimeout(toast._timeout);
    toast._timeout = setTimeout(() => {
      toast.classList.add('hidden');
    }, 2500);
  }

  function copyTextToClipboard(text, successMessage) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(() => {
        showToast(successMessage);
      }).catch(() => {
        fallbackCopy(text, successMessage);
      });
    } else {
      fallbackCopy(text, successMessage);
    }
  }

  function fallbackCopy(text, successMessage) {
    const tempInput = document.createElement('input');
    tempInput.value = text;
    document.body.appendChild(tempInput);
    tempInput.select();
    document.execCommand('copy');
    document.body.removeChild(tempInput);
    showToast(successMessage);
  }





  // Event Delegation for Cards & List Items
  sermonListEl.addEventListener('click', (e) => {
    // 1. Audio button click
    const audioBtn = e.target.closest('.btn-audio');
    if (audioBtn) {
      e.stopPropagation();
      const mp3 = audioBtn.dataset.mp3;
      const id = parseInt(audioBtn.dataset.id, 10);
      const title = audioBtn.dataset.title;
      const meta = audioBtn.dataset.meta;
      playAudio(mp3, id, title, meta);
      return;
    }

    // 2. YouTube button click
    const ytBtn = e.target.closest('.btn-youtube:not(.disabled)');
    if (ytBtn) {
      e.stopPropagation();
      const ytUrl = ytBtn.dataset.yt;
      openYouTubeTab(ytUrl);
      return;
    }

    // 3. Share button click
    const shareBtn = e.target.closest('.btn-share');
    if (shareBtn) {
      e.stopPropagation();
      let idStr = shareBtn.dataset.id;
      if (!idStr) {
        const parentCard = shareBtn.closest('.sermon-card');
        if (parentCard) idStr = parentCard.dataset.id;
      }
      const sermon = allSermons.find(s => String(s.id) === String(idStr));
      if (sermon) {
        openShareModal(sermon);
      }
      return;
    }

    // 4. Scripture text click ONLY -> Open Scripture Modal
    const scriptureEl = e.target.closest('.card-scripture');
    if (scriptureEl) {
      e.stopPropagation();
      const cardItem = scriptureEl.closest('.sermon-card');
      if (cardItem) {
        const id = parseInt(cardItem.dataset.id, 10);
        const sermon = allSermons.find(s => s.id === id);
        if (sermon) {
          openScriptureModal(sermon);
        }
      }
      return;
    }
  });

  // 6. UI Event Listeners
  searchInput.addEventListener('input', () => {
    if (searchInput.value.trim().length > 0) {
      clearSearchBtn.style.display = 'block';
    } else {
      clearSearchBtn.style.display = 'none';
    }
    applyFilters();
  });

  clearSearchBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    applyFilters();
  });

  startDateInput.addEventListener('change', () => {
    currentPresetYear = 'all';
    presetBtns.forEach(b => b.classList.remove('active'));
    applyFilters();
  });
  endDateInput.addEventListener('change', () => {
    currentPresetYear = 'all';
    presetBtns.forEach(b => b.classList.remove('active'));
    applyFilters();
  });
  if (ytOnlyFilter) {
    ytOnlyFilter.addEventListener('change', applyFilters);
  }
  sortOrderSelect.addEventListener('change', applyFilters);

  // Preset Buttons Listener (2004 ~ 2014)
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      presetBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const preset = btn.dataset.preset;
      currentPresetYear = preset;

      if (preset === 'all') {
        startDateInput.value = '';
        endDateInput.value = '';
      } else if (/^\d{4}$/.test(preset)) {
        startDateInput.value = `${preset}-01-01`;
        endDateInput.value = `${preset}-12-31`;
      }
      applyFilters();
    });
  });

  // Reset Filters Button
  resetFiltersBtn.addEventListener('click', () => {
    searchInput.value = '';
    clearSearchBtn.style.display = 'none';
    startDateInput.value = '';
    endDateInput.value = '';
    currentPresetYear = 'all';
    if (ytOnlyFilter) ytOnlyFilter.checked = false;
    sortOrderSelect.value = 'date-desc';

    presetBtns.forEach(b => b.classList.remove('active'));
    const allBtn = document.querySelector('.preset-btn[data-preset="all"]');
    if (allBtn) allBtn.classList.add('active');

    applyFilters();
  });

  // Load More Button
  loadMoreBtn.addEventListener('click', () => {
    displayedCount += PAGE_SIZE;
    renderSermons();
  });

  // ==========================================================================
  // Mode Navigation Tabs Switching
  // ==========================================================================
  function switchTab(mode) {
    currentTabMode = mode;
    if (mode === 'all') {
      if (tabAllSermons) tabAllSermons.classList.add('active');
      if (tabPlaylists) tabPlaylists.classList.remove('active');
      if (allSermonsView) {
        allSermonsView.classList.remove('hidden');
        allSermonsView.style.display = 'block';
      }
      if (playlistsView) {
        playlistsView.classList.add('hidden');
        playlistsView.style.display = 'none';
      }
    } else {
      if (tabPlaylists) tabPlaylists.classList.add('active');
      if (tabAllSermons) tabAllSermons.classList.remove('active');
      if (allSermonsView) {
        allSermonsView.classList.add('hidden');
        allSermonsView.style.display = 'none';
      }
      if (playlistsView) {
        playlistsView.classList.remove('hidden');
        playlistsView.style.display = 'block';
      }

      // Ensure sidebar is rendered
      renderPlaylistSidebar();

      // Select playlist
      if (!activePlaylistId && allPlaylists.length > 0) {
        selectPlaylist(allPlaylists[0].id);
      } else if (activePlaylistId) {
        selectPlaylist(activePlaylistId);
      }
    }
  }

  if (tabAllSermons) {
    tabAllSermons.addEventListener('click', () => switchTab('all'));
  }
  if (tabPlaylists) {
    tabPlaylists.addEventListener('click', () => switchTab('playlists'));
  }



  // ==========================================================================
  // Playlists Mode Logic
  // ==========================================================================
  async function loadPlaylistsData() {
    try {
      if (window.PLAYLISTS_DATA && Array.isArray(window.PLAYLISTS_DATA) && window.PLAYLISTS_DATA.length > 0) {
        allPlaylists = window.PLAYLISTS_DATA;
      } else {
        const response = await fetch('./playlists.json');
        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        allPlaylists = await response.json();
      }

      if (playlistTabBadge) playlistTabBadge.textContent = allPlaylists.length;
      if (plTotalCount) plTotalCount.textContent = allPlaylists.length;

      renderPlaylistSidebar();

      if (allPlaylists.length > 0) {
        selectPlaylist(allPlaylists[0].id);
      }
    } catch (error) {
      console.warn('Playlists data not loaded yet or failed:', error);
      if (playlistItemsList) {
        playlistItemsList.innerHTML = `
          <div style="padding: 1rem; color: var(--text-muted); font-size: 0.85rem; text-align: center;">
            <i class="fa-solid fa-circle-info"></i> 재생목록 데이터가 아직 준비되지 않았습니다.
          </div>
        `;
      }
    }
  }


  function renderPlaylistSidebar() {
    if (!playlistItemsList) return;
    const query = normalizeStr(plSearchInput ? plSearchInput.value : '');

    filteredPlaylists = allPlaylists.filter(pl => {
      if (!query) return true;
      return normalizeStr(pl.title).includes(query) || normalizeStr(pl.id).includes(query);
    });

    if (filteredPlaylists.length === 0) {
      playlistItemsList.innerHTML = `
        <div style="padding: 1.5rem 1rem; color: var(--text-muted); font-size: 0.85rem; text-align: center;">
          <p>검색된 재생목록이 없습니다.</p>
        </div>
      `;
      return;
    }

    let html = '';
    filteredPlaylists.forEach(pl => {
      const isActive = pl.id === activePlaylistId;
      html += `
        <button type="button" class="playlist-item-btn ${isActive ? 'active' : ''}" data-pl-id="${pl.id}">
          <div class="pl-item-info">
            <i class="fa-solid fa-folder-play"></i>
            <span class="pl-item-title" title="${escapeHtml(pl.title)}">${escapeHtml(pl.title)}</span>
          </div>
          <span class="pl-item-badge">${pl.video_count || (pl.videos ? pl.videos.length : 0)}편</span>
        </button>
      `;
    });

    playlistItemsList.innerHTML = html;
  }

  function selectPlaylist(playlistId) {
    activePlaylistId = playlistId;
    const currentPl = allPlaylists.find(p => p.id === playlistId);
    if (!currentPl) return;

    // Update sidebar active classes
    renderPlaylistSidebar();

    // Update Banner Info
    if (activePlTitle) activePlTitle.textContent = currentPl.title;
    if (activePlMeta) activePlMeta.textContent = `총 ${currentPl.videos ? currentPl.videos.length : 0}개의 설교 영상이 등록되어 있습니다.`;
    if (activePlShareBtn) {
      activePlShareBtn.classList.remove('hidden');
    }
    if (activePlYtLink) {
      activePlYtLink.href = currentPl.url;
      activePlYtLink.classList.remove('hidden');
    }

    renderPlaylistVideos();
  }


  function renderPlaylistVideos() {
    if (!playlistVideoList) return;
    const currentPl = allPlaylists.find(p => p.id === activePlaylistId);
    if (!currentPl || !currentPl.videos || currentPl.videos.length === 0) {
      playlistVideoList.innerHTML = `
        <div class="pl-empty-state">
          <i class="fa-solid fa-video-slash"></i>
          <h3>등록된 영상이 없습니다</h3>
          <p>이 재생목록에 영상이 존재하지 않습니다.</p>
        </div>
      `;
      return;
    }

    const searchQuery = normalizeStr(plVideoSearchInput ? plVideoSearchInput.value : '');
    const sortVal = plSortOrder ? plSortOrder.value : 'date-asc';

    let videos = currentPl.videos.filter(v => {
      if (!searchQuery) return true;
      const titleMatch = normalizeStr(v.title).includes(searchQuery);
      const sTitleMatch = v.sermon_title ? normalizeStr(v.sermon_title).includes(searchQuery) : false;
      const scriptureMatch = v.scripture ? normalizeStr(v.scripture).includes(searchQuery) : false;
      return titleMatch || sTitleMatch || scriptureMatch;
    });

    // Sorting (Default: date-asc)
    videos.sort((a, b) => {
      if (sortVal === 'date-asc') {
        const dA = a.date || '9999-99-99';
        const dB = b.date || '9999-99-99';
        return dA.localeCompare(dB) || (a.index || 0) - (b.index || 0);
      } else if (sortVal === 'date-desc') {
        const dA = a.date || '0000-00-00';
        const dB = b.date || '0000-00-00';
        return dB.localeCompare(dA) || (b.index || 0) - (a.index || 0);
      } else if (sortVal === 'title-asc') {
        return (a.title || '').localeCompare(b.title || '');
      }
      return 0;
    });


    if (videos.length === 0) {
      playlistVideoList.innerHTML = `
        <div class="pl-empty-state">
          <i class="fa-solid fa-magnifying-glass"></i>
          <h3>검색 결과가 없습니다</h3>
          <p>다른 검색어로 검색해 보세요.</p>
        </div>
      `;
      return;
    }

    let html = '';
    videos.forEach((v, index) => {
      const displayTitle = v.sermon_title || v.title;
      const hasDate = Boolean(v.date);
      const hasScripture = Boolean(v.scripture);
      const hasScriptureText = Boolean(v.scripture_text);
      const hasMp3 = Boolean(v.mp3_url);
      const sermonId = v.sermon_id;

      const metaString = `${v.date || ''} | ${v.scripture || ''}`;

      html += `
        <div class="pl-video-item" data-video-id="${v.video_id}" data-sermon-id="${sermonId || ''}">
          <div class="pl-video-index">#${index + 1}</div>
          <div class="pl-video-details">
            <h4 class="pl-video-title">${escapeHtml(v.title)}</h4>
            <div class="pl-video-meta">
              ${hasDate ? `<span><i class="fa-regular fa-calendar"></i> ${v.date}</span>` : ''}
              ${hasScripture ? `<span class="verse-pill ${hasScriptureText ? 'cursor-pointer scripture-btn-trigger' : ''}" data-id="${sermonId || ''}"><i class="fa-solid fa-book-open"></i> ${escapeHtml(v.scripture)}</span>` : ''}
              ${!hasDate && !hasScripture ? `<span><i class="fa-brands fa-youtube"></i> YouTube 영상</span>` : ''}
            </div>
          </div>
          <div class="pl-video-actions">
            <button type="button" class="btn-media btn-youtube" data-yt="${v.url}" title="YouTube 영상 재생">
              <i class="fa-brands fa-youtube"></i> 유튜브 보기
            </button>
            ${hasMp3 ? `
              <button type="button" class="btn-media btn-audio" data-mp3="${v.mp3_url}" data-id="${sermonId || 0}" data-title="${escapeHtml(displayTitle)}" data-meta="${escapeHtml(metaString)}" title="MP3 설교 듣기">
                <i class="fa-solid fa-headphones"></i> 오디오
              </button>
            ` : ''}
            ${hasScriptureText ? `
              <button type="button" class="btn-media btn-scripture" data-id="${sermonId}" title="성경 본문 보기">
                <i class="fa-solid fa-book-bible"></i> 본문
              </button>
            ` : ''}
            <button type="button" class="btn-media btn-share" data-id="${sermonId || ''}" data-video-id="${v.video_id}" data-yt="${v.url}" data-mp3="${v.mp3_url || ''}" data-title="${escapeHtml(displayTitle)}" data-meta="${escapeHtml(metaString)}" title="설교 링크 공유">
              <i class="fa-solid fa-share-nodes"></i> 공유
            </button>
          </div>
        </div>
      `;
    });

    playlistVideoList.innerHTML = html;
  }



  // Playlist Sidebar Item Click Handler
  if (playlistItemsList) {
    playlistItemsList.addEventListener('click', (e) => {
      const btn = e.target.closest('.playlist-item-btn');
      if (btn) {
        const plId = btn.dataset.plId;
        if (plId) selectPlaylist(plId);
      }
    });
  }

  // Playlist Search Filter Input
  if (plSearchInput) {
    plSearchInput.addEventListener('input', () => {
      if (plSearchInput.value.trim().length > 0) {
        if (clearPlSearchBtn) clearPlSearchBtn.classList.remove('hidden');
      } else {
        if (clearPlSearchBtn) clearPlSearchBtn.classList.add('hidden');
      }
      renderPlaylistSidebar();
    });
  }

  if (clearPlSearchBtn) {
    clearPlSearchBtn.addEventListener('click', () => {
      plSearchInput.value = '';
      clearPlSearchBtn.classList.add('hidden');
      renderPlaylistSidebar();
    });
  }

  // Active Playlist Share Button Click Handler
  if (activePlShareBtn) {
    activePlShareBtn.addEventListener('click', () => {
      const currentPl = allPlaylists.find(p => p.id === activePlaylistId);
      if (currentPl && currentPl.url) {
        copyTextToClipboard(currentPl.url, `'${currentPl.title}' 재생목록 링크가 복사되었습니다!`);
      }
    });
  }


  // Playlist Video Search & Sort Listeners
  if (plVideoSearchInput) {
    plVideoSearchInput.addEventListener('input', renderPlaylistVideos);
  }
  if (plSortOrder) {
    plSortOrder.addEventListener('change', renderPlaylistVideos);
  }



  // Playlist Video List Click Delegation
  if (playlistVideoList) {
    playlistVideoList.addEventListener('click', (e) => {
      // 1. Audio button click
      const audioBtn = e.target.closest('.btn-audio');
      if (audioBtn) {
        e.stopPropagation();
        const mp3 = audioBtn.dataset.mp3;
        const id = parseInt(audioBtn.dataset.id, 10);
        const title = audioBtn.dataset.title;
        const meta = audioBtn.dataset.meta;
        playAudio(mp3, id, title, meta);
        return;
      }

      // 2. YouTube button click
      const ytBtn = e.target.closest('.btn-youtube');
      if (ytBtn) {
        e.stopPropagation();
        const ytUrl = ytBtn.dataset.yt;
        openYouTubeTab(ytUrl);
        return;
      }

      // 3. Share button click
      const shareBtn = e.target.closest('.btn-share');
      if (shareBtn) {
        e.stopPropagation();
        const sId = shareBtn.dataset.id;
        const sermon = sId ? allSermons.find(s => String(s.id) === String(sId)) : null;
        if (sermon) {
          openShareModal(sermon);
        } else {
          // Construct fallback sermon object for modal
          const fallbackObj = {
            id: 0,
            title: shareBtn.dataset.title || '설교 영상',
            date: '',
            scripture: '',
            url: shareBtn.dataset.mp3 || '',
            youtube_url: shareBtn.dataset.yt || ''
          };
          openShareModal(fallbackObj);
        }
        return;
      }

      // 4. Scripture button / badge click
      const scriptureTrigger = e.target.closest('.btn-scripture, .scripture-btn-trigger');
      if (scriptureTrigger) {
        e.stopPropagation();
        const sId = parseInt(scriptureTrigger.dataset.id, 10);
        const sermon = allSermons.find(s => s.id === sId);
        if (sermon) {
          openScriptureModal(sermon);
        }
        return;
      }
    });
  }

  // Initialize Data
  loadSermonData();
  loadPlaylistsData();
  switchTab('all');
});


