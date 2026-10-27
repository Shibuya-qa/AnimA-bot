/**
 * SHODA ANIME & WEBTOON — TELEGRAM MINI APP LOGIC
 * Full interactive client matching the UI screenshots
 */

// STATE MANAGEMENT
const state = {
  tgUser: null,
  activeTab: 'home',
  mediaType: 'anime', // 'anime' | 'webtoon'
  catalogType: 'anime',
  catalogFormat: 'all', // 'all' | 'film' | 'serial'
  catalogGenre: 'all',
  catalogStatus: 'all',
  searchQuery: '',
  
  animes: [],
  reels: [],
  chatMessages: [],
  favorites: new Set(),
  userPoints: 0,
  
  currentHeroIndex: 0,
  currentReelIndex: 0,
  replyingTo: null
};

// TELEGRAM WEB APP SDK SETUP
function initTelegramApp() {
  const tg = window.Telegram?.WebApp;
  if (tg) {
    tg.ready();
    tg.expand();
    
    // Set theme header color
    try {
      tg.setHeaderColor('#0b0e14');
      tg.setBackgroundColor('#0b0e14');
    } catch (e) {
      console.warn("Theme colors could not be set:", e);
    }

    // Extract user info
    if (tg.initDataUnsafe && tg.initDataUnsafe.user) {
      const u = tg.initDataUnsafe.user;
      state.tgUser = {
        id: u.id,
        first_name: u.first_name || '',
        last_name: u.last_name || '',
        full_name: `${u.first_name || ''} ${u.last_name || ''}`.trim() || 'ShoDaShi',
        username: u.username ? `@${u.username}` : '@Shoxrux_Daminov',
        photo_url: u.photo_url || ''
      };
    }
  }

  // Fallback user if opened outside Telegram
  if (!state.tgUser) {
    state.tgUser = {
      id: 5199820118,
      full_name: 'ShoDaShi',
      username: '@Shoxrux_Daminov',
      photo_url: ''
    };
  }

  // Sync profile UI
  syncProfileUI();
}

function triggerHaptic(type = 'light') {
  if (window.Telegram?.WebApp?.HapticFeedback) {
    try {
      window.Telegram.WebApp.HapticFeedback.impactOccurred(type);
    } catch (e) {}
  }
}

// SYNC PROFILE DETAILS
function syncProfileUI() {
  const u = state.tgUser;
  if (!u) return;

  const initials = u.full_name.split(' ').map(n => n[0]).join('').substring(0, 2).toUpperCase() || 'SD';

  // Desktop sidebar profile
  const sidebarName = document.getElementById('sidebarUserName');
  const sidebarAvatar = document.getElementById('sidebarUserAvatar');
  if (sidebarName) sidebarName.textContent = u.full_name;
  if (sidebarAvatar) {
    if (u.photo_url) {
      sidebarAvatar.innerHTML = `<img src="${u.photo_url}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;" alt="Avatar">`;
    } else {
      sidebarAvatar.textContent = initials;
    }
  }

  const isAdmin = (u.id == 5199820118);

  const sidebarStatus = document.querySelector('.user-quick-status');
  if (sidebarStatus) {
    sidebarStatus.textContent = isAdmin ? '👑 Bosh Admin' : '💎 Oddiy a\'zo';
  }

  // Profile tab
  const profName = document.getElementById('profileFullName');
  const profUser = document.getElementById('profileUsername');
  const profId = document.getElementById('profileUserId');
  const profInitials = document.getElementById('profileInitials');
  const profAvatar = document.getElementById('profileAvatar');
  const profPoints = document.getElementById('profilePoints');

  if (profName) profName.textContent = u.full_name;
  if (profUser) profUser.textContent = u.username;
  if (profId) profId.textContent = u.id;
  if (profPoints) profPoints.textContent = isAdmin ? (state.userPoints || 999) : state.userPoints;

  // Plan badges in profile
  const planBadges = document.querySelector('.plan-badges');
  if (planBadges && isAdmin) {
    planBadges.innerHTML = '<span class="badge-pill lock" style="background:rgba(245,158,11,0.2);color:#f59e0b;border:1px solid rgba(245,158,11,0.4);">👑 ADMIN</span><span class="badge-pill gray" style="background:rgba(16,185,129,0.2);color:#10b981;border:1px solid rgba(16,185,129,0.4);">FAOL</span>';
  }

  if (profInitials && profAvatar) {
    if (u.photo_url) {
      profAvatar.innerHTML = `<img src="${u.photo_url}" style="width:100%;height:100%;border-radius:50%;object-fit:cover;" alt="Avatar">`;
    } else {
      profInitials.textContent = initials;
    }
  }
}

