/**
 * 샬롬 말씀 아카이브 검색 - Client-side Search, Filtering & Player Logic
 */

document.addEventListener('DOMContentLoaded', () => {
  // Data Store
  let allSermons = [];
  let filteredSermons = [];
  let displayedCount = 30; // Batch load size for UI performance
  const PAGE_SIZE = 30;

  // View Mode State
  let currentViewMode = 'list'; // 'card' | 'list'

  // DOM Elements
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

  // 1. Fetch Sermons JSON
  async function loadSermonData() {
    try {
      const response = await fetch('./sermons.json');
      if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
      allSermons = await response.json();
      
      headerTotalCount.textContent = allSermons.length.toLocaleString();
      loadingSpinner.style.display = 'none';

      applyFilters();
    } catch (error) {
      console.error('Failed to load sermons.json:', error);
      loadingSpinner.innerHTML = `
        <i class="fa-solid fa-triangle-exclamation" style="color: #ef4444;"></i>
        <p>설교 데이터를 불러오는 데 실패했습니다 (sermons.json).</p>
      `;
    }
  }

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
    if (query || startDate || endDate || ytOnly) {
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
      if (startDate && sermonDate < startDate) return false;
      if (endDate && sermonDate > endDate) return false;

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

  // Modal Actions inside Scripture Modal
  const scriptureModalActions = document.getElementById('scriptureModalActions');
  if (scriptureModalActions) {
    scriptureModalActions.addEventListener('click', (e) => {
      const audioBtn = e.target.closest('.btn-audio');
      if (audioBtn) {
        const mp3 = audioBtn.dataset.mp3;
        const id = parseInt(audioBtn.dataset.id);
        const title = audioBtn.dataset.title;
        const meta = audioBtn.dataset.meta;
        playAudio(mp3, id, title, meta);
        closeScriptureModal();
        return;
      }

      const ytBtn = e.target.closest('.btn-youtube:not(.disabled)');
      if (ytBtn) {
        const ytUrl = ytBtn.dataset.yt;
        closeScriptureModal();
        openYouTubeTab(ytUrl);
        return;
      }

      const shareBtn = e.target.closest('.btn-share');
      if (shareBtn) {
        const id = parseInt(shareBtn.dataset.id);
        const sermon = allSermons.find(s => s.id === id);
        if (sermon) {
          closeScriptureModal();
          openShareModal(sermon);
        }
        return;
      }
    });
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

  startDateInput.addEventListener('change', applyFilters);
  endDateInput.addEventListener('change', applyFilters);
  if (ytOnlyFilter) {
    ytOnlyFilter.addEventListener('change', applyFilters);
  }
  sortOrderSelect.addEventListener('change', applyFilters);

  // Preset Buttons Listener
  presetBtns.forEach(btn => {
    btn.addEventListener('click', () => {
      presetBtns.forEach(b => b.classList.remove('active'));
      btn.classList.add('active');

      const preset = btn.dataset.preset;
      if (preset === 'all') {
        startDateInput.value = '';
        endDateInput.value = '';
      } else if (preset === '2014') {
        startDateInput.value = '2014-01-01';
        endDateInput.value = '2014-12-31';
      } else if (preset === '2013') {
        startDateInput.value = '2013-01-01';
        endDateInput.value = '2013-12-31';
      } else if (preset === '2012') {
        startDateInput.value = '2012-01-01';
        endDateInput.value = '2012-12-31';
      } else if (preset === '2011') {
        startDateInput.value = '2011-01-01';
        endDateInput.value = '2011-12-31';
      } else if (preset === '2010') {
        startDateInput.value = '2000-01-01';
        endDateInput.value = '2010-12-31';
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
    if (ytOnlyFilter) ytOnlyFilter.checked = false;
    sortOrderSelect.value = 'date-desc';

    presetBtns.forEach(b => b.classList.remove('active'));
    document.querySelector('.preset-btn[data-preset="all"]').classList.add('active');

    applyFilters();
  });

  // Load More Button
  loadMoreBtn.addEventListener('click', () => {
    displayedCount += PAGE_SIZE;
    renderSermons();
  });

  // Initialize Data
  loadSermonData();
});
