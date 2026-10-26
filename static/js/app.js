/**
 * PULSEARR - Unified Frontend Application Engine
 * Blazing fast, reactive vanilla JavaScript client for TV (Sonarr) + Movies (Radarr) + Trackers Hub (Prowlarr).
 */

// Global Reactive State
const state = {
  currentView: 'series',
  // Series (TV)
  series: [],
  filteredSeries: [],
  statusFilter: 'all',
  activeSeriesDetail: null,
  // Movies
  movies: [],
  filteredMovies: [],
  movieStatusFilter: 'all',
  activeMovieDetail: null,
  // Trackers Hub (Prowlarr)
  trackers: [],
  // System & Infrastructure
  profiles: [],
  queueCount: 0,
  sseConnection: null,
  debounceTimer: null,
  movieDebounceTimer: null
};

// Initialization on DOM Ready
document.addEventListener('DOMContentLoaded', () => {
  initApp();
});

async function initApp() {
  await loadProfiles();
  await loadSeries();
  setupSSE();
  startQueuePolling();
}

// ==========================================
// Navigation & Views
// ==========================================
function switchView(viewName) {
  state.currentView = viewName;
  document.querySelectorAll('.nav-link').forEach(link => {
    link.classList.toggle('active', link.dataset.view === viewName);
  });

  document.querySelectorAll('.view-section').forEach(sec => {
    sec.classList.remove('active');
  });

  const targetSec = document.getElementById(`view-${viewName}`);
  if (targetSec) {
    targetSec.classList.add('active');
  }

  // Load view-specific data
  if (viewName === 'series') loadSeries();
  else if (viewName === 'movies') loadMovies();
  else if (viewName === 'trackers') loadTrackers();
  else if (viewName === 'calendar') loadCalendar();
  else if (viewName === 'activity') loadQueue();
  else if (viewName === 'history') loadHistory();
  else if (viewName === 'settings') loadSettings();
  else if (viewName === 'system') loadSystemDiagnostics();
}

// ==========================================
// TV Shows Library (Sonarr)
// ==========================================
async function loadSeries() {
  try {
    const res = await fetch('/api/v1/series');
    if (!res.ok) throw new Error('Failed to load series');
    state.series = await res.json();
    filterSeriesCards();
  } catch (err) {
    showToast('Failed to load series: ' + err.message, 'error');
  }
}

function filterSeriesCards() {
  const query = (document.getElementById('series-filter-input')?.value || '').toLowerCase().trim();
  const filter = state.statusFilter;

  state.filteredSeries = state.series.filter(s => {
    const matchesQuery = !query || s.title.toLowerCase().includes(query) || (s.network || '').toLowerCase().includes(query);
    if (!matchesQuery) return false;

    if (filter === 'continuing') return s.status.toLowerCase() === 'running';
    if (filter === 'ended') return s.status.toLowerCase() === 'ended';
    if (filter === 'missing') return s.downloaded_episode_count < s.episode_count;
    return true;
  });

  sortSeriesCards(false);
  renderSeriesGrid();
}

function setSeriesStatusFilter(filter) {
  state.statusFilter = filter;
  document.querySelectorAll('.filter-pills .pill-btn[data-filter]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.filter === filter);
  });
  filterSeriesCards();
}

function sortSeriesCards(triggerRender = true) {
  const sortBy = document.getElementById('series-sort-select')?.value || 'title';
  state.filteredSeries.sort((a, b) => {
    if (sortBy === 'title') return a.sort_title.localeCompare(b.sort_title);
    if (sortBy === 'episodes') return b.episode_count - a.episode_count;
    if (sortBy === 'date') return new Date(b.created_at) - new Date(a.created_at);
    return 0;
  });
  if (triggerRender) renderSeriesGrid();
}