// DEFAULT SEED DATA (Top Mashhur Animelar)
const DEFAULT_ANIMES = [
  {
    id: 1,
    code: "1001",
    name: "Yolg'iz daraja ko'tarish (Solo Leveling)",
    status: "Davom etmoqda",
    genres: "Jangari, Fantastika, Sehr, Sarguzasht",
    rating: 5.0,
    views: 48900,
    translation: "O'zbekcha (AnimAfundub)",
    episodes: 12,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=700&auto=format&fit=crop&q=85",
    description: "Insoniyatning eng zaif ovchisi Son Jin-Vu halokatli ikki qavatli g'ordan so'ng sirli 'Tizim'ga ega bo'ladi va butun dunyoda yagona darajasi cheksiz o'suvchi Qora Soya Hukmdoriga aylanadi!"
  },
  {
    id: 2,
    code: "1002",
    name: "Titanlar Hujumi (Attack on Titan)",
    status: "Tugallangan",
    genres: "Jangari, Drama, Fantastika, Triller",
    rating: 5.0,
    views: 54200,
    translation: "O'zbekcha (AnimAfundub)",
    episodes: 89,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=700&auto=format&fit=crop&q=85",
    description: "Insoniyat bahaybat odamxo'r titanlardan saqlanish uchun uch qavatli ulkan devorlar ortida yashaydi. Eren Yeager onasini yo'qotgach, barcha titanlarni yo'q qilishga qasamyod qiladi."
  },
  {
    id: 3,
    code: "1003",
    name: "Sehrli Jang (Jujutsu Kaisen)",
    status: "Davom etmoqda",
    genres: "Jangari, Sehr, Dahshat, Shonen",
    rating: 4.9,
    views: 41200,
    translation: "O'zbekcha (AnimAfundub)",
    episodes: 47,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=700&auto=format&fit=crop&q=85",
    description: "Yuji Itadori la'natlangan barmoqni yutib, afsonaviy la'natlar shohi Sukunaning tirilishiga sabab bo'ladi va Gojo Satoru qo'l ostida sehrli jangga kirishadi."
  },
  {
    id: 4,
    code: "1004",
    name: "Iblislar Qotili (Demon Slayer: Kimetsu no Yaiba)",
    status: "Davom etmoqda",
    genres: "Jangari, Tarixiy, Sehr, Sarguzasht",
    rating: 4.9,
    views: 46800,
    translation: "O'zbekcha (AnimAfundub)",
    episodes: 55,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=700&auto=format&fit=crop&q=85",
    description: "Tanjiro Kamado oilasini qirib tashlagan iblislardan qasos olish va iblisga aylangan singlisi Nezukoni qayta insonga aylantirish uchun Iblislar Qotili safiga qo'shiladi."
  },
  {
    id: 5,
    code: "1005",
    name: "Naruto: Dovulli yillar (Naruto Shippuden)",
    status: "Tugallangan",
    genres: "Jangari, Sarguzasht, Shonen, Komediya",
    rating: 5.0,
    views: 62000,
    translation: "O'zbekcha",
    episodes: 500,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1563089145-599997674d42?w=700&auto=format&fit=crop&q=85",
    description: "Ichida to'qqiz dumli tulki muhrlangan yetim bola Naruto Uzumaki butun qishloqning hurmatiga sazovor bo'lish va eng buyuk Hokage bo'lish yo'lida mislsiz to'siqlarni yengib o'tadi."
  },
  {
    id: 6,
    code: "1006",
    name: "One Piece",
    status: "Davom etmoqda",
    genres: "Jangari, Sarguzasht, Komediya, Fantastika",
    rating: 5.0,
    views: 71000,
    translation: "O'zbekcha",
    episodes: 1100,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1542751371-adc38448a05e?w=700&auto=format&fit=crop&q=85",
    description: "Monkey D. Luffy va uning Straw Hat jamoasi afsonaviy xazina 'One Piece'ni topish va Qaroqchilar Qiroli bo'lish uchun Grand Line bo'ylab suzishadi."
  },
  {
    id: 7,
    code: "1007",
    name: "O'lim Daftari (Death Note)",
    status: "Tugallangan",
    genres: "Detektiv, Triller, Psixologik, Fantastika",
    rating: 5.0,
    views: 38400,
    translation: "O'zbekcha",
    episodes: 37,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1518709268805-4e9042af9f23?w=700&auto=format&fit=crop&q=85",
    description: "Aqlli talaba Light Yagami nom yozilgan odam o'ladigan O'lim Daftarchasini topib oladi va jinoyatchilarsiz yangi dunyo yaratish uchun o'zini yangi Xudo deb e'lon qiladi."
  },
  {
    id: 8,
    code: "1008",
    name: "Qora klever (Black Clover)",
    status: "Davom etmoqda",
    genres: "Jangari, Sarguzasht, Sehr, Fantastika",
    rating: 4.8,
    views: 29500,
    translation: "O'zbekcha (AnimAfundub)",
    episodes: 170,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=700&auto=format&fit=crop&q=85",
    description: "Asta sehr kuchi bo'lmagan holda 5 bargli qora klever anti-sehr grimoirini qo'lga kiritadi va Qora Buqalar jamoasi bilan birga Sehrgarlar Qiroli bo'lish sari intiladi!"
  },
  {
    id: 9,
    code: "1009",
    name: "Zanjirli arra odam (Chainsaw Man)",
    status: "Tugallangan",
    genres: "Ekshen, Dahshat, Qora komediya, Shonen",
    rating: 4.8,
    views: 23400,
    translation: "O'zbekcha",
    episodes: 12,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=700&auto=format&fit=crop&q=85",
    description: "Qashshoqlikda yashagan Denji o'zining iblis iti Pochita bilan birlashib, g'ayritabiiy Zanjirli arra odamga aylanadi va Iblislar xavfsizlik byurosiga olinadi."
  },
  {
    id: 10,
    code: "1010",
    name: "Bleach: Ming yillik qonli urush",
    status: "Davom etmoqda",
    genres: "Jangari, Sehr, Sarguzasht, Shonen",
    rating: 4.9,
    views: 31000,
    translation: "O'zbekcha",
    episodes: 26,
    type: "serial",
    is_vip: true,
    poster: "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=700&auto=format&fit=crop&q=85",
    description: "Ruhlar Jamiyati va Quincy imperatori Yhwach boshchiligidagi Wandenreich o'rtasida ming yillik qonli va shafqatsiz yakuniy urush boshlanadi."
  },
  {
    id: 11,
    code: "1011",
    name: "Tokio qasoskorlari (Tokyo Revengers)",
    status: "Tugallangan",
    genres: "Jangari, Fantastika, Maktab, Drama",
    rating: 4.7,
    views: 26500,
    translation: "O'zbekcha",
    episodes: 24,
    type: "serial",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1563089145-599997674d42?w=700&auto=format&fit=crop&q=85",
    description: "Takemichi Hanagaki o'tmishga 12 yil orqaga qaytib, sevgilisini qutqarish va Tokyo Manji to'dasining fojiali kelajagini o'zgartirish uchun kurashadi."
  },
  {
    id: 12,
    code: "1012",
    name: "Suzume eshiklarni yopmoqda (Suzume no Tojimari)",
    status: "Tugallangan",
    genres: "Fantastika, Drama, Sarguzasht",
    rating: 4.9,
    views: 22100,
    translation: "O'zbekcha",
    episodes: 1,
    type: "film",
    is_vip: false,
    poster: "https://images.unsplash.com/photo-1509198397868-475647b2a1e5?w=700&auto=format&fit=crop&q=85",
    description: "Makoto Shinkayning dunyoga mashhur shedevri. Yaponiya bo'ylab tabiiy ofatlar olib kelayotgan sehrli eshiklarni yopish uchun Suzumening hayratlanarli sayohati."
  }
];

