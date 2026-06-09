// ── 공통 드롭다운 렌더러 ──
function renderDropdownItems(people) {
  return people.map(p => {
    const krName = p.fullNameKr || '';
    const enName = p.fullName || '';
    const displayName = krName ? `${krName} <span style="color:#94a3b8;font-weight:400;font-size:.85em">${enName}</span>` : enName;
    return `
      <div class="sd-item" onclick="location.href='/player/${p.id}'">
        <img src="https://img.mlbstatic.com/mlb-photos/image/upload/d_people:generic:headshot:67:current.png/w_213,q_auto:best/v1/people/${p.id}/headshot/67/current" alt="${enName}" />
        <div>
          <div class="sd-name">${displayName}</div>
          <div class="sd-sub">${p.primaryPosition?.name || p.primaryPosition?.abbreviation || ''} · ${p.currentTeam?.name || ''}</div>
        </div>
      </div>`;
  }).join('');
}

// ── 네비게이션 검색 ──
let navSearchTimer = null;

function navSearch() {
  const q = document.getElementById('nav-search-input')?.value.trim();
  if (q) window.location.href = '/search?q=' + encodeURIComponent(q);
}

function heroSearch() {
  const q = document.getElementById('hero-search-input')?.value.trim();
  if (q) window.location.href = '/search?q=' + encodeURIComponent(q);
}

function setupNavSearch() {
  const input = document.getElementById('nav-search-input');
  const dropdown = document.getElementById('nav-search-dropdown');
  if (!input || !dropdown) return;

  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') navSearch();
  });

  input.addEventListener('input', () => {
    clearTimeout(navSearchTimer);
    const q = input.value.trim();
    if (!q) { dropdown.classList.add('hidden'); return; }
    navSearchTimer = setTimeout(() => fetchDropdown(q, dropdown, 6), 300);
  });

  document.addEventListener('click', e => {
    if (!e.target.closest('.nav-search-wrap')) dropdown.classList.add('hidden');
  });
}

function setupHeroSearch() {
  const input = document.getElementById('hero-search-input');
  const dropdown = document.getElementById('hero-search-dropdown');
  if (!input || !dropdown) return;

  let timer = null;
  input.addEventListener('keydown', e => {
    if (e.key === 'Enter') heroSearch();
  });
  input.addEventListener('input', () => {
    clearTimeout(timer);
    const q = input.value.trim();
    if (!q) { dropdown.classList.add('hidden'); return; }
    timer = setTimeout(() => fetchDropdown(q, dropdown, 5), 300);
  });

  document.addEventListener('click', e => {
    if (!e.target.closest('.hero-search-box')) dropdown.classList.add('hidden');
  });
}

async function fetchDropdown(q, dropdown, limit) {
  try {
    const r = await fetch('/api/search?q=' + encodeURIComponent(q));
    const d = await r.json();
    const people = (d.people || []).slice(0, limit);
    if (!people.length) { dropdown.classList.add('hidden'); return; }
    dropdown.innerHTML = renderDropdownItems(people);
    dropdown.classList.remove('hidden');
  } catch {
    dropdown.classList.add('hidden');
  }
}

document.addEventListener('DOMContentLoaded', () => {
  setupNavSearch();
  setupHeroSearch();
});