function renderSeriesGrid() {
  const grid = document.getElementById('series-grid');
  const empty = document.getElementById('series-empty');
  if (!grid || !empty) return;

  if (state.filteredSeries.length === 0) {
    grid.innerHTML = '';
    empty.style.display = 'block';
    return;
  }

  empty.style.display = 'none';
  grid.innerHTML = state.filteredSeries.map(s => {
    const pct = s.episode_count > 0 ? Math.round((s.downloaded_episode_count / s.episode_count) * 100) : 0;
    const isContinuing = s.status.toLowerCase() === 'running';
    const poster = s.poster_url || '/static/img/no-poster.png';

    return `
      <div class="series-card" onclick="openSeriesDetailModal(${s.id})">
        <div class="poster-wrapper">
          <img class="poster-img" src="${poster}" alt="${s.title}" loading="lazy" onerror="this.src='https://placehold.co/300x450/0d121c/ffffff?text=${encodeURIComponent(s.title)}'">
          <div class="status-badge ${isContinuing ? 'continuing' : 'ended'}">
            ${isContinuing ? 'Continuing' : 'Ended'}
          </div>
          <div class="poster-overlay">
            <div class="network-tag">${s.network || 'TV'}</div>
            <div class="series-title" title="${s.title}">${s.title}</div>
          </div>
        </div>
        <div class="card-footer">
          <div class="progress-info">
            <span>${s.season_count} Season${s.season_count === 1 ? '' : 's'}</span>
            <span>${s.downloaded_episode_count}/${s.episode_count} Ep (${pct}%)</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${pct}%"></div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ==========================================
// Movies Library (Radarr)
// ==========================================
async function loadMovies() {
  try {
    const res = await fetch('/api/v1/movies');
    if (!res.ok) throw new Error('Failed to load movies');
    state.movies = await res.json();
    filterMovieCards();
  } catch (err) {
    showToast('Failed to load movies: ' + err.message, 'error');
  }
}

function filterMovieCards() {
  const query = (document.getElementById('movies-filter-input')?.value || '').toLowerCase().trim();
  const filter = state.movieStatusFilter;

  state.filteredMovies = state.movies.filter(m => {
    const matchesQuery = !query || m.title.toLowerCase().includes(query) || (m.year && m.year.toString().includes(query));
    if (!matchesQuery) return false;

    if (filter === 'downloaded') return m.has_file;
    if (filter === 'missing') return !m.has_file;
    return true;
  });

  sortMovieCards(false);
  renderMoviesGrid();
}

function setMovieStatusFilter(filter) {
  state.movieStatusFilter = filter;
  document.querySelectorAll('[data-movie-filter]').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.movieFilter === filter);
  });
  filterMovieCards();
}

function sortMovieCards(triggerRender = true) {
  const sortBy = document.getElementById('movies-sort-select')?.value || 'title';
  state.filteredMovies.sort((a, b) => {
    if (sortBy === 'title') return a.sort_title.localeCompare(b.sort_title);
    if (sortBy === 'year') return (b.year || 0) - (a.year || 0);
    if (sortBy === 'rating') return (b.rating || 0) - (a.rating || 0);
    return 0;
  });
  if (triggerRender) renderMoviesGrid();
}

function renderMoviesGrid() {
  const grid = document.getElementById('movies-grid');
  const empty = document.getElementById('movies-empty');
  if (!grid || !empty) return;

  if (state.filteredMovies.length === 0) {
    grid.innerHTML = '';
    empty.style.display = 'block';
    return;
  }

  empty.style.display = 'none';
  grid.innerHTML = state.filteredMovies.map(m => {
    const poster = m.poster_url || 'https://placehold.co/300x450/0d121c/ffffff?text=' + encodeURIComponent(m.title);
    const hasFile = m.has_file;
    const ratingStr = m.rating > 0 ? `★ ${m.rating.toFixed(1)}` : '';

    return `
      <div class="series-card" onclick="openMovieDetailModal(${m.id})">
        <div class="poster-wrapper">
          <img class="poster-img" src="${poster}" alt="${m.title}" loading="lazy" onerror="this.src='https://placehold.co/300x450/0d121c/ffffff?text=${encodeURIComponent(m.title)}'">
          <div class="status-badge ${hasFile ? 'continuing' : 'ended'}">
            ${hasFile ? 'Downloaded' : 'Missing'}
          </div>
          <div class="poster-overlay">
            <div class="network-tag">${m.year || 'Movie'} ${ratingStr ? '• ' + ratingStr : ''}</div>
            <div class="series-title" title="${m.title}">${m.title}</div>
          </div>
        </div>
        <div class="card-footer">
          <div class="progress-info">
            <span>${(m.genres || []).slice(0, 2).join(', ') || 'Feature Film'}</span>
            <span style="color: ${hasFile ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">${hasFile ? (m.quality || 'Ready') : 'Wanted'}</span>
          </div>
          <div class="progress-bar-bg">
            <div class="progress-bar-fill" style="width: ${hasFile ? '100%' : '0%'}; background: ${hasFile ? 'linear-gradient(90deg, var(--accent-emerald), var(--accent-cyan))' : 'var(--accent-rose)'};"></div>
          </div>
        </div>
      </div>
    `;
  }).join('');
}

// ==========================================
// Trackers Hub & Prowlarr Benchmarking
// ==========================================
async function loadTrackers() {
  try {
    const res = await fetch('/api/v1/trackers');
    if (!res.ok) throw new Error('Failed to load trackers');
    state.trackers = await res.json();
    renderTrackersTable();
  } catch (err) {
    showToast('Failed to load trackers: ' + err.message, 'error');
  }
}

function renderTrackersTable() {
  const tbody = document.getElementById('trackers-table-body');
  if (!tbody) return;

  if (state.trackers.length === 0) {
    tbody.innerHTML = `
      <tr>
        <td colspan="7" style="text-align: center; color: var(--text-muted); padding: 2rem;">
          No trackers configured. Click "+ Add Tracker" to add Torznab or direct indexers.
        </td>
      </tr>
    `;
    return;
  }

  tbody.innerHTML = state.trackers.map(t => {
    let latencyBadge = '<span class="pill-latency" style="color: var(--text-muted); border: 1px solid var(--border-subtle);">Untested</span>';
    if (t.latency_ms > 0) {
      const cls = t.latency_ms < 300 ? 'good' : (t.latency_ms < 1000 ? 'medium' : 'slow');
      latencyBadge = `<span class="pill-latency ${cls}">⚡ ${t.latency_ms} ms</span>`;
    }

    const capsBadge = t.capabilities === 'both' 
      ? '<span class="badge-tv">TV</span> <span class="badge-movie">Movies</span>'
      : (t.capabilities === 'tv' ? '<span class="badge-tv">TV</span>' : '<span class="badge-movie">Movies</span>');

    return `
      <tr>
        <td style="font-weight: 700;">
          <div style="display: flex; align-items: center; gap: 0.5rem;">
            <div class="pulse-dot" style="width: 7px; height: 7px; background: ${t.enabled ? 'var(--accent-emerald)' : 'var(--text-muted)'}; box-shadow: none;"></div>
            <span>${t.name}</span>
          </div>
        </td>
        <td><span class="tag" style="text-transform: uppercase;">${t.type}</span></td>
        <td>${capsBadge}</td>
        <td>${latencyBadge}</td>
        <td style="font-size: 0.8rem; color: var(--text-muted); font-family: 'JetBrains Mono', monospace;">${t.categories || 'All'}</td>
        <td><span class="${t.enabled ? 'badge-downloaded' : 'badge-missing'}">${t.enabled ? 'Active' : 'Disabled'}</span></td>
        <td>
          <div style="display: flex; gap: 0.4rem;">
            <button class="btn btn-secondary btn-sm" onclick="testSingleTrackerBenchmark(${t.id})" title="Test Tracker Connection">Test</button>
            <button class="btn btn-danger btn-sm" onclick="deleteTracker(${t.id})" title="Delete Tracker">&times;</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function testSingleTrackerBenchmark(trackerId) {
  try {
    showToast('Testing tracker connection...', 'info');
    const res = await fetch(`/api/v1/indexers/${trackerId}/test`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(`Success: ${data.message}`, 'success');
      await loadTrackers();
    } else {
      showToast(`Failed: ${data.message}`, 'error');
    }
  } catch (err) {
    showToast('Test error: ' + err.message, 'error');
  }
}

async function testAllTrackersBenchmark() {
  const btn = document.getElementById('btn-test-trackers');
  if (btn) btn.disabled = true;
  showToast('Benchmarking all trackers concurrently...', 'info');

  try {
    const res = await fetch('/api/v1/trackers/test-all', { method: 'POST' });
    const data = await res.json();
    showToast(`Benchmark complete! Tested ${data.benchmarks ? data.benchmarks.length : 0} indexers.`, 'success');
    await loadTrackers();
  } catch (err) {
    showToast('Benchmark failed: ' + err.message, 'error');
  } finally {
    if (btn) btn.disabled = false;
  }
}

function openAddTrackerModal() {
  openModal('modal-add-tracker');
}

async function saveNewTracker() {
  try {
    const name = document.getElementById('new-tracker-name')?.value.trim();
    const type = document.getElementById('new-tracker-type')?.value;
    const caps = document.getElementById('new-tracker-caps')?.value || 'both';
    const url = document.getElementById('new-tracker-url')?.value.trim();
    const apiKey = document.getElementById('new-tracker-key')?.value.trim();

    if (!name || !url) {
      showToast('Tracker name and URL are required.', 'error');
      return;
    }

    const payload = {
      name: name,
      type: type,
      url: url,
      api_key: apiKey,
      capabilities: caps,
      categories: caps === 'movie' ? '2000' : (caps === 'tv' ? '5000' : '2000,5000'),
      enabled: true,
      priority: 1
    };

    const res = await fetch('/api/v1/indexers', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Failed to create tracker');
    showToast(`Tracker '${name}' added successfully!`, 'success');
    closeModal('modal-add-tracker');
    await loadTrackers();
  } catch (err) {
    showToast('Error saving tracker: ' + err.message, 'error');
  }
}

async function deleteTracker(id) {
  if (!confirm('Are you sure you want to delete this tracker?')) return;
  try {
    await fetch(`/api/v1/indexers/${id}`, { method: 'DELETE' });
    showToast('Tracker deleted', 'info');
    await loadTrackers();
  } catch (err) {
    showToast('Delete failed: ' + err.message, 'error');
  }
}

// ==========================================
// Series Detail Modal (TV)
// ==========================================
async function openSeriesDetailModal(seriesId) {
  try {
    const res = await fetch(`/api/v1/series/${seriesId}`);
    if (!res.ok) throw new Error('Failed to fetch series details');
    const data = await res.json();
    state.activeSeriesDetail = data;

    document.getElementById('detail-modal-title').textContent = data.title;
    document.getElementById('detail-name').textContent = data.title;
    document.getElementById('detail-poster').src = data.poster_url || '';
    document.getElementById('detail-poster').onerror = function() {
      this.src = `https://placehold.co/300x450/0d121c/ffffff?text=${encodeURIComponent(data.title)}`;
    };

    const overviewEl = document.createElement('div');
    overviewEl.innerHTML = data.overview || 'No overview available.';
    document.getElementById('detail-overview').textContent = overviewEl.textContent;

    const tagsContainer = document.getElementById('detail-tags');
    tagsContainer.innerHTML = `
      <span class="tag" style="color: var(--accent-cyan);">${data.network || 'Unknown'}</span>
      <span class="tag">${data.status}</span>
      <span class="tag">${data.premiered ? data.premiered.substring(0, 4) : ''}</span>
      ${(data.genres || []).map(g => `<span class="tag">${g}</span>`).join('')}
    `;

    const seasonsContainer = document.getElementById('detail-seasons-container');
    seasonsContainer.innerHTML = data.seasons.map(season => {
      const downloadedInSeason = season.episodes.filter(e => e.has_file).length;
      return `
        <div class="season-accordion">
          <div class="season-header" onclick="toggleSeasonAccordion(this)">
            <div class="season-title">
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><polyline points="6 9 12 15 18 9"></polyline></svg>
              <span>Season ${season.season_number}</span>
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
              ${downloadedInSeason}/${season.episodes.length} Episodes
            </div>
          </div>
          <div class="season-content">
            <table class="episodes-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>Title</th>
                  <th>Air Date</th>
                  <th>Status</th>
                  <th>Quality</th>
                  <th>Size</th>
                  <th>Search</th>
                </tr>
              </thead>
              <tbody>
                ${season.episodes.map(ep => {
                  let statusBadge = '<span class="badge-missing">Missing</span>';
                  if (ep.has_file) statusBadge = '<span class="badge-downloaded">Downloaded</span>';

                  const sizeMb = ep.file_size ? (ep.file_size / (1024 * 1024)).toFixed(0) + ' MB' : '-';
                  return `
                    <tr>
                      <td style="font-family: 'JetBrains Mono', monospace; font-weight: 600;">S${String(ep.season_number).padStart(2, '0')}E${String(ep.episode_number).padStart(2, '0')}</td>
                      <td style="font-weight: 500;">${ep.title}</td>
                      <td style="color: var(--text-muted); font-size: 0.8rem;">${ep.air_date || 'TBA'}</td>
                      <td>${statusBadge}</td>
                      <td><span style="font-size: 0.75rem; color: var(--accent-indigo);">${ep.quality || '-'}</span></td>
                      <td style="font-size: 0.8rem; color: var(--text-muted);">${sizeMb}</td>
                      <td>
                        <button class="btn btn-secondary btn-sm" onclick="triggerInteractiveSearch('${data.title.replace(/'/g, "\\'")}', ${ep.season_number}, ${ep.episode_number}, ${data.id}, 'tv', null)" title="Interactive Search">
                          <svg width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
                        </button>
                      </td>
                    </tr>
                  `;
                }).join('')}
              </tbody>
            </table>
          </div>
        </div>
      `;
    }).join('');

    openModal('modal-series-detail');
  } catch (err) {
    showToast('Failed to open series: ' + err.message, 'error');
  }
}

function toggleSeasonAccordion(header) {
  const content = header.nextElementSibling;
  const isHidden = content.style.display === 'none';
  content.style.display = isHidden ? 'block' : 'none';
}

async function scanCurrentSeries() {
  if (!state.activeSeriesDetail) return;
  try {
    showToast('Scanning disk folder...', 'info');
    const res = await fetch(`/api/v1/series/${state.activeSeriesDetail.id}/scan`, { method: 'POST' });
    const data = await res.json();
    showToast(`Scan complete! Matched ${data.matched_files} files.`, 'success');
    await openSeriesDetailModal(state.activeSeriesDetail.id);
    await loadSeries();
  } catch (err) {
    showToast('Scan failed: ' + err.message, 'error');
  }
}

async function deleteCurrentSeries() {
  if (!state.activeSeriesDetail) return;
  if (!confirm(`Are you sure you want to remove "${state.activeSeriesDetail.title}" from Pulsearr?`)) return;

  const deleteFiles = confirm('Do you also want to delete the show files from disk?');
  try {
    await fetch(`/api/v1/series/${state.activeSeriesDetail.id}?delete_files=${deleteFiles}`, { method: 'DELETE' });
    showToast('Series deleted successfully.', 'success');
    closeModal('modal-series-detail');
    await loadSeries();
  } catch (err) {
    showToast('Delete failed: ' + err.message, 'error');
  }
}

// ==========================================
// Movie Detail Modal (Radarr)
// ==========================================
async function openMovieDetailModal(movieId) {
  try {
    const res = await fetch(`/api/v1/movies/${movieId}`);
    if (!res.ok) throw new Error('Failed to load movie details');
    const movie = await res.json();
    state.activeMovieDetail = movie;

    document.getElementById('movie-detail-modal-title').textContent = `${movie.title} (${movie.year || 'TBA'})`;
    document.getElementById('movie-detail-name').textContent = movie.title;
    document.getElementById('movie-detail-poster').src = movie.poster_url || '';
    document.getElementById('movie-detail-poster').onerror = function() {
      this.src = `https://placehold.co/300x450/0d121c/ffffff?text=${encodeURIComponent(movie.title)}`;
    };

    document.getElementById('movie-detail-overview').textContent = movie.overview || 'No synopsis available.';

    const tagsContainer = document.getElementById('movie-detail-tags');
    tagsContainer.innerHTML = `
      <span class="tag" style="color: var(--accent-violet);">${movie.year || 'TBA'}</span>
      <span class="tag">${movie.runtime || 0} min</span>
      <span class="tag">★ ${movie.rating || 0.0}</span>
      <span class="${movie.has_file ? 'badge-downloaded' : 'badge-missing'}">${movie.has_file ? 'Downloaded (' + (movie.quality || 'Ready') + ')' : 'Missing'}</span>
      ${(movie.genres || []).map(g => `<span class="tag">${g}</span>`).join('')}
    `;

    openModal('modal-movie-detail');
  } catch (err) {
    showToast('Failed to load movie: ' + err.message, 'error');
  }
}

async function deleteCurrentMovie() {
  if (!state.activeMovieDetail) return;
  if (!confirm(`Are you sure you want to remove "${state.activeMovieDetail.title}" from library?`)) return;

  const deleteFiles = confirm('Do you also want to delete the movie files from disk?');
  try {
    await fetch(`/api/v1/movies/${state.activeMovieDetail.id}?delete_files=${deleteFiles}`, { method: 'DELETE' });
    showToast('Movie deleted.', 'success');
    closeModal('modal-movie-detail');
    await loadMovies();
  } catch (err) {
    showToast('Delete failed: ' + err.message, 'error');
  }
}

function triggerMovieInteractiveSearch() {
  if (!state.activeMovieDetail) return;
  closeModal('modal-movie-detail');
  triggerInteractiveSearch(state.activeMovieDetail.title, null, null, null, 'movie', state.activeMovieDetail.id);
}

// ==========================================
// Interactive Release Search & Grab (TV & Movies)
// ==========================================
async function triggerInteractiveSearch(mediaTitle, seasonNum = null, episodeNum = null, seriesId = null, mediaType = 'tv', movieId = null) {
  const modal = document.getElementById('modal-release-search');
  const titleEl = document.getElementById('release-search-title');
  const loader = document.getElementById('release-search-loader');
  const table = document.getElementById('release-search-table');
  const tbody = document.getElementById('release-search-tbody');
  const empty = document.getElementById('release-search-empty');

  const isMovie = mediaType === 'movie';
  titleEl.textContent = isMovie ? `Search Movie: ${mediaTitle}` : `Search TV: ${mediaTitle} S${String(seasonNum).padStart(2, '0')}E${String(episodeNum).padStart(2, '0')}`;
  loader.style.display = 'block';
  table.style.display = 'none';
  empty.style.display = 'none';
  tbody.innerHTML = '';
  openModal('modal-release-search');

  try {
    let url = `/api/v1/search/releases?query=${encodeURIComponent(mediaTitle)}&media_type=${mediaType}`;
    if (!isMovie && seasonNum && episodeNum) {
      url += `&season=${seasonNum}&episode=${episodeNum}`;
    }
    const res = await fetch(url);
    const candidates = await res.json();

    loader.style.display = 'none';

    if (candidates.length === 0) {
      empty.style.display = 'block';
      return;
    }

    table.style.display = 'table';
    tbody.innerHTML = candidates.map((cand, idx) => {
      const sizeGb = (cand.size / (1024 * 1024 * 1024)).toFixed(2);
      const isRejected = cand.reject_reasons && cand.reject_reasons.length > 0;
      const rejectText = isRejected ? cand.reject_reasons.join(', ') : '';

      return `
        <tr style="${isRejected ? 'opacity: 0.6;' : ''}">
          <td>
            <span style="font-weight: 700; color: ${cand.parsed.score > 80 ? 'var(--accent-emerald)' : 'var(--accent-amber)'};">
              ${cand.parsed.score}
            </span>
          </td>
          <td>
            <div style="font-weight: 600; font-size: 0.85rem;" title="${cand.title}">${cand.title}</div>
            <div style="font-size: 0.75rem; color: var(--text-muted); display: flex; gap: 0.5rem; margin-top: 2px;">
              <span>${cand.parsed.resolution}</span>
              <span>${cand.parsed.source}</span>
              <span>${cand.parsed.codec}</span>
              <span>${cand.parsed.audio}</span>
            </div>
            ${isRejected ? `<div style="font-size: 0.7rem; color: var(--accent-rose); margin-top: 2px;">⚠️ ${rejectText}</div>` : ''}
          </td>
          <td><span class="tag">${cand.indexer_name}</span></td>
          <td style="font-size: 0.8rem; font-family: 'JetBrains Mono', monospace;">${sizeGb} GB</td>
          <td>
            <span style="color: var(--accent-emerald); font-weight: 600;">${cand.seeders || 0}</span> /
            <span style="color: var(--text-muted);">${cand.leechers || 0}</span>
          </td>
          <td><span class="badge-downloaded" style="font-size: 0.7rem;">${cand.parsed.quality_tag}</span></td>
          <td>
            <button class="btn btn-primary btn-sm" onclick='grabCandidateRelease(${JSON.stringify(cand).replace(/'/g, "&apos;")}, ${isMovie ? "null" : seriesId}, ${seasonNum || "null"}, ${episodeNum || "null"}, "${mediaType}", ${isMovie ? movieId : "null"})'>
              ⚡ Grab
            </button>
          </td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    loader.style.display = 'none';
    showToast('Search error: ' + err.message, 'error');
  }
}

async function grabCandidateRelease(candidate, seriesId = null, seasonNum = null, episodeNum = null, mediaType = 'tv', movieId = null) {
  try {
    showToast(`Grabbing release '${candidate.title.substring(0, 30)}...'`, 'info');
    const res = await fetch('/api/v1/search/grab', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        candidate: candidate,
        media_type: mediaType,
        series_id: seriesId,
        movie_id: movieId,
        season_number: seasonNum,
        episode_number: episodeNum
      })
    });
    if (!res.ok) throw new Error('Grab failed');
    showToast('Release queued successfully!', 'success');
    closeModal('modal-release-search');
    switchView('activity');
  } catch (err) {
    showToast('Grab error: ' + err.message, 'error');
  }
}

// ==========================================
// Live Activity Queue (Unified TV + Movies)
// ==========================================
async function loadQueue() {
  try {
    const res = await fetch('/api/v1/queue');
    const items = await res.json();
    renderQueue(items);
  } catch (err) {
    console.error('Queue load error:', err);
  }
}

function renderQueue(items) {
  const tbody = document.getElementById('queue-table-body');
  const empty = document.getElementById('queue-empty');
  const ticker = document.getElementById('queue-status-ticker');
  const navBadge = document.getElementById('nav-queue-count');

  state.queueCount = items.length;
  if (navBadge) {
    navBadge.textContent = items.length;
    navBadge.style.display = items.length > 0 ? 'inline-block' : 'none';
  }

  if (!tbody || !empty) return;

  if (items.length === 0) {
    tbody.innerHTML = '';
    empty.style.display = 'block';
    if (ticker) ticker.textContent = 'Idle';
    return;
  }

  empty.style.display = 'none';
  if (ticker) ticker.textContent = `${items.length} Active Download${items.length === 1 ? '' : 's'}`;

  tbody.innerHTML = items.map(q => {
    const speedMb = (q.download_speed / (1024 * 1024)).toFixed(1);
    const sizeGb = (q.size / (1024 * 1024 * 1024)).toFixed(2);
    const isMovie = q.media_type === 'movie' || Boolean(q.movie_id);
    const typeBadge = isMovie ? '<span class="badge-movie">Movie</span>' : '<span class="badge-tv">TV</span>';
    const epLabel = isMovie ? (q.title || 'Movie') : (q.series_title && q.season_number ? `${q.series_title} S${String(q.season_number).padStart(2, '0')}E${String(q.episode_number).padStart(2, '0')}` : (q.series_title || 'TV Release'));

    return `
      <tr>
        <td>${typeBadge}</td>
        <td style="font-weight: 600;">${epLabel}</td>
        <td>
          <div style="font-size: 0.85rem; max-width: 380px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${q.title}">${q.title}</div>
        </td>
        <td>
          <div style="font-size: 0.75rem; font-weight: 600; color: var(--accent-cyan);">${q.progress}% @ ${speedMb} MB/s</div>
          <div class="queue-progress-bar">
            <div class="queue-progress-fill" style="width: ${q.progress}%"></div>
          </div>
        </td>
        <td style="font-size: 0.8rem; font-family: 'JetBrains Mono', monospace; color: var(--text-muted);">${q.eta > 0 ? q.eta + 's' : '-'}</td>
        <td style="font-size: 0.8rem; font-family: 'JetBrains Mono', monospace;">${sizeGb} GB</td>
        <td><span class="badge-downloaded" style="font-size: 0.7rem;">${q.quality}</span></td>
        <td><span class="tag">${q.indexer}</span></td>
        <td>
          <div style="display: flex; gap: 0.4rem;">
            <button class="btn btn-success btn-sm" onclick="forceImportQueueItem(${q.id})" title="Force Immediate Import">Import</button>
            <button class="btn btn-danger btn-sm" onclick="removeQueueItem(${q.id})" title="Cancel Download">&times;</button>
          </div>
        </td>
      </tr>
    `;
  }).join('');
}

async function forceImportQueueItem(queueId) {
  try {
    showToast('Importing media...', 'info');
    const res = await fetch(`/api/v1/queue/${queueId}/import`, { method: 'POST' });
    if (!res.ok) throw new Error('Force import failed');
    showToast('Import successful!', 'success');
    await loadQueue();
    await loadSeries();
    await loadMovies();
  } catch (err) {
    showToast('Import failed: ' + err.message, 'error');
  }
}

async function removeQueueItem(queueId) {
  if (!confirm('Cancel and delete this download?')) return;
  try {
    await fetch(`/api/v1/queue/${queueId}`, { method: 'DELETE' });
    showToast('Item cancelled', 'info');
    await loadQueue();
  } catch (err) {
    showToast('Cancel failed: ' + err.message, 'error');
  }
}

function startQueuePolling() {
  setInterval(() => {
    if (state.currentView === 'activity' || state.queueCount > 0) {
      loadQueue();
    }
  }, 4000);
}

// ==========================================
// Calendar View
// ==========================================
async function loadCalendar() {
  try {
    const res = await fetch('/api/v1/calendar');
    const episodes = await res.json();
    const grid = document.getElementById('calendar-grid');
    const empty = document.getElementById('calendar-empty');
    if (!grid || !empty) return;

    if (episodes.length === 0) {
      grid.innerHTML = '';
      empty.style.display = 'block';
      return;
    }

    empty.style.display = 'none';
    grid.innerHTML = episodes.map(ep => {
      return `
        <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 1rem; display: flex; gap: 0.85rem;">
          <img src="${ep.poster_url || ''}" style="width: 55px; height: 80px; object-fit: cover; border-radius: var(--radius-sm);" onerror="this.src='https://placehold.co/100x150/0d121c/ffffff?text=TV'">
          <div style="display: flex; flex-direction: column; justify-content: center;">
            <div style="font-size: 0.75rem; color: var(--accent-cyan); font-weight: 600;">${ep.air_date}</div>
            <div style="font-weight: 700; font-size: 0.9rem; margin: 2px 0;">${ep.series_title}</div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">S${String(ep.season_number).padStart(2, '0')}E${String(ep.episode_number).padStart(2, '0')} - ${ep.title}</div>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Calendar error:', err);
  }
}

// ==========================================
// History View (Unified Audit Log)
// ==========================================
async function loadHistory() {
  try {
    const res = await fetch('/api/v1/history');
    const items = await res.json();
    const tbody = document.getElementById('history-table-body');
    const empty = document.getElementById('history-empty');
    if (!tbody || !empty) return;

    if (items.length === 0) {
      tbody.innerHTML = '';
      empty.style.display = 'block';
      return;
    }

    empty.style.display = 'none';
    tbody.innerHTML = items.map(h => {
      let eventBadge = `<span class="tag">${h.event_type}</span>`;
      if (h.event_type === 'grabbed') eventBadge = `<span class="badge-downloading">Grabbed</span>`;
      if (h.event_type === 'imported') eventBadge = `<span class="badge-downloaded">Imported</span>`;

      const isMovie = h.media_type === 'movie' || Boolean(h.movie_id);
      const typeBadge = isMovie ? '<span class="badge-movie">Movie</span>' : '<span class="badge-tv">TV</span>';

      return `
        <tr>
          <td>${typeBadge}</td>
          <td>${eventBadge}</td>
          <td style="font-weight: 600;">${h.series_title || (isMovie ? h.source_title : 'Item')}</td>
          <td style="font-size: 0.85rem; max-width: 320px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="${h.source_title}">${h.source_title}</td>
          <td><span class="tag">${h.quality}</span></td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${h.download_client || '-'}</td>
          <td style="font-size: 0.8rem; color: var(--text-muted);">${h.timestamp}</td>
        </tr>
      `;
    }).join('');
  } catch (err) {
    console.error('History error:', err);
  }
}

// ==========================================
// Settings Panel (Media, Clients, Profiles)
// ==========================================
function switchSettingsTab(tabName) {
  document.querySelectorAll('.settings-tab-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  document.querySelectorAll('.settings-pane').forEach(pane => {
    pane.classList.remove('active');
  });

  const btn = Array.from(document.querySelectorAll('.settings-tab-btn')).find(b => b.getAttribute('onclick')?.includes(tabName));
  if (btn) btn.classList.add('active');

  const pane = document.getElementById(`settings-pane-${tabName}`);
  if (pane) pane.classList.add('active');

  if (tabName === 'profiles') loadProfilesSettings();
  else if (tabName === 'clients') loadClientsSettings();
}

async function loadSettings() {
  try {
    const res = await fetch('/api/v1/settings');
    const cfg = await res.json();
    document.getElementById('setting-root-folder').value = cfg.root_folder || '';
    document.getElementById('setting-movies-root-folder').value = cfg.movies_root_folder || '';
    document.getElementById('setting-naming-format').value = cfg.standard_episode_format || '';
    document.getElementById('setting-movie-naming-format').value = cfg.standard_movie_format || '{Movie Title} ({Year}) [{Quality}]';
    document.getElementById('setting-import-mode').value = cfg.import_mode || 'move';

    livePreviewNamingFormat('tv');
    livePreviewNamingFormat('movie');
  } catch (err) {
    showToast('Failed to load settings', 'error');
  }
}

async function livePreviewNamingFormat(mediaType = 'tv') {
  if (mediaType === 'movie') {
    const fmt = document.getElementById('setting-movie-naming-format')?.value || '';
    const previewEl = document.getElementById('movie-naming-format-preview');
    if (!previewEl) return;
    try {
      const res = await fetch('/api/v1/settings/preview-format', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format_template: fmt, media_type: 'movie' })
      });
      const data = await res.json();
      previewEl.textContent = data.preview;
    } catch (err) {
      previewEl.textContent = 'Formatting syntax error';
    }
  } else {
    const fmt = document.getElementById('setting-naming-format')?.value || '';
    const previewEl = document.getElementById('naming-format-preview');
    if (!previewEl) return;
    try {
      const res = await fetch('/api/v1/settings/preview-format', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ format_template: fmt, media_type: 'tv' })
      });
      const data = await res.json();
      previewEl.textContent = data.preview;
    } catch (err) {
      previewEl.textContent = 'Formatting syntax error';
    }
  }
}