const DEFAULT_REELS = [
  {
    id: 1,
    title: "Erimni qanday qilib o'z tomonimga og'dirsam bo'ladi",
    creator: "Nagasera Webtoon",
    verified: true,
    tags: "Romantika. Isekai. Drama. Fantastika. Siyosiy Intriga",
    likes: 128,
    comments: 14,
    views: 2420,
    is_liked: false,
    is_following: true,
    cta_text: "O'QISH",
    media_url: "https://images.unsplash.com/photo-1607604276583-eef5d076aa5f?w=800&auto=format&fit=crop&q=80"
  },
  {
    id: 2,
    title: "Solo Leveling — Qora Soya Hukmdori uyg'onishi",
    creator: "Daminov Anime",
    verified: true,
    tags: "Jangari. Manhwa. Sehr. Qaytish",
    likes: 542,
    comments: 48,
    views: 9810,
    is_liked: true,
    is_following: false,
    cta_text: "TOMOSHA QILISH",
    media_url: "https://images.unsplash.com/photo-1578632767115-351597cf2477?w=800&auto=format&fit=crop&q=80"
  },
  {
    id: 3,
    title: "Sehrgarlar Qirolligi va Asta ning so'nggi jangi",
    creator: "AnimAfundub TV",
    verified: true,
    tags: "Anime. Shonen. Ekshen. Grimoire",
    likes: 890,
    comments: 92,
    views: 15400,
    is_liked: false,
    is_following: true,
    cta_text: "TOMOSHA QILISH",
    media_url: "https://images.unsplash.com/photo-1534447677768-be436bb09401?w=800&auto=format&fit=crop&q=80"
  }
];

// DATA FETCHING & API INTEGRATION
async function loadData() {
  try {
    const res = await fetch('/api/animes');
    if (res.ok) {
      const data = await res.json();
      if (Array.isArray(data) && data.length > 0) {
        state.animes = data;
      } else {
        state.animes = DEFAULT_ANIMES;
      }
    } else {
      state.animes = DEFAULT_ANIMES;
    }
  } catch (err) {
    console.warn("API serveriga ulanmadi, lokal namunaviy ma'lumotlar yuklandi:", err);
    state.animes = DEFAULT_ANIMES;
  }

  // Load reels
  state.reels = DEFAULT_REELS;

  // Load saved favorites from localStorage
  try {
    const savedFavs = localStorage.getItem('shoda_favorites');
    if (savedFavs) {
      const arr = JSON.parse(savedFavs);
      state.favorites = new Set(arr);
    }
    const savedPoints = localStorage.getItem('shoda_points');
    if (savedPoints) {
      state.userPoints = parseInt(savedPoints, 10) || 0;
    }
  } catch (e) {}

  // Sync User data with Bot Database
  if (state.tgUser?.id) {
    try {
      const uRes = await fetch(`/api/user/${state.tgUser.id}`);
      if (uRes.ok) {
        const uData = await uRes.json();
        if (Array.isArray(uData.favorites)) {
          state.favorites = new Set(uData.favorites);
        }
        if (uData.points !== undefined) {
          state.userPoints = uData.points;
        }
        if (Array.isArray(uData.history) && uData.history.length > 0) {
          renderHistoryList(uData.history);
        }
        syncProfileUI();
      }
    } catch (e) {
      console.warn("User profile sync failed:", e);
    }
  }

  // Render initial components
  renderHeroBanner();
  renderHomeCards();
  renderCatalog();
  renderFavorites();
  renderCurrentReel();
}

function renderHistoryList(history) {
  const card = document.getElementById('historyCard');
  if (!card) return;
  if (!history || history.length === 0) {
    card.innerHTML = '<span class="history-text">Hali tarix bo\'sh.</span>';
    return;
  }
  card.innerHTML = `
    <div style="display:flex;flex-direction:column;gap:8px;text-align:left;">
      ${history.map(item => `
        <div style="display:flex;align-items:center;justify-content:space-between;padding:8px 12px;background:rgba(255,255,255,0.04);border-radius:10px;cursor:pointer;" onclick="openAnimeDetail(${item.id})">
          <div>
            <div style="font-weight:700;font-size:13.5px;color:#fff;">${escapeHtml(item.name)}</div>
            <div style="font-size:11px;color:#94a3b8;">${escapeHtml(item.genres || '')} • Kod: #${item.code}</div>
          </div>
          <span style="font-size:11px;color:#38bdf8;font-weight:600;">Tomosha qilingan ›</span>
        </div>
      `).join('')}
    </div>
  `;
}

// NAVIGATION / TAB SWITCHING
function switchTab(tabId) {
  triggerHaptic('light');
  state.activeTab = tabId;

  // Update Sidebar buttons
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });

  // Update Mobile nav buttons
  document.querySelectorAll('.mobile-bottom-nav .mob-nav-item').forEach(btn => {
    btn.classList.toggle('active', btn.dataset.tab === tabId);
  });

  // Update Tab Panes
  document.querySelectorAll('.tab-pane').forEach(pane => {
    pane.classList.remove('active');
  });
  const targetPane = document.getElementById(`tab-${tabId}`);
  if (targetPane) {
    targetPane.classList.add('active');
  }

  // Scroll to top
  const viewport = document.querySelector('.content-viewport');
  if (viewport) viewport.scrollTop = 0;

  // Re-render favorites if active
  if (tabId === 'favorites') {
    renderFavorites();
  }
}

// 1. HOME TAB: HERO BANNER
function renderHeroBanner() {
  const current = state.animes[state.currentHeroIndex] || state.animes[0];
  if (!current) return;

  const heroGenre = document.getElementById('heroGenre');
  const heroTitle = document.getElementById('heroTitle');
  const heroDesc = document.getElementById('heroDesc');
  const heroPosterImg = document.getElementById('heroPosterImg');
  const heroPosterTag = document.getElementById('heroPosterTag');
  const heroFavBtn = document.getElementById('heroFavBtn');
  const heroBackdrop = document.getElementById('heroBackdrop');

  if (heroGenre) heroGenre.textContent = current.genres || 'Jangari • Sarguzasht';
  if (heroTitle) heroTitle.textContent = current.name;
  if (heroDesc) heroDesc.textContent = current.description;
  if (heroPosterImg) heroPosterImg.src = current.poster || DEFAULT_ANIMES[0].poster;
  if (heroPosterTag) heroPosterTag.textContent = current.name.toUpperCase();
  if (heroBackdrop && current.poster) {
    heroBackdrop.style.backgroundImage = `url('${current.poster}')`;
  }

  const isFav = state.favorites.has(current.id);
  if (heroFavBtn) {
    heroFavBtn.innerHTML = isFav ? '❤️' : '+';
    heroFavBtn.style.color = isFav ? '#ef4444' : '#ffffff';
  }

  // Update dots
  const dotsContainer = document.getElementById('heroDots');
  if (dotsContainer) {
    dotsContainer.innerHTML = '';
    const totalDots = Math.min(state.animes.length, 5);
    for (let i = 0; i < totalDots; i++) {
      const dot = document.createElement('span');
      dot.className = `dot ${i === state.currentHeroIndex ? 'active' : ''}`;
      dot.onclick = () => {
        state.currentHeroIndex = i;
        renderHeroBanner();
      };
      dotsContainer.appendChild(dot);
    }
  }
}

function nextHero() {
  state.currentHeroIndex = (state.currentHeroIndex + 1) % Math.min(state.animes.length, 5);
  renderHeroBanner();
}

function prevHero() {
  state.currentHeroIndex = (state.currentHeroIndex - 1 + Math.min(state.animes.length, 5)) % Math.min(state.animes.length, 5);
  renderHeroBanner();
}

// 1. HOME TAB: SECTIONS
function renderHomeCards() {
  const recentGrid = document.getElementById('recentCardsGrid');
  const topGrid = document.getElementById('topCardsGrid');

  if (recentGrid) {
    recentGrid.innerHTML = state.animes.slice(0, 4).map(anime => createAnimeCardHtml(anime)).join('');
  }
  if (topGrid) {
    // Sort by rating or views
    const sorted = [...state.animes].sort((a, b) => (b.views || 0) - (a.views || 0));
    topGrid.innerHTML = sorted.slice(0, 4).map(anime => createAnimeCardHtml(anime)).join('');
  }
}

// CARD HTML BUILDER
function createAnimeCardHtml(anime) {
  const isFav = state.favorites.has(anime.id);
  const badgeClass = anime.is_vip ? 'vip' : 'bepul';
  const badgeText = anime.is_vip ? 'VIP' : 'Bepul';
  const rating = (anime.rating || 5.0).toFixed(1);

  return `
    <div class="anime-card" onclick="openAnimeDetail(${anime.id})">
      <div class="anime-card-media">
        <span class="badge-tag ${badgeClass}">${badgeText}</span>
        <button class="card-fav-btn ${isFav ? 'active' : ''}" onclick="toggleFavorite(event, ${anime.id})">
          ${isFav ? '❤️' : '🤍'}
        </button>
        <img src="${anime.poster || DEFAULT_ANIMES[0].poster}" alt="${anime.name}" class="anime-card-img" loading="lazy">
      </div>
      <div class="anime-card-info">
        <h4 class="anime-card-title">${anime.name}</h4>
        <p class="anime-card-genre">${anime.genres || 'Anime'}</p>
        <div class="anime-card-meta">
          <span class="card-rating">⭐ ${rating}</span>
          <span class="card-views">👁 ${anime.views || 0}</span>
        </div>
      </div>
    </div>
  `;
}