async function saveMediaSettings() {
  try {
    const payload = {
      root_folder: document.getElementById('setting-root-folder').value,
      movies_root_folder: document.getElementById('setting-movies-root-folder').value,
      standard_episode_format: document.getElementById('setting-naming-format').value,
      standard_movie_format: document.getElementById('setting-movie-naming-format').value,
      import_mode: document.getElementById('setting-import-mode').value,
      auto_import: true,
      rename_episodes: true
    };
    await fetch('/api/v1/settings', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    showToast('Settings saved successfully!', 'success');
  } catch (err) {
    showToast('Save failed: ' + err.message, 'error');
  }
}

async function loadProfiles() {
  try {
    const res = await fetch('/api/v1/profiles');
    state.profiles = await res.json();
    const tvSelect = document.getElementById('add-series-profile');
    if (tvSelect) {
      tvSelect.innerHTML = state.profiles.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    }
    const movieSelect = document.getElementById('add-movie-profile');
    if (movieSelect) {
      movieSelect.innerHTML = state.profiles.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
    }
  } catch (err) {
    console.error('Profiles load error:', err);
  }
}

async function loadProfilesSettings() {
  const container = document.getElementById('profiles-list-container');
  if (!container) return;
  container.innerHTML = state.profiles.map(p => `
    <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 1.25rem;">
      <h4 style="font-weight: 700; font-size: 1rem; margin-bottom: 0.5rem;">${p.name}</h4>
      <div style="display: flex; flex-wrap: wrap; gap: 0.4rem;">
        ${p.items.map(item => `<span class="tag" style="color: var(--accent-cyan);">${item.name} (${item.score} pts)</span>`).join('')}
      </div>
    </div>
  `).join('');
}

// ==========================================
// Download Clients & Remote Seedboxes
// ==========================================
async function loadClientsSettings() {
  const container = document.getElementById('clients-list-container');
  if (!container) return;
  try {
    const res = await fetch('/api/v1/download-clients');
    const clients = await res.json();

    if (clients.length === 0) {
      container.innerHTML = `
        <div style="background: var(--bg-card); border: 1px dashed var(--border-subtle); border-radius: var(--radius-lg); padding: 1.5rem; text-align: center; color: var(--text-muted);">
          No download clients configured. Click "+ Add Client" above to connect your local or remote qBittorrent host.
        </div>
      `;
      return;
    }

    container.innerHTML = clients.map(c => {
      const isRemote = c.host && c.host !== 'localhost' && c.host !== '127.0.0.1';
      const sslBadge = c.use_ssl ? '<span class="badge-ssl">HTTPS</span>' : '<span class="tag">HTTP</span>';
      const remoteBadge = isRemote ? '<span class="badge-remote">Remote Seedbox</span>' : '<span class="tag">Local</span>';
      const mediaBadge = c.media_type === 'both' 
        ? '<span class="badge-tv">TV</span> <span class="badge-movie">Movies</span>'
        : (c.media_type === 'movie' ? '<span class="badge-movie">Movies</span>' : '<span class="badge-tv">TV</span>');

      const pathMapInfo = (c.remote_path && c.local_path)
        ? `<div style="font-size: 0.75rem; color: var(--accent-cyan); font-family: 'JetBrains Mono', monospace; margin-top: 4px;">
             Path Mapping: ${c.remote_path} ➔ ${c.local_path}
           </div>`
        : '';

      return `
        <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-lg); padding: 1.25rem; display: flex; justify-content: space-between; align-items: center;">
          <div>
            <div style="display: flex; align-items: center; gap: 0.5rem; margin-bottom: 3px;">
              <span style="font-weight: 700; font-size: 1rem;">${c.name}</span>
              ${remoteBadge}
              ${sslBadge}
              ${mediaBadge}
            </div>
            <div style="font-size: 0.8rem; color: var(--text-muted);">
              ${c.type.toUpperCase()} • ${c.use_ssl ? 'https://' : 'http://'}${c.host}:${c.port}${c.url_base || ''}
            </div>
            ${pathMapInfo}
          </div>
          <div style="display: flex; gap: 0.5rem;">
            <button class="btn btn-secondary btn-sm" onclick="testDownloadClient(${c.id})">Test Connection</button>
            <button class="btn btn-danger btn-sm" onclick="deleteDownloadClient(${c.id})">&times;</button>
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    console.error('Clients load error:', err);
  }
}

function openAddClientModal() {
  openModal('modal-add-client');
}

async function saveDownloadClient() {
  try {
    const name = document.getElementById('client-name')?.value.trim();
    const type = document.getElementById('client-type')?.value;
    const mediaType = document.getElementById('client-media-type')?.value || 'both';
    const host = document.getElementById('client-host')?.value.trim();
    const port = parseInt(document.getElementById('client-port')?.value || '8080', 10);
    const useSsl = document.getElementById('client-use-ssl')?.checked || false;
    const urlBase = document.getElementById('client-url-base')?.value.trim() || '';
    const username = document.getElementById('client-username')?.value.trim() || '';
    const password = document.getElementById('client-password')?.value || '';
    const remotePath = document.getElementById('client-remote-path')?.value.trim() || '';
    const localPath = document.getElementById('client-local-path')?.value.trim() || '';

    if (!name || !host) {
      showToast('Client Name and Host are required.', 'error');
      return;
    }

    const payload = {
      name: name,
      type: type,
      host: host,
      port: port,
      use_ssl: useSsl,
      url_base: urlBase,
      username: username,
      password: password,
      category: mediaType === 'movie' ? 'movies' : 'tv',
      media_type: mediaType,
      download_path: '',
      remote_path: remotePath,
      local_path: localPath,
      enabled: true,
      priority: 1
    };

    const res = await fetch('/api/v1/download-clients', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) throw new Error('Failed to create download client');
    showToast(`Download client '${name}' added successfully!`, 'success');
    closeModal('modal-add-client');
    await loadClientsSettings();
  } catch (err) {
    showToast('Error saving client: ' + err.message, 'error');
  }
}

async function deleteDownloadClient(clientId) {
  if (!confirm('Are you sure you want to delete this download client?')) return;
  try {
    await fetch(`/api/v1/download-clients/${clientId}`, { method: 'DELETE' });
    showToast('Download client deleted', 'info');
    await loadClientsSettings();
  } catch (err) {
    showToast('Delete failed: ' + err.message, 'error');
  }
}

async function testDownloadClient(id) {
  try {
    showToast('Testing download client...', 'info');
    const res = await fetch(`/api/v1/download-clients/${id}/test`, { method: 'POST' });
    const data = await res.json();
    if (data.success) {
      showToast(`Client Test Passed: ${data.message}`, 'success');
    } else {
      showToast(`Client Test Failed: ${data.message}`, 'error');
    }
  } catch (err) {
    showToast('Test failed: ' + err.message, 'error');
  }
}

// ==========================================
// System Diagnostics & Live Event Stream
// ==========================================
async function loadSystemDiagnostics() {
  try {
    const res = await fetch('/api/v1/system/status');
    const data = await res.json();
    document.getElementById('sys-disk-free').textContent = `${data.disk.free_gb} GB`;
    document.getElementById('sys-disk-total').textContent = `of ${data.disk.total_gb} GB (${data.disk.percent_used}% used)`;
    document.getElementById('sys-series-count').textContent = `${data.library.series} Shows • ${data.library.movies || 0} Movies`;
    document.getElementById('sys-episodes-count').textContent = `${data.library.episodes} Episodes (${data.library.downloaded} Downloaded)`;
    document.getElementById('sys-db-size').textContent = `${data.database_size_kb} KB`;
    document.getElementById('sys-python-ver').textContent = `Python ${data.python_version} (${data.platform})`;
  } catch (err) {
    console.error('System stats error:', err);
  }
}

function setupSSE() {
  try {
    state.sseConnection = new EventSource('/api/v1/system/events');
    state.sseConnection.onmessage = (event) => {
      try {
        const payload = JSON.parse(event.data);
        handleSystemEvent(payload);
      } catch (e) {}
    };
  } catch (err) {
    console.warn('SSE stream not available, falling back to polling.');
  }
}

function handleSystemEvent(payload) {
  const terminal = document.getElementById('live-log-terminal');
  if (terminal && payload.event) {
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    const timeStr = new Date().toLocaleTimeString();
    entry.innerHTML = `<span class="log-time">[${timeStr}]</span> <span class="log-info">[${payload.event}]</span> <span>${JSON.stringify(payload.data)}</span>`;
    terminal.appendChild(entry);
    terminal.scrollTop = terminal.scrollHeight;
  }

  if (payload.event === 'import_complete') {
    showToast(`Imported ${payload.data.title}!`, 'success');
    if (payload.data.media_type === 'movie') {
      loadMovies();
    } else {
      loadSeries();
    }
  }
}

function clearLiveLogs() {
  const terminal = document.getElementById('live-log-terminal');
  if (terminal) terminal.innerHTML = '';
}

async function triggerManualRssSync() {
  try {
    showToast('Triggering RSS sync across indexers...', 'info');
    await fetch('/api/v1/system/rss-sync', { method: 'POST' });
    showToast('RSS sync cycle active in background.', 'success');
  } catch (err) {
    showToast('RSS sync failed: ' + err.message, 'error');
  }
}

// ==========================================
// Add Series Modal & TVMaze Search
// ==========================================
function openAddSeriesModal() {
  openModal('modal-add-series');
  document.getElementById('tvmaze-search-input')?.focus();
}

function debounceTvMazeSearch() {
  clearTimeout(state.debounceTimer);
  state.debounceTimer = setTimeout(performTvMazeSearch, 300);
}

async function performTvMazeSearch() {
  const query = document.getElementById('tvmaze-search-input')?.value.trim();
  const container = document.getElementById('tvmaze-results-container');
  if (!query || query.length < 2) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = '<div style="text-align: center; padding: 1.5rem; color: var(--text-muted);"><div class="pulse-dot" style="margin: 0 auto 8px auto;"></div>Searching TVMaze...</div>';

  try {
    const res = await fetch(`/api/v1/search/tvmaze?q=${encodeURIComponent(query)}`);
    const results = await res.json();

    if (results.length === 0) {
      container.innerHTML = '<div style="text-align: center; padding: 1.5rem; color: var(--text-muted);">No shows found matching query.</div>';
      return;
    }

    container.innerHTML = results.map(show => {
      const summaryClean = (show.overview || '').replace(/<[^>]*>?/gm, '');
      const existing = state.series.some(s => s.tvmaze_id === show.tvmaze_id);

      return `
        <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.85rem; display: flex; gap: 1rem; align-items: center;">
          <img src="${show.poster_url || ''}" style="width: 55px; height: 80px; object-fit: cover; border-radius: var(--radius-sm); flex-shrink: 0;" onerror="this.src='https://placehold.co/100x150/0d121c/ffffff?text=TV'">
          <div style="flex: 1; min-width: 0;">
            <div style="font-weight: 700; font-size: 0.95rem;">${show.title} <span style="font-size: 0.8rem; color: var(--text-muted); font-weight: 500;">(${show.premiered ? show.premiered.substring(0, 4) : 'TBA'})</span></div>
            <div style="font-size: 0.75rem; color: var(--accent-indigo); margin: 2px 0;">${show.network} • ${show.status}</div>
            <p style="font-size: 0.75rem; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 480px;">${summaryClean}</p>
          </div>
          <div>
            ${existing 
              ? `<span class="badge-downloaded">In Library</span>` 
              : `<button class="btn btn-primary btn-sm" onclick="addShowToLibrary(${show.tvmaze_id}, '${show.title.replace(/'/g, "\\'")}')">+ Add</button>`
            }
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div style="color: var(--accent-rose); padding: 1rem;">Search error: ${err.message}</div>`;
  }
}

async function addShowToLibrary(tvmazeId, title) {
  try {
    showToast(`Adding '${title}' to library...`, 'info');
    const profileId = parseInt(document.getElementById('add-series-profile')?.value || '1', 10);
    const res = await fetch('/api/v1/series', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        tvmaze_id: tvmazeId,
        title: title,
        quality_profile_id: profileId,
        monitored: true
      })
    });
    if (!res.ok) {
      const errData = await res.json();
      throw new Error(errData.detail || 'Add failed');
    }
    showToast(`'${title}' added successfully!`, 'success');
    closeModal('modal-add-series');
    await loadSeries();
  } catch (err) {
    showToast('Error adding show: ' + err.message, 'error');
  }
}

// ==========================================
// Add Movie Modal & Metadata Search (Radarr)
// ==========================================
function openAddMovieModal() {
  const select = document.getElementById('add-movie-profile');
  if (select && state.profiles.length > 0) {
    select.innerHTML = state.profiles.map(p => `<option value="${p.id}">${p.name}</option>`).join('');
  }
  openModal('modal-add-movie');
  document.getElementById('movie-search-input')?.focus();
}

function debounceMovieSearch() {
  clearTimeout(state.movieDebounceTimer);
  state.movieDebounceTimer = setTimeout(performMovieSearch, 300);
}

async function performMovieSearch() {
  const query = document.getElementById('movie-search-input')?.value.trim();
  const container = document.getElementById('movie-results-container');
  if (!query || query.length < 2) {
    container.innerHTML = '';
    return;
  }

  container.innerHTML = '<div style="text-align: center; padding: 1.5rem; color: var(--text-muted);"><div class="pulse-dot" style="margin: 0 auto 8px auto;"></div>Searching movie databases (YTS/Public APIs)...</div>';

  try {
    const res = await fetch(`/api/v1/search/movies?q=${encodeURIComponent(query)}`);
    const results = await res.json();

    if (results.length === 0) {
      container.innerHTML = '<div style="text-align: center; padding: 1.5rem; color: var(--text-muted);">No movies found matching query.</div>';
      return;
    }

    container.innerHTML = results.map(movie => {
      const existing = state.movies.some(m => m.tmdb_id === movie.tmdb_id || (m.title.toLowerCase() === movie.title.toLowerCase() && m.year === movie.year));
      const movieJson = JSON.stringify(movie).replace(/'/g, "&apos;");

      return `
        <div style="background: var(--bg-card); border: 1px solid var(--border-subtle); border-radius: var(--radius-md); padding: 0.85rem; display: flex; gap: 1rem; align-items: center;">
          <img src="${movie.poster_url || ''}" style="width: 55px; height: 80px; object-fit: cover; border-radius: var(--radius-sm); flex-shrink: 0;" onerror="this.src='https://placehold.co/100x150/0d121c/ffffff?text=Movie'">
          <div style="flex: 1; min-width: 0;">
            <div style="font-weight: 700; font-size: 0.95rem;">
              ${movie.title} <span style="font-size: 0.8rem; color: var(--text-muted); font-weight: 500;">(${movie.year || 'TBA'})</span>
            </div>
            <div style="font-size: 0.75rem; color: var(--accent-violet); margin: 2px 0;">
              ${movie.genres ? movie.genres.join(', ') : 'Film'} • ★ ${movie.rating || 'N/A'} • ${movie.runtime || 0} min
            </div>
            <p style="font-size: 0.75rem; color: var(--text-secondary); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 480px;">${movie.overview || 'No overview available.'}</p>
          </div>
          <div>
            ${existing 
              ? `<span class="badge-downloaded">In Library</span>` 
              : `<button class="btn btn-primary btn-sm" onclick='addMovieToLibrary(${movieJson})'>+ Add</button>`
            }
          </div>
        </div>
      `;
    }).join('');
  } catch (err) {
    container.innerHTML = `<div style="color: var(--accent-rose); padding: 1rem;">Movie search error: ${err.message}</div>`;
  }
}

async function addMovieToLibrary(movieData) {
  try {
    showToast(`Adding '${movieData.title}' to library...`, 'info');
    const profileId = parseInt(document.getElementById('add-movie-profile')?.value || '1', 10);
    const monitored = document.getElementById('add-movie-monitored')?.value === 'true';

    const payload = {
      tmdb_id: movieData.tmdb_id || 0,
      imdb_id: movieData.imdb_id || '',
      title: movieData.title,
      year: movieData.year || 0,
      overview: movieData.overview || '',
      poster_url: movieData.poster_url || '',
      genres: movieData.genres || [],
      rating: movieData.rating || 0.0,
      runtime: movieData.runtime || 0,
      quality_profile_id: profileId,
      monitored: monitored
    };

    const res = await fetch('/api/v1/movies', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      const err = await res.json();
      throw new Error(err.detail || 'Failed to add movie');
    }

    showToast(`'${movieData.title}' added to library!`, 'success');
    closeModal('modal-add-movie');
    await loadMovies();
  } catch (err) {
    showToast('Error adding movie: ' + err.message, 'error');
  }
}

// ==========================================
// Modal Helpers & Toast System
// ==========================================
function openModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.add('open');
}

function closeModal(modalId) {
  const el = document.getElementById(modalId);
  if (el) el.classList.remove('open');
}

function showToast(message, type = 'info') {
  const container = document.getElementById('toast-container');
  if (!container) return;

  const toast = document.createElement('div');
  toast.className = `toast ${type}`;
  toast.textContent = message;
  container.appendChild(toast);

  setTimeout(() => {
    toast.style.opacity = '0';
    toast.style.transform = 'translateX(20px)';
    toast.style.transition = 'all 0.25s ease';
    setTimeout(() => toast.remove(), 250);
  }, 3500);
}