// 2. KATALOG (CATALOG) FILTERING & RENDERING
function renderCatalog() {
  const grid = document.getElementById('catalogCardsGrid');
  const empty = document.getElementById('catalogEmptyState');
  const countEl = document.getElementById('catalogResultsCount');
  if (!grid) return;

  const query = state.searchQuery.toLowerCase().trim();

  const filtered = state.animes.filter(a => {
    // Query search
    if (query) {
      const matchName = a.name.toLowerCase().includes(query);
      const matchGenre = (a.genres || '').toLowerCase().includes(query);
      const matchCode = (a.code || '').toLowerCase().includes(query);
      if (!matchName && !matchGenre && !matchCode) return false;
    }

    // Format filter: all | film | serial
    if (state.catalogFormat !== 'all') {
      if (a.type && a.type !== state.catalogFormat) return false;
    }

    // Genre filter
    if (state.catalogGenre !== 'all') {
      if (!(a.genres || '').includes(state.catalogGenre)) return false;
    }

    // Status / Access filter
    if (state.catalogStatus !== 'all') {
      if (state.catalogStatus === 'VIP' && !a.is_vip) return false;
      if (state.catalogStatus === 'Bepul' && a.is_vip) return false;
      if (state.catalogStatus === 'Davom etmoqda' && a.status !== 'Davom etmoqda') return false;
      if (state.catalogStatus === 'Tugallangan' && a.status !== 'Tugallangan') return false;
    }

    return true;
  });

  if (countEl) countEl.textContent = `${filtered.length} ta anime`;

  if (filtered.length === 0) {
    grid.innerHTML = '';
    if (empty) empty.style.display = 'block';
  } else {
    if (empty) empty.style.display = 'none';
    grid.innerHTML = filtered.map(a => createAnimeCardHtml(a)).join('');
  }
}

// 3. LENTA (REELS / SHORTS)
function renderCurrentReel() {
  const reel = state.reels[state.currentReelIndex];
  if (!reel) return;

  const mediaImg = document.getElementById('reelMediaImg');
  const title = document.getElementById('reelTitle');
  const tags = document.getElementById('reelTagsSub');
  const creator = document.getElementById('reelCreatorName');
  const likeBtn = document.getElementById('reelLikeBtn');
  const likeCount = document.getElementById('reelLikeCount');
  const commentCount = document.getElementById('reelCommentCount');
  const viewCount = document.getElementById('reelViewCount');
  const followBtn = document.getElementById('reelFollowBtn');
  const ctaText = document.getElementById('reelCtaText');

  if (mediaImg) mediaImg.src = reel.media_url;
  if (title) title.textContent = reel.title;
  if (tags) tags.textContent = reel.tags;
  if (creator) creator.textContent = reel.creator;
  if (likeCount) likeCount.textContent = reel.likes;
  if (commentCount) commentCount.textContent = reel.comments;
  if (viewCount) viewCount.textContent = reel.views;
  if (ctaText) ctaText.textContent = reel.cta_text || "O'QISH";

  if (likeBtn) {
    likeBtn.classList.toggle('liked', reel.is_liked);
    likeBtn.querySelector('.heart-icon').textContent = reel.is_liked ? '❤️' : '🤍';
  }

  if (followBtn) {
    followBtn.textContent = reel.is_following ? '✓ Obunadasiz' : '+ Obuna bo\'lish';
  }
}

function nextReel() {
  triggerHaptic('medium');
  state.currentReelIndex = (state.currentReelIndex + 1) % state.reels.length;
  renderCurrentReel();
}

function prevReel() {
  triggerHaptic('medium');
  state.currentReelIndex = (state.currentReelIndex - 1 + state.reels.length) % state.reels.length;
  renderCurrentReel();
}

// 4. CHAT FUNCTIONS
function prepareReply(user, snippet) {
  triggerHaptic('light');
  state.replyingTo = { user, snippet };
  const bar = document.getElementById('replyPreviewBar');
  const uEl = document.getElementById('replyToUser');
  const sEl = document.getElementById('replyToSnippet');
  if (bar && uEl && sEl) {
    uEl.textContent = user;
    sEl.textContent = snippet.length > 30 ? snippet.substring(0, 30) + '...' : snippet;
    bar.style.display = 'flex';
  }
  const input = document.getElementById('chatMessageInput');
  if (input) input.focus();
}

function cancelReply() {
  state.replyingTo = null;
  const bar = document.getElementById('replyPreviewBar');
  if (bar) bar.style.display = 'none';
}

function handleSendMessage(e) {
  e.preventDefault();
  const input = document.getElementById('chatMessageInput');
  const text = (input ? input.value : '').trim();
  if (!text) return;

  triggerHaptic('medium');
  const now = new Date();
  const timeStr = now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });

  const container = document.getElementById('chatMessagesContainer');
  if (container) {
    const initials = (state.tgUser?.full_name || 'U').substring(0, 2).toUpperCase();
    const replySnippet = state.replyingTo 
      ? `<div style="font-size:11px;color:#38bdf8;margin-bottom:3px;border-left:2px solid #38bdf8;padding-left:6px;">↪ ${state.replyingTo.user}: ${state.replyingTo.snippet}</div>` 
      : '';

    const newMsgHtml = `
      <div class="chat-message-item" style="animation: fadeIn 0.2s ease;">
        <div class="msg-avatar user">${initials}</div>
        <div class="msg-body">
          <div class="msg-top">
            <span class="msg-author">${state.tgUser?.full_name || 'Foydalanuvchi'}</span>
            <span class="msg-time">${timeStr}</span>
          </div>
          <div class="msg-bubble">
            ${replySnippet}
            <p class="msg-text">${escapeHtml(text)}</p>
          </div>
          <div class="msg-actions">
            <button class="reply-btn" onclick="prepareReply('${state.tgUser?.full_name}', '${escapeHtml(text)}')">↩ Javob berish</button>
            <div class="msg-reactions">
              <button class="react-btn">❤️</button>
            </div>
          </div>
        </div>
      </div>
    `;

    container.insertAdjacentHTML('beforeend', newMsgHtml);
    container.scrollTop = container.scrollHeight;
  }

  // Clear input & reply
  if (input) input.value = '';
  cancelReply();

  // Try posting to API
  try {
    fetch('/api/chat', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        user_id: state.tgUser?.id,
        user_name: state.tgUser?.full_name,
        message: text
      })
    }).catch(() => {});
  } catch (err) {}
}

// 5. FAVORITES MANAGEMENT
function toggleFavorite(event, animeId) {
  if (event) event.stopPropagation();
  triggerHaptic('light');

  const id = parseInt(animeId, 10);
  if (state.favorites.has(id)) {
    state.favorites.delete(id);
    showToast("Sevimlilardan olib tashlandi");
  } else {
    state.favorites.add(id);
    showToast("❤️ Sevimlilarga qo'shildi!");
  }

  // Persist locally
  try {
    localStorage.setItem('shoda_favorites', JSON.stringify([...state.favorites]));
  } catch (e) {}

  // Sync with Bot Database (favorites table)
  if (state.tgUser?.id) {
    fetch(`/api/user/${state.tgUser.id}/favorites`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anime_id: id })
    }).then(res => res.json()).then(data => {
      if (Array.isArray(data.favorites)) {
        state.favorites = new Set(data.favorites);
      }
    }).catch(e => console.warn("Favorite sync failed:", e));
  }

  // Update UI
  renderHomeCards();
  renderCatalog();
  renderHeroBanner();
  renderFavorites();
}

function renderFavorites() {
  const grid = document.getElementById('favoritesGrid');
  const empty = document.getElementById('favoritesEmptyState');
  const countEl = document.getElementById('favCountText');
  if (!grid) return;

  const favAnimes = state.animes.filter(a => state.favorites.has(a.id));
  if (countEl) countEl.textContent = `${favAnimes.length} ta saqlangan`;

  if (favAnimes.length === 0) {
    grid.innerHTML = '';
    if (empty) empty.style.display = 'block';
  } else {
    if (empty) empty.style.display = 'none';
    grid.innerHTML = favAnimes.map(a => createAnimeCardHtml(a)).join('');
  }
}

// ANIME DETAIL MODAL
function openAnimeDetail(animeId) {
  triggerHaptic('medium');
  const anime = state.animes.find(a => a.id === animeId);
  if (!anime) return;

  const modal = document.getElementById('animeDetailModal');
  const cover = document.getElementById('modalAnimeCover');
  const title = document.getElementById('modalAnimeTitle');
  const genres = document.getElementById('modalAnimeGenres');
  const status = document.getElementById('modalAnimeStatus');
  const rating = document.getElementById('modalAnimeRating');
  const code = document.getElementById('modalAnimeCode');
  const translation = document.getElementById('modalAnimeTranslation');
  const epCount = document.getElementById('modalAnimeEpisodesCount');
  const views = document.getElementById('modalAnimeViews');
  const desc = document.getElementById('modalAnimeDesc');
  const epGrid = document.getElementById('modalEpisodesGrid');
  const favBtn = document.getElementById('modalToggleFavBtn');
  const watchFirst = document.getElementById('modalWatchFirstBtn');

  if (cover) cover.src = anime.poster || DEFAULT_ANIMES[0].poster;
  if (title) title.textContent = anime.name;
  if (genres) genres.textContent = anime.genres || '';
  if (status) status.textContent = anime.status || 'Tugallangan';
  if (rating) rating.textContent = `⭐ ${(anime.rating || 5.0).toFixed(1)}`;
  if (code) code.textContent = `#${anime.code || anime.id}`;
  if (translation) translation.textContent = anime.translation || "O'zbekcha";
  if (epCount) epCount.textContent = `${anime.episodes || 1} qism`;
  if (views) views.textContent = anime.views || 0;
  if (desc) desc.textContent = anime.description || "Ushbu anime haqida ma'lumot tez orada joylanadi.";

  // Populate episode buttons (1..12 or actual count)
  if (epGrid) {
    epGrid.innerHTML = '';
    const totalEp = Math.max(1, anime.episodes || 12);
    for (let i = 1; i <= Math.min(totalEp, 24); i++) {
      const b = document.createElement('button');
      b.className = 'ep-btn';
      b.textContent = `${i}-qism`;
      b.onclick = () => playEpisode(anime, i);
      epGrid.appendChild(b);
    }
  }

  // Favorite button
  const isFav = state.favorites.has(anime.id);
  if (favBtn) {
    favBtn.textContent = isFav ? "💔 Sevimlilardan o'chirish" : "❤️ Sevimlilarga qo'shish";
    favBtn.onclick = () => {
      toggleFavorite(null, anime.id);
      openAnimeDetail(anime.id);
    };
  }

  if (watchFirst) {
    watchFirst.onclick = () => playEpisode(anime, 1);
  }

  if (modal) modal.style.display = 'flex';
}

function playEpisode(anime, epNum) {
  triggerHaptic('heavy');
  showToast(`🎬 "${anime.name}" ${epNum}-qismi botda ochilmoqda...`);

  // Sync watch history and view counter in bot database
  if (state.tgUser?.id && anime.id) {
    fetch(`/api/user/${state.tgUser.id}/history`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ anime_id: anime.id })
    }).catch(() => {});
  }

  // Deep-link to Telegram Bot (@animafundubbot) to receive protected episode
  const botUsername = "animafundubbot";
  const startArg = anime.code || anime.id;
  const botUrl = `https://t.me/${botUsername}?start=${startArg}`;

  if (window.Telegram?.WebApp) {
    const tg = window.Telegram.WebApp;
    try {
      tg.openTelegramLink(botUrl);
      setTimeout(() => {
        try { tg.close(); } catch (e) {}
      }, 400);
      return;
    } catch (e) {}
  }

  // Fallback if opened in standard browser
  window.open(botUrl, '_blank');
}

function closeModal(modalId) {
  const m = document.getElementById(modalId);
  if (m) m.style.display = 'none';
}

// TOAST HELPER
let toastTimeout;
function showToast(message) {
  const box = document.getElementById('toastBox');
  const msg = document.getElementById('toastMsg');
  if (!box || !msg) return;

  msg.textContent = message;
  box.classList.add('show');

  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => {
    box.classList.remove('show');
  }, 2400);
}

function escapeHtml(text) {
  const map = { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#039;' };
  return text.replace(/[&<>"']/g, m => map[m]);
}

// EVENT LISTENERS & INITIALIZATION
document.addEventListener('DOMContentLoaded', () => {
  initTelegramApp();
  loadData();

  // Navigation tab clicks (Sidebar)
  document.querySelectorAll('.sidebar-nav .nav-item').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Navigation tab clicks (Mobile bottom nav)
  document.querySelectorAll('.mobile-bottom-nav .mob-nav-item').forEach(btn => {
    btn.addEventListener('click', () => switchTab(btn.dataset.tab));
  });

  // Quick profile click in sidebar
  const sidebarProf = document.getElementById('sidebarUserProfileBtn');
  if (sidebarProf) {
    sidebarProf.addEventListener('click', () => switchTab('profile'));
  }

  // Media Type Switcher (ANIME / WEBTOON)
  document.querySelectorAll('.type-switch-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      triggerHaptic('light');
      const type = btn.dataset.type || btn.dataset.catType;
      document.querySelectorAll('.type-switch-btn').forEach(b => {
        if (b.dataset.type === type || b.dataset.catType === type) {
          b.classList.add('active');
        } else {
          b.classList.remove('active');
        }
      });
      state.mediaType = type;
      showToast(`${type.toUpperCase()} bo'limi tanlandi`);
    });
  });

  // Hero controls
  const heroNext = document.getElementById('heroNextBtn');
  const heroPrev = document.getElementById('heroPrevBtn');
  const heroWatch = document.getElementById('heroWatchBtn');
  const heroFav = document.getElementById('heroFavBtn');

  if (heroNext) heroNext.addEventListener('click', nextHero);
  if (heroPrev) heroPrev.addEventListener('click', prevHero);
  if (heroWatch) heroWatch.addEventListener('click', () => {
    const cur = state.animes[state.currentHeroIndex];
    if (cur) openAnimeDetail(cur.id);
  });
  if (heroFav) heroFav.addEventListener('click', () => {
    const cur = state.animes[state.currentHeroIndex];
    if (cur) toggleFavorite(null, cur.id);
  });

  // Search Inputs (Top header & Catalog)
  const globalSearch = document.getElementById('globalSearchInput');
  const catSearch = document.getElementById('catalogSearchInput');
  const clearBtn = document.getElementById('clearSearchBtn');

  function handleSearch(val) {
    state.searchQuery = val;
    if (globalSearch && globalSearch.value !== val) globalSearch.value = val;
    if (catSearch && catSearch.value !== val) catSearch.value = val;
    if (clearBtn) clearBtn.style.display = val ? 'block' : 'none';

    if (state.activeTab !== 'catalog' && val) {
      switchTab('catalog');
    }
    renderCatalog();
  }

  if (globalSearch) {
    globalSearch.addEventListener('input', e => handleSearch(e.target.value));
  }
  if (catSearch) {
    catSearch.addEventListener('input', e => handleSearch(e.target.value));
  }
  if (clearBtn) {
    clearBtn.addEventListener('click', () => handleSearch(''));
  }

  // Catalog Format Pills (Hammasi / Filmlar / Seriallar)
  document.querySelectorAll('.format-pills .pill-btn').forEach(btn => {
    btn.addEventListener('click', () => {
      triggerHaptic('light');
      document.querySelectorAll('.format-pills .pill-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.catalogFormat = btn.dataset.format;
      renderCatalog();
    });
  });

  // Catalog Genre Pills
  document.querySelectorAll('.genre-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      triggerHaptic('light');
      document.querySelectorAll('.genre-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.catalogGenre = btn.dataset.genre;
      renderCatalog();
    });
  });

  // Catalog Status Pills
  document.querySelectorAll('.status-pill').forEach(btn => {
    btn.addEventListener('click', () => {
      triggerHaptic('light');
      document.querySelectorAll('.status-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      state.catalogStatus = btn.dataset.status;
      renderCatalog();
    });
  });

  // Reset Filters
  const resetBtn = document.getElementById('resetFiltersBtn');
  if (resetBtn) {
    resetBtn.addEventListener('click', () => {
      handleSearch('');
      state.catalogFormat = 'all';
      state.catalogGenre = 'all';
      state.catalogStatus = 'all';
      document.querySelectorAll('.genre-pill, .status-pill, .format-pills .pill-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.genre === 'all' || b.dataset.status === 'all' || b.dataset.format === 'all');
      });
      renderCatalog();
    });
  }

  // See all buttons in home
  document.querySelectorAll('.see-all-btn').forEach(b => {
    b.addEventListener('click', () => switchTab('catalog'));
  });

  // Reels Controls
  const reelLike = document.getElementById('reelLikeBtn');
  const reelFollow = document.getElementById('reelFollowBtn');
  const reelShare = document.getElementById('reelShareBtn');
  const reelRead = document.getElementById('reelReadBtn');
  const reelNextBtn = document.getElementById('reelNextBtn');
  const reelPrevBtn = document.getElementById('reelPrevBtn');

  if (reelLike) {
    reelLike.addEventListener('click', () => {
      triggerHaptic('medium');
      const r = state.reels[state.currentReelIndex];
      if (r) {
        r.is_liked = !r.is_liked;
        r.likes += r.is_liked ? 1 : -1;
        renderCurrentReel();
      }
    });
  }

  if (reelFollow) {
    reelFollow.addEventListener('click', () => {
      triggerHaptic('light');
      const r = state.reels[state.currentReelIndex];
      if (r) {
        r.is_following = !r.is_following;
        showToast(r.is_following ? "Obuna bo'lindi!" : "Obuna bekor qilindi");
        renderCurrentReel();
      }
    });
  }

  if (reelShare) {
    reelShare.addEventListener('click', () => {
      triggerHaptic('light');
      if (navigator.clipboard) {
        navigator.clipboard.writeText(window.location.href);
        showToast("Havola nusxalandi!");
      } else {
        showToast("Ulashish muvaffaqiyatli!");
      }
    });
  }

  if (reelRead) {
    reelRead.addEventListener('click', () => {
      triggerHaptic('heavy');
      showToast("Webtoon ochilmoqda...");
    });
  }

  if (reelNextBtn) reelNextBtn.addEventListener('click', nextReel);
  if (reelPrevBtn) reelPrevBtn.addEventListener('click', prevReel);

  // Chat Form & Actions
  const chatForm = document.getElementById('chatForm');
  if (chatForm) chatForm.addEventListener('submit', handleSendMessage);
  const cancelReplyBtn = document.getElementById('cancelReplyBtn');
  if (cancelReplyBtn) cancelReplyBtn.addEventListener('click', cancelReply);

  // Copy User ID in Profile
  const copyId = document.getElementById('copyIdBtn');
  if (copyId) {
    copyId.addEventListener('click', () => {
      triggerHaptic('light');
      if (state.tgUser?.id) {
        navigator.clipboard?.writeText(state.tgUser.id.toString());
        showToast(`ID nusxalandi: ${state.tgUser.id}`);
      }
    });
  }

  // Profile action modals
  const promoMenu = document.getElementById('menuPromoCode');
  if (promoMenu) {
    promoMenu.addEventListener('click', () => {
      document.getElementById('promoModal').style.display = 'flex';
    });
  }

  const reqMenu = document.getElementById('menuRequestFilm');
  if (reqMenu) {
    reqMenu.addEventListener('click', () => {
      document.getElementById('filmRequestModal').style.display = 'flex';
    });
  }

  const verifyCard = document.getElementById('verifyAccountCard');
  if (verifyCard) {
    verifyCard.addEventListener('click', () => {
      document.getElementById('verifyModal').style.display = 'flex';
    });
  }

  const premiumBtn = document.getElementById('getPremiumBtn');
  const premiumMenu = document.getElementById('menuPremiumSub');
  const openPremium = () => {
    showToast("👑 Premium obuna: Bot orqali to'lov tizimiga yo'naltirilmoqda...");
  };
  if (premiumBtn) premiumBtn.addEventListener('click', openPremium);
  if (premiumMenu) premiumMenu.addEventListener('click', openPremium);

  const supportMenu = document.getElementById('menuSupport');
  if (supportMenu) {
    supportMenu.addEventListener('click', () => {
      showToast("🎧 Qo'llab-quvvatlash xizmati @admin ga yo'naltirilmoqda");
    });
  }

  const logoutBtn = document.getElementById('logoutBtn');
  if (logoutBtn) {
    logoutBtn.addEventListener('click', () => {
      triggerHaptic('medium');
      showToast("Hisobdan chiqildi.");
      if (window.Telegram?.WebApp) {
        window.Telegram.WebApp.close();
      }
    });
  }

  // Promo code submit
  const submitPromo = document.getElementById('submitPromoBtn');
  if (submitPromo) {
    submitPromo.addEventListener('click', () => {
      const code = (document.getElementById('promoCodeInput')?.value || '').trim();
      if (!code) {
        showToast("Promo-kodni kiriting!");
        return;
      }
      triggerHaptic('heavy');
      state.userPoints += 50;
      localStorage.setItem('shoda_points', state.userPoints.toString());
      syncProfileUI();
      closeModal('promoModal');
      showToast(`Tabriklaymiz! +50 ball berildi. Jami: ${state.userPoints} ball`);
    });
  }

  // Film request submit
  const submitReq = document.getElementById('submitFilmRequestBtn');
  if (submitReq) {
    submitReq.addEventListener('click', () => {
      const film = (document.getElementById('filmRequestInput')?.value || '').trim();
      if (!film) {
        showToast("Film nomini kiriting!");
        return;
      }
      triggerHaptic('medium');
      closeModal('filmRequestModal');
      showToast("Arizangiz qabul qilindi! Tez orada ko'rib chiqiladi.");
    });
  }

  // Verification submit
  const submitVer = document.getElementById('submitVerifyBtn');
  if (submitVer) {
    submitVer.addEventListener('click', () => {
      triggerHaptic('medium');
      closeModal('verifyModal');
      showToast("Arizangiz adminlarga yuborildi!");
    });
  }

  // Detail Modal Close
  const closeDetail = document.getElementById('closeDetailModalBtn');
  if (closeDetail) {
    closeDetail.addEventListener('click', () => closeModal('animeDetailModal'));
  }

  // Close modals when clicking backdrop
  document.querySelectorAll('.modal-backdrop').forEach(modal => {
    modal.addEventListener('click', e => {
      if (e.target === modal) modal.style.display = 'none';
    });
  });
});
