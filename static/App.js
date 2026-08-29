const API_URL = 'http://127.0.0.1:8000';
let currentChannelId = null;
const state = {
    loading: false,
    result: null,
    progress: 0,
    currentStep: 0,
    videoFile: null,
    mode: "long",
    channels: [],
    isCreatingChannel: false,
    editingChannel: null,
    proMode: false,
    currentUser: null,
    currentView: 'dashboard',
    dashboardData: null,
    groqKey: '',
    geminiKey: '',
    lang: localStorage.getItem('ytlang') || 'tr'
};


// ═══════════════════════════════════════════════════════════
// SECURITY & MEMORY MANAGEMENT
// ═══════════════════════════════════════════════════════════
function escapeHTML(str) {
    if (str === null || str === undefined) return '';
    return String(str)
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

let _cachedVideoObjectURL = null;

function getVideoObjectURL() {
    if (!state.videoFile) {
        revokeVideoObjectURL();
        return null;
    }
    if (!_cachedVideoObjectURL) {
        _cachedVideoObjectURL = URL.createObjectURL(state.videoFile);
    }
    return _cachedVideoObjectURL;
}

function revokeVideoObjectURL() {
    if (_cachedVideoObjectURL) {
        URL.revokeObjectURL(_cachedVideoObjectURL);
        _cachedVideoObjectURL = null;
    }
}


let LANGS = { tr: {}, en: {}, es: {} };

const INLINE_LANGS = {
    tr: {
        emailVerify: "Email Doğrulama",
        codeSent: "adresine 6 haneli kod gönderdik.",
        sixDigit: "6 haneli kod",
        verify: "✅ Doğrula",
        resendBtn: "📨 Kodu Tekrar Gönder",
        checkSpam: "Kodu göremediysen spam klasörüne bak.",
        codeIncomplete: "6 haneli kodu eksiksiz gir.",
        wait: "⏳ Bekleyin...",
        sending: "⏳ Gönderiliyor...",
        codeSentMsg: "Yeni kod e-posta adresinize gönderildi!",
        connErr: "Bağlantı hatası!",
        reportSent: "Raporunuz e-posta adresinize gönderildi.",
        reportResend: "Raporu Tekrar Gönder",
        reportResending: "Gönderiliyor...",
        sysProfile: "Sistem Profili",
    },
    en: {
        emailVerify: "Email Verification",
        codeSent: "we sent a 6-digit code.",
        sixDigit: "6-digit code",
        verify: "✅ Verify",
        resendBtn: "📨 Resend Code",
        checkSpam: "Check spam if you don't see the code.",
        codeIncomplete: "Enter the full 6-digit code.",
        wait: "⏳ Wait...",
        sending: "⏳ Sending...",
        codeSentMsg: "New code sent to your email!",
        connErr: "Connection error!",
        reportSent: "Report has been sent to your email.",
        reportResend: "Resend Report",
        reportResending: "Sending...",
        sysProfile: "System Profile",
    },
    es: {
        emailVerify: "Verificación de Correo",
        codeSent: "enviamos un código de 6 dígitos.",
        sixDigit: "Código de 6 dígitos",
        verify: "✅ Verificar",
        resendBtn: "📨 Reenviar Código",
        checkSpam: "Revisa spam si no ves el código.",
        codeIncomplete: "Ingresa el código completo de 6 dígitos.",
        wait: "⏳ Espera...",
        sending: "⏳ Enviando...",
        codeSentMsg: "¡Nuevo código enviado a tu correo!",
        connErr: "¡Error de conexión!",
        reportSent: "El informe ha sido enviado a su correo electrónico.",
        reportResend: "Reenviar Informe",
        reportResending: "Enviando...",
        sysProfile: "Perfil del Sistema",
    }
};

async function loadTranslations() {
    try {
        const res = await fetch(`${API_URL}/api/translations`);
        const data = await res.json();
        if (data.error) {
            // Backend could not find or read the file — to prevent raw keys from being visible
            // existing LANGS remain empty; The problem appears in detail on the console.
            console.error(
                '[loadTranslations] ❌ Backend çeviri hatası döndürdü:',
                data.error,
                '\nÇözüm: translations.xlsx dosyasını proje kök dizinine koyun ve sunucuyu yeniden başlatın.'
            );
            return; // Leave LANGS blank (t() falls back to fallback)
        }
        if (data.tr) {
            LANGS = data;
        } else {
            console.error('[loadTranslations] ❌ Backend beklenmeyen format döndürdü:', data);
        }
    } catch (e) {
        console.error('[loadTranslations] ❌ Ağ/parse hatası (sunucu çalışıyor mu?):', e);
    }
}

function t(key) {
    return LANGS[state.lang]?.[key] || INLINE_LANGS[state.lang]?.[key] || INLINE_LANGS['tr']?.[key] || LANGS['tr']?.[key] || key;
}


const TOOLTIPS = {
    tr: {
        retention: "İzleyicinin videoyu ne kadar izlediğini ölçer. 10'a yakın = izleyici sonuna kadar izliyor.",
        techTempo: "Videodaki ses patlamaları ve sahne değişimlerinin yoğunluğu. Yüksek = dinamik video.",
        seoPower: "Başlık, etiket ve açıklamanın YouTube aramasında seni ne kadar yukarı taşıdığı.",
        peakCount: "Videodaki enerji zirvesi sayısı. Her zirve izleyiciyi ekranda tutar.",
        thumbQual: "Thumbnail'in renk, kontrast ve yüz içeriğine göre tıklanabilirlik puanı.",
        overallScore: "Tüm metriklerin ağırlıklı ortalaması. 7+ iyi, 8.5+ viral potansiyel var.",
        energy: "O anın ses + görsel enerji yüzdesi. %70+ = patlama noktası.",
        viewVelocity: "Videonun günlük ortalama izlenme hızı. Yüksek hız = algoritma videoyu seviyor.",
        viralScore: "Patlama sayısı ve yoğunluğuna göre hesaplanan viral olma ihtimali.",
    },
    en: {
        retention: "Measures how much of the video viewers watch. Close to 10 = viewers watch to the end.",
        techTempo: "Density of audio peaks and scene changes. High = dynamic video.",
        seoPower: "How much your title, tags and description push you up in YouTube search.",
        peakCount: "Number of energy peaks in the video. Each peak keeps viewers on screen.",
        thumbQual: "Clickability score based on thumbnail color, contrast and face content.",
        overallScore: "Weighted average of all metrics. 7+ is good, 8.5+ has viral potential.",
        energy: "Audio + visual energy percentage at that moment. 70%+ = peak point.",
        viewVelocity: "Average daily view speed of the video. High speed = algorithm loves it.",
        viralScore: "Viral probability calculated from peak count and intensity.",
    },
    es: {
        retention: "Mide cuánto del video ven los espectadores. Cerca de 10 = ven hasta el final.",
        techTempo: "Densidad de picos de audio y cambios de escena. Alto = video dinámico.",
        seoPower: "Cuánto tu título, etiquetas y descripción te suben en la búsqueda de YouTube.",
        peakCount: "Número de picos de energía en el video. Cada pico mantiene a los espectadores.",
        thumbQual: "Puntuación de clicabilidad basada en color, contraste y contenido facial.",
        overallScore: "Promedio ponderado de todas las métricas. 7+ es bueno, 8.5+ tiene potencial viral.",
        energy: "Porcentaje de energía de audio + visual en ese momento. 70%+ = punto de explosión.",
        viewVelocity: "Velocidad de vistas diarias promedio. Alta velocidad = el algoritmo lo ama.",
        viralScore: "Probabilidad viral calculada a partir del conteo e intensidad de picos.",
    }
};

function tip(key) {
    return TOOLTIPS[state.lang]?.[key] || TOOLTIPS['tr'][key] || '';
}


const getAnalysisSteps = () => [
    { text: t('step1') },
    { text: t('step2') },
    { text: t('step3') },
    { text: t('step4') },
    { text: t('step5') },
    { text: t('step6') },
    { text: t('step7') }
];

async function loadChannels() {
    try {
        const uid = state.currentUser ? state.currentUser.user_id : 1;
        const res = await fetch(`${API_URL}/channels?user_id=${uid}`);
        state.channels = await res.json();
        render();
    } catch (e) { console.error("Kanallar yüklenemedi", e); }
}

function goHome() {
    currentChannelId = null;
    state.isCreatingChannel = false;
    state.editingChannel = null;
    state.loading = false;
    state.result = null;
    state.progress = 0;
    state.videoFile = null;
    state.currentView = 'dashboard';
    render();
}

function navigateTo(view) {
    // Clear Object URL if exiting analysis view
    if (state.currentView === 'analyze' && view !== 'analyze') {
        revokeVideoObjectURL();
    }
    state.currentView = view;
    if (view === 'dashboard') {
        loadDashboard();
        loadChannels();
    }
    render();
}

function render() {
    injectTooltipCSS();

    const authView = document.getElementById('view-auth');
    const appLayout = document.getElementById('app-layout');
    const sidebarContainer = document.getElementById('sidebar-container');

    // 1. Auth Check
    if (!state.currentUser) {
        authView.innerHTML = renderLoginScreen();
        authView.style.display = 'block';
        if (appLayout) appLayout.style.display = 'none';
        return;
    }

    // 2. Show App Skeleton
    authView.style.display = 'none';
    if (appLayout) appLayout.style.display = 'flex';

    // 3. Update Sidebar Only If Necessary (DOM Optimization)
    const newSidebarHTML = renderSidebar();
    if (sidebarContainer.innerHTML !== newSidebarHTML) {
        sidebarContainer.innerHTML = newSidebarHTML;
    }

    // 4. Determine Content Area
    let contentHTML = '';
    let targetViewId = 'view-dashboard';

    if (state.currentView === 'analyze') {
        if (state.loading) {
            contentHTML = renderLoadingScreen();
            targetViewId = 'view-analyze';
        } else if (state.result) {
            contentHTML = renderResultScreen();
            targetViewId = 'view-result';
        } else if (state.isCreatingChannel) {
            contentHTML = renderCreateChannel();
            targetViewId = 'view-analyze';
        } else if (currentChannelId === null) {
            contentHTML = state.channels.length > 0 ? renderChannelSelection() : renderCreateChannel();
            targetViewId = 'view-analyze';
        } else {
            contentHTML = renderFormScreen();
            targetViewId = 'view-analyze';
        }
    } else if (state.currentView === 'settings') {
        contentHTML = renderSettings();
        targetViewId = 'view-settings';
    } else if (state.currentView === 'content_finder') {
        contentHTML = renderContentFinder();
        targetViewId = 'view-analyze';
    } else if (state.currentView === 'coach') {
        contentHTML = renderCoachPage();
        targetViewId = 'view-analyze';
    } else {
        contentHTML = renderDashboard();
        targetViewId = 'view-dashboard';
    }

    // 5. Update and Show Only the Inside of the Related View
    const views = ['view-dashboard', 'view-analyze', 'view-result', 'view-settings'];
    views.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            if (id === targetViewId) {
                if (el.innerHTML !== contentHTML) el.innerHTML = contentHTML;
                el.style.display = 'block';
            } else {
                el.style.display = 'none';
            }
        }
    });

    // 6. Extra Rendering Processes (Graphics, Video, etc.)
    if (state.result && state.clientCombined && state.clientCombined.length > 0 && targetViewId === 'view-result') {
        requestAnimationFrame(() => {
            drawViralTimeline('viral-timeline-canvas', state.clientCombined, state.clientMoments || [], state.clientVideoDuration || 0, 0);
        });
    }

    if (state.result && state.videoFile && targetViewId === 'view-result') {
        requestAnimationFrame(() => {
            const vid = document.getElementById('my-video-player');
            if (vid && !vid.src) vid.src = getVideoObjectURL();
        });
    }
}

// ── Render with page transition (fade-out → render → fade-in) ──
let _lastView = '';
function navigateWithTransition(view) {
    if (view === _lastView && !state.loading && !state.result) return;
    
    const main = document.getElementById('main-content');
    if (main && _lastView !== '') {
        main.classList.remove('view-enter');
        main.classList.add('view-exit');
        setTimeout(() => {
            state.currentView = view;
            _lastView = view;
            render();
            main.classList.remove('view-exit');
            main.classList.add('view-enter');
        }, 140);
    } else {
        state.currentView = view;
        _lastView = view;
        render();
    }
}

// ═══════════════════════════════════════════════════════════
// LOGIN / REGISTRATION SCREEN
// ═══════════════════════════════════════════════════════════


function injectTooltipCSS() {
    if (document.getElementById('tooltip-style')) return;
    const style = document.createElement('style');
    style.id = 'tooltip-style';
    style.textContent = `
        .tt { position: relative; display: inline-flex; align-items: center; gap: 4px; cursor: help; }
        .tt::after {
            content: attr(data-tip);
            position: absolute;
            bottom: calc(100% + 8px);
            left: 50%;
            transform: translateX(-50%);
            background: #1e1b4b;
            border: 1px solid #7c3aed;
            color: #e2e8f0;
            font-size: 0.78rem;
            line-height: 1.5;
            padding: 8px 12px;
            border-radius: 8px;
            width: 200px;
            max-width: 90vw;
            white-space: normal;
            left: auto;
            right: 0;
            transform: none;
            white-space: normal;
            text-align: left;
            opacity: 0;
            pointer-events: none;
            transition: opacity 0.18s;
            z-index: 9999;
            box-shadow: 0 4px 20px rgba(0,0,0,0.5);
            font-weight: normal;
        }
        .tt:hover::after { opacity: 1; }
        .tt-icon { font-size: 0.7rem; color: #7c3aed; background: rgba(124,58,237,0.15);
                   border-radius: 50%; width: 14px; height: 14px; display: inline-flex;
                   align-items: center; justify-content: center; flex-shrink: 0; }
    `;
    document.head.appendChild(style);
}

function renderLoginScreen() {
    return `
        <div class="login-screen">
            <div class="login-card">
                <div class="login-logo">
                    <span class="login-logo-icon">🎬</span>
                    <h1>${t('loginApp')}</h1>
                    <p class="login-subtitle">${t('loginSub')}</p>
                </div>
                <div class="login-tabs">
                    <button class="login-tab active" id="tab-login" onclick="switchAuthTab('login')">${t('loginTab')}</button>
                    <button class="login-tab" id="tab-register" onclick="switchAuthTab('register')">${t('regTab')}</button>
                </div>
                <div id="auth-form">
                    <input type="text" id="auth-username" placeholder="${t('userPh')}" class="login-input" autocomplete="username">
                    <input type="password" id="auth-password" placeholder="${t('passPh')}" class="login-input" autocomplete="current-password">
                    <div id="email-row" style="display:none;">
                        <input type="email" id="auth-email" placeholder="Email adresin" class="login-input" autocomplete="email">
                    </div>
                    <div id="auth-error" class="login-error" style="display:none;"></div>
                    <button class="analyze-btn" onclick="doLogin()" id="auth-btn" style="width:100%; margin-top:8px;">${t('loginTab')}</button>
                    <button class="google-login-btn" onclick="loginWithGoogle()">
                        <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
                            <path d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92a5.06 5.06 0 0 1-2.2 3.32v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.1z" fill="#4285F4"/>
                            <path d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z" fill="#34A853"/>
                            <path d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18A10.96 10.96 0 0 0 1 12c0 1.77.42 3.45 1.18 4.93l3.66-2.84z" fill="#FBBC05"/>
                            <path d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z" fill="#EA4335"/>
                        </svg>
                        Google ile Giriş Yap
                    </button>
                </div>
                <p class="login-hint">${t('guestText')} <a href="#" onclick="guestLogin(); return false;" style="color:#a855f7;">${t('guestBtn')}</a></p>
            </div>
        </div>
    `;
}

let authMode = 'login';
function switchAuthTab(mode) {
    authMode = mode;
    document.querySelectorAll('.login-tab').forEach(t_el => t_el.classList.remove('active'));
    document.getElementById(`tab-${mode}`)?.classList.add('active');
    const btn = document.getElementById('auth-btn');
    if (btn) btn.textContent = mode === 'login' ? t('loginTab') : t('regTab');
    const err = document.getElementById('auth-error');
    if (err) err.style.display = 'none';
    const emailRow = document.getElementById('email-row');
    if (emailRow) emailRow.style.display = mode === 'register' ? 'block' : 'none';
}

async function doLogin() {
    const username = document.getElementById('auth-username')?.value.trim();
    const password = document.getElementById('auth-password')?.value;
    const email = document.getElementById('auth-email')?.value.trim();
    const errEl = document.getElementById('auth-error');
    const btn = document.getElementById('auth-btn');

    if (!username || !password) {
        if (errEl) { errEl.textContent = t('emptyCreds'); errEl.style.display = 'block'; }
        return;
    }
    if (authMode === 'register' && (!email || !email.includes('@'))) {
        if (errEl) { errEl.textContent = 'Geçerli bir email adresi girin.'; errEl.style.display = 'block'; }
        return;
    }

    if (btn) { btn.textContent = t('wait'); btn.disabled = true; }
    try {
        const endpoint = authMode === 'login' ? '/api/auth/login' : '/api/auth/register';
        const body = authMode === 'register'
            ? { username, password, email, lang: state.lang }
            : { username, password };

        const res = await fetch(`${API_URL}${endpoint}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const data = await res.json();

        if (data.error === 'EMAIL_NOT_VERIFIED') {
            showVerificationScreen(data.user_id, data.email);
            return;
        }
        if (data.error) {
            if (errEl) { errEl.textContent = data.error; errEl.style.display = 'block'; }
            if (btn) { btn.textContent = authMode === 'login' ? t('loginTab') : t('regTab'); btn.disabled = false; }
        } else if (data.needs_verification) {
            showVerificationScreen(data.user_id, data.email);
        } else {
            setCurrentUser({ user_id: data.user_id, username: data.username });
        }
    } catch (e) {
        if (errEl) { errEl.textContent = t('connErr'); errEl.style.display = 'block'; }
        if (btn) { btn.textContent = authMode === 'login' ? t('loginTab') : t('regTab'); btn.disabled = false; }
    }
}

function guestLogin() {
    setCurrentUser({ user_id: 1, username: 'Misafir' });
}

async function loginWithGoogle() {
    try {
        const res = await fetch(`${API_URL}/api/auth/google/url`);
        const data = await res.json();
        if (data.error) {
            alert(data.error);
        } else if (data.url) {
            window.location.href = data.url;
        }
    } catch (e) {
        alert(t('connErr'));
    }
}

function showVerificationScreen(userId, email) {
    const root = document.getElementById('root');
    if (!root) return;
    root.innerHTML = `
        <div class="login-screen">
            <div class="login-card">
                <div class="login-logo">
                    <span style="font-size:3rem;">📧</span>
                    <h1 style="font-size:1.4rem;margin-top:10px;">${t('emailVerify')}</h1>
                    <p class="login-subtitle">${email} ${t('codeSent')}</p>
                </div>
                <div id="ver-form">
                    <input type="text" id="ver-code" placeholder="${t('sixDigit')}"
                        class="login-input" maxlength="6"
                        style="text-align:center;font-size:1.5rem;letter-spacing:8px;font-weight:bold;"
                        oninput="this.value=this.value.replace(/[^0-9]/g,'')">
                    <div id="ver-error" class="login-error" style="display:none;"></div>
                    <button class="analyze-btn" onclick="submitVerification(${userId})" id="ver-btn" style="width:100%;margin-top:8px;">
                        ${t('verify')}
                    </button>
                    <button onclick="resendCode(${userId})" id="resend-btn"
                        style="width:100%;margin-top:8px;background:transparent;border:1px solid #7c3aed;color:#a855f7;padding:10px;border-radius:8px;cursor:pointer;font-size:0.9rem;">
                        ${t('resendBtn')}
                    </button>
                    <p style="color:#94a3b8;font-size:0.8rem;text-align:center;margin-top:12px;">
                        ${t('checkSpam')}
                    </p>
                </div>
            </div>
        </div>
    `;
    setTimeout(() => document.getElementById('ver-code')?.focus(), 100);
}

async function submitVerification(userId) {
    const code = document.getElementById('ver-code')?.value.trim();
    const errEl = document.getElementById('ver-error');
    const btn = document.getElementById('ver-btn');
    if (!code || code.length !== 6) {
        if (errEl) { errEl.textContent = t('codeIncomplete'); errEl.style.display = 'block'; }
        return;
    }
    if (btn) { btn.textContent = t('wait'); btn.disabled = true; }
    try {
        const res = await fetch(`${API_URL}/api/auth/verify`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, code })
        });
        const data = await res.json();
        if (data.error) {
            if (errEl) { errEl.textContent = data.error; errEl.style.display = 'block'; }
            if (btn) { btn.textContent = t('verify'); btn.disabled = false; }
        } else {
            setCurrentUser({ user_id: data.user_id, username: data.username });
        }
    } catch (e) {
        if (errEl) { errEl.textContent = t('connErr'); errEl.style.display = 'block'; }
        if (btn) { btn.textContent = t('verify'); btn.disabled = false; }
    }
}

async function resendCode(userId) {
    const btn = document.getElementById('resend-btn');
    if (btn) { btn.textContent = t('sending'); btn.disabled = true; }
    try {
        const res = await fetch(`${API_URL}/api/auth/resend`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ user_id: userId, lang: state.lang })
        });
        const data = await res.json();
        if (data.success) {
            alert(t('codeSentMsg'));
        } else {
            alert(data.error);
        }
    } catch (e) {
        alert(t('connErr'));
    } finally {
        if (btn) { btn.textContent = t('resendBtn'); btn.disabled = false; }
    }
}

function setCurrentUser(user) {
    state.currentUser = user;
    const json = JSON.stringify(user);
    try { localStorage.setItem('yt_user', json); } catch (e) { }
    try { sessionStorage.setItem('yt_user', json); } catch (e) { }
    fetch(`${API_URL}/api/session`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: json
    }).catch(() => { });
    state.currentView = 'dashboard';
    render();
    loadChannels();
    loadDashboard();
}

function logOut() {
    localStorage.removeItem('yt_user');
    sessionStorage.removeItem('yt_user');
    state.currentUser = null;
    fetch(`${API_URL}/api/session`, { method: 'DELETE' }).catch(() => { });
    state.currentView = 'dashboard';
    state.channels = [];
    currentChannelId = null;
    state.dashboardData = null;
    render();
}

// ═══════════════════════════════════════════════════════════
// SIDEBAR
// ═══════════════════════════════════════════════════════════
function renderSidebar() {
    const nav = [
        { view: 'dashboard', icon: '🏠', label: t('dashboard') },
        { view: 'analyze', icon: '📊', label: t('analyze') },
        { view: 'coach', icon: '🤖', label: t('coach') },
        { view: 'content_finder', icon: '🔍', label: t('finder') },
        { view: 'settings', icon: '⚙️', label: t('settings') },
    ];
    const items = nav.map(n => `
        <li class="sidebar-item ${state.currentView === n.view ? 'active' : ''}"
            onclick="navigateWithTransition('${n.view}')">
            <span class="sidebar-icon">${n.icon}</span>
            <span class="sidebar-label">${n.label}</span>
        </li>
    `).join('');
    return `
        <aside class="sidebar">
            <div class="sidebar-top">
                <div class="sidebar-brand">
                    <span>🎬</span>
                    <span class="sidebar-brand-text">YT Analiz</span>
                </div>
                <nav><ul class="sidebar-nav">${items}</ul></nav>
            </div>
            <div class="sidebar-bottom">
                <div class="sidebar-user">
                    <span class="sidebar-user-avatar">${(state.currentUser && state.currentUser.username && state.currentUser.username !== 'undefined' ? state.currentUser.username : 'K')[0].toUpperCase()}</span>
                    <span class="sidebar-user-name">${state.currentUser && state.currentUser.username && state.currentUser.username !== 'undefined' ? state.currentUser.username : ''}</span>
                </div>
                <select onchange="changeLang(this.value)" style="width:100%;background:rgba(0,0,0,0.3);color:rgba(255,255,255,0.7);padding:6px;border:1px solid #7c3aed;border-radius:6px;margin-top:8px;margin-bottom:8px;font-size:0.8rem;">
                    <option value="tr" ${state.lang === 'tr' ? 'selected' : ''}>🇹🇷 Türkçe</option>
                    <option value="en" ${state.lang === 'en' ? 'selected' : ''}>🇬🇧 English</option>
                    <option value="es" ${state.lang === 'es' ? 'selected' : ''}>🇪🇸 Español</option>
                </select>
                <button class="sidebar-logout" onclick="logOut()">${t('logout')}</button>
            </div>
        </aside>
    `;
}

// ═══════════════════════════════════════════════════════════
// DASHBOARD
// ═══════════════════════════════════════════════════════════
// LATEST ANALYSIS — HELPER FUNCTIONS
// ═══════════════════════════════════════════════════════════
let _dashShowAll = false;

function renderRecentAnalysesList(analyses) {
    const top5 = analyses.slice(0, 5);
    const rest  = analyses.slice(5);
    const hasMore = rest.length > 0;

    function rowHTML(a, showInspect) {
        return `
        <div class="recent-item" id="analysis-row-${a.id}" style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
            <div style="flex:1;min-width:0;">
                <div class="recent-title" style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">${escapeHTML(a.video) || '—'}</div>
                <div style="display:flex;gap:10px;align-items:center;margin-top:4px;">
                    <span class="recent-channel">${escapeHTML(a.channel) || ''}</span>
                    <span class="recent-score">${a.score}/10</span>
                    <span style="color:#64748b;font-size:0.75rem;">${a.date ? a.date.split(' ')[0] : ''}</span>
                </div>
            </div>
            <div style="display:flex;gap:6px;flex-shrink:0;">
                ${showInspect ? `<button onclick="inspectAnalysis(${a.id})"
                    style="background:linear-gradient(135deg,#7c3aed,#a855f7);color:#fff;border:none;
                    padding:5px 12px;border-radius:8px;font-size:0.8rem;font-weight:600;cursor:pointer;">
                    🔍 İncele
                </button>` : ''}
                <button onclick="deleteAnalysis(${a.id})"
                    style="background:rgba(239,68,68,0.15);color:#ef4444;border:1px solid rgba(239,68,68,0.3);
                    padding:5px 9px;border-radius:8px;font-size:0.9rem;cursor:pointer;" title="Analizi Sil">
                    🗑️
                </button>
            </div>
        </div>`;
    }

    const top5HTML  = top5.map(a => rowHTML(a, true)).join('');
    const restHTML  = hasMore ? rest.map(a => rowHTML(a, false)).join('') : '';

    return `
        <div class="section-title" style="margin-top:30px;">${t('recentAna')}</div>
        <div class="recent-list" id="recent-list-top5">${top5HTML}</div>
        ${hasMore ? `
        <div id="recent-list-rest" style="${_dashShowAll ? '' : 'display:none;'}">
            <div class="recent-list">${restHTML}</div>
        </div>
        <div style="text-align:center;margin-top:8px;">
            <button onclick="toggleDashboardAll()"
                id="btn-show-all"
                style="background:transparent;border:1px solid #7c3aed;color:#a78bfa;
                padding:6px 20px;border-radius:20px;font-size:0.85rem;cursor:pointer;">
                ${_dashShowAll ? '▲ Daha Az Göster' : `▼ Tümünü Gör (${analyses.length})`}
            </button>
        </div>` : ''}
    `;
}

function toggleDashboardAll() {
    _dashShowAll = !_dashShowAll;
    // Partial DOM update — no full re-render
    const restEl = document.getElementById('recent-list-rest');
    const btnEl  = document.getElementById('btn-show-all');
    const total  = (state.dashboardData && state.dashboardData.recent_analyses)
        ? state.dashboardData.recent_analyses.length : 0;
    if (restEl) restEl.style.display = _dashShowAll ? '' : 'none';
    if (btnEl)  btnEl.textContent = _dashShowAll
        ? '▲ Daha Az Göster'
        : `▼ Tümünü Gör (${total})`;
}

async function inspectAnalysis(id) {
    try {
        const res = await fetch(`${API_URL}/api/analyses/${id}`);
        const data = await res.json();
        if (data.error) { alert('Analiz yüklenemedi: ' + data.error); return; }

        // Convert API response to the format renderResultScreen expects.
        // The stored blob is a data bag: besides the rival it carries the thumbnail
        // analysis and the viral segments, so it is present even when no rival was
        // found. Treating it as a rival would blank the screen on comp.channel.
        let blob = null;
        try { blob = data.competitor_data ? JSON.parse(data.competitor_data) : null; } catch(e) {}
        // Rows saved before the rival became optional carry no flag but do have one.
        const hasComp = !!(blob && blob.has_competitor !== false && blob.title);

        state.result = {
            analysis_id:        data.analysis_id,
            title:              data.video_name,
            overall_score:      data.overall_score,
            retention_score:    data.retention_score,
            tech_score:         data.tech_score,
            seo_score:          data.seo_score,
            thumb_score:        data.thumb_score || 0,
            peaks:              data.peaks,
            viral_score:        data.viral_score,
            dynamic_feedback:   data.coach_feedback,
            dynamic_feedback_tr: data.coach_feedback,
            dynamic_feedback_en: data.coach_feedback,
            dynamic_feedback_es: data.coach_feedback,
            competitor_data:    hasComp ? blob : null,
            competitor_status:  (blob && blob.competitor_status) || (hasComp ? 'ok' : 'no_confident_match'),
            viral_segments:     (blob && blob._viral_segments) || [],
            thumb_data:         (blob && blob._thumb_data) || {},
            is_shorts_mode:     false,
            ffmpeg_available:   false,
            is_history:         true,
            email_sent:         false,
            retention_data:     { score: data.retention_score, has_csv: false, worst_drop_sec: 0, drop_percent: 0, early_drop_sec: 0 },
            tech_data:          { tech_score: data.tech_score, peaks: data.peaks, peak_times: [], max_gap: 0, viral_score: data.viral_score, duration: 0 },
            visual_tempo:       [],
            audio_tempo:        [],
            channel_comparison: { avg_overall: 0, avg_retention: 0, avg_tech: 0, avg_seo: 0, avg_thumb: 0 },
            industry_std:       { tempo: 7.0, seo: 8.0, retention: 6.0 },
            critical_warning:   '',
            kill_switch_active: false,
            scene_changes:      {},
            ffmpeg_available:   false,
        };

        state.currentView = 'analyze';
        state.loading = false;
        state.clientCombined = [];
        render();
    } catch(e) {
        alert('Analiz yüklenirken hata oluştu.');
        console.error(e);
    }
}

async function deleteAnalysis(id) {
    if (!confirm('Bu analizi kalıcı olarak silmek istediğinden emin misin?')) return;
    try {
        const res = await fetch(`${API_URL}/api/analyses/${id}`, { method: 'DELETE' });
        const data = await res.json();
        if (!data.success) { alert('Silme başarısız: ' + (data.error || '')); return; }

        // Update dashboard data and render
        if (state.dashboardData && state.dashboardData.recent_analyses) {
            state.dashboardData.recent_analyses = state.dashboardData.recent_analyses.filter(a => a.id !== id);
            state.dashboardData.analysis_count = Math.max(0, (state.dashboardData.analysis_count || 1) - 1);
        }
        render();
    } catch(e) {
        alert('Silme sırasında hata oluştu.');
    }
}

// ═══════════════════════════════════════════════════════════
function renderDashboard() {
    const dd = state.dashboardData;
    const ddOk = dd && !dd.error && dd.channel_count !== undefined;

    const uname = (state.currentUser && state.currentUser.username && state.currentUser.username !== 'undefined')
        ? state.currentUser.username
        : (state.currentUser && state.currentUser.user_id ? 'User #' + state.currentUser.user_id : 'User');

    const statsHTML = ddOk ? `
        <div class="dashboard-stats">
            <div class="stat-card">
                <div class="stat-value">${dd.channel_count !== undefined ? dd.channel_count : '—'}</div>
                <div class="stat-label">${t('statCh')}</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${dd.analysis_count !== undefined ? dd.analysis_count : '—'}</div>
                <div class="stat-label">${t('statAna')}</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${dd.avg_score || '—'}</div>
                <div class="stat-label">${t('statAvg')}</div>
            </div>
        </div>
        ${dd.recent_analyses && dd.recent_analyses.length ? renderRecentAnalysesList(dd.recent_analyses) : ''}
    ` : `<p style="color:#94a3b8;text-align:center;padding:40px 0;">${dd && dd.error ? '⚠️ ' + dd.error : t('loadingText')}</p>`;

    const channelListHTML = state.channels.length > 0 ? `
        <div class="section-title" style="margin-top:30px;">${t('yourCh')}</div>
        <div style="display:flex;flex-direction:column;gap:10px;">
            ${state.channels.map(ch => `
                <div class="channel-card" onclick="startAnalyzeFor(${ch.id})">
                    <div>
                        <strong>${escapeHTML(ch.name)}</strong>
                        <span class="channel-type">${escapeHTML(ch.content_type) || 'Genel'}</span>
                    </div>
                    <span class="channel-arrow">${t('analyzeBtnText')}</span>
                </div>
            `).join('')}
        </div>
        <button class="retry-btn" style="margin-top:15px;border-radius:12px;" onclick="startNewChannel()">${t('newChBtn')}</button>
    ` : `
        <div style="text-align:center;padding:40px 0;">
            <p style="color:#94a3b8;margin-bottom:20px;">${t('noChYet')}</p>
            <button class="analyze-btn" onclick="startNewChannel()">${t('firstChBtn')}</button>
        </div>
    `;

    return `
        <div class="main-container">
            <h1 style="font-size:2rem;">${t('welcome')}, ${uname} 👋</h1>
            <p class="subtitle">${t('dashSub')}</p>
            ${statsHTML}
            ${channelListHTML}
        </div>
    `;
}

function startAnalyzeFor(channelId) {
    state.currentView = 'analyze';
    state.isCreatingChannel = false;
    state.editingChannel = null;
    state.result = null;
    state.loading = false;
    currentChannelId = channelId;
    render();
}

function startNewChannel() {
    state.currentView = 'analyze';
    state.isCreatingChannel = true;
    state.editingChannel = null;
    currentChannelId = null;
    render();
}

async function loadDashboard() {
    if (!state.currentUser) return;
    try {
        const userId = state.currentUser.user_id || 1;
        const res = await fetch(`${API_URL}/api/profile?user_id=${userId}`);
        const data = await res.json();
        if (data.error) {
            state.dashboardData = { channel_count: state.channels.length || 0, analysis_count: 0, avg_score: null, recent_analyses: [] };
        } else {
            state.dashboardData = data;
        }
        render();
    } catch (e) {
        state.dashboardData = { channel_count: state.channels.length || 0, analysis_count: 0, avg_score: null, recent_analyses: [] };
        render();
    }
}

// ═══════════════════════════════════════════════════════════
// AI COACH PAGE
// ═══════════════════════════════════════════════════════════
function renderCoachPage() {
    const tips = [
        { icon: '📊', q: t('fast_q1') },
        { icon: '🎯', q: t('fast_q2') },
        { icon: '🔥', q: t('fast_q3') },
        { icon: '⏱️', q: t('fast_q4') },
        { icon: '📝', q: t('fast_q5') },
        { icon: '🎬', q: t('fast_q6') },
    ];
    const tipsHTML = tips.map(tip => `
        <button onclick="askCoach('${tip.q.replace(/'/g, "\\'")}')"
            style="background:rgba(139,92,246,0.12);border:1px solid rgba(139,92,246,0.3);
                   color:#d8b4fe;padding:10px 14px;border-radius:10px;cursor:pointer;
                   font-size:0.88rem;text-align:left;transition:all 0.2s;display:flex;align-items:center;gap:8px;"
            onmouseover="this.style.background='rgba(139,92,246,0.25)'"
            onmouseout="this.style.background='rgba(139,92,246,0.12)'">
            ${tip.icon} ${tip.q}
        </button>
    `).join('');

    return `
        <div class="main-container" style="max-width:700px;">
            <h1 style="font-size:2rem;">🤖 ${t('coachTitle')}</h1>
            <p class="subtitle">${t('coachDesc')}</p>

            ${!hasGroqKey ? `
                <div style="background:rgba(245,158,11,0.1);border:1px solid #f59e0b;border-radius:12px;padding:20px;margin:20px 0;text-align:center;">
                    <div style="font-size:2rem;margin-bottom:10px;">🔑</div>
                    <h3 style="color:#fbbf24;margin-bottom:8px;">${t('apiKeyReq')}</h3>
                    <p style="color:#94a3b8;font-size:0.9rem;margin-bottom:15px;">${t('apiKeyDesc')}</p>
                    <button class="analyze-btn" style="width:auto;padding:10px 24px;" onclick="navigateTo('settings')">
                        ${t('goToSet')}
                    </button>
                </div>
            ` : `
                <div style="background:rgba(34,197,94,0.1);border:1px solid #22c55e;border-radius:10px;padding:12px 16px;margin-bottom:20px;font-size:0.88rem;color:#4ade80;display:flex;align-items:center;gap:8px;">
                    ✅ <span>${t('coach_connected')}</span>
                </div>
            `}

            <div class="section-title">${t('fastQs')}</div>
            <div style="display:grid;grid-template-columns:1fr 1fr;gap:10px;margin-bottom:25px;">
                ${tipsHTML}
            </div>

            <div style="background:rgba(30,20,50,0.6);border:1px solid rgba(168,85,247,0.25);border-radius:12px;padding:18px;">
                <p style="color:#94a3b8;font-size:0.9rem;margin-bottom:12px;">${t('chatNowDesc')}</p>
                <button class="analyze-btn" style="width:auto;padding:10px 24px;" onclick="openChatFromCoach()">
                    ${t('chatNowBtn')}
                </button>
            </div>
        </div>
    `;
}
function askCoach(question) {
    if (!chatOpen) { chatOpen = true; renderChatbot(); }
    setTimeout(() => {
        const inp = document.getElementById('chatInput');
        if (inp) { inp.value = question; sendChat(); }
    }, 150);
}

function openChatFromCoach() {
    chatOpen = true;
    renderChatbot();
    setTimeout(() => {
        const inp = document.getElementById('chatInput');
        if (inp) inp.focus();
    }, 150);
}

// ═══════════════════════════════════════════════════════════
// SETTINGS
// ═══════════════════════════════════════════════════════════
function renderSettings() {
    const activeLang = state.lang || 'tr';

    function card(code, flag, label) {
        const isActive = activeLang === code;
        const bg = isActive ? 'linear-gradient(135deg,rgba(107,33,168,0.6),rgba(147,51,234,0.5))' : 'rgba(255,255,255,0.06)';
        const bord = isActive ? '2px solid #a855f7' : '2px solid rgba(168,85,247,0.2)';
        const sh = isActive ? '0 0 16px rgba(168,85,247,0.4)' : 'none';
        const col = isActive ? '#f0abfc' : '#e2e8f0';
        const tick = isActive ? '<div style="position:absolute;top:6px;right:8px;color:#a855f7;font-size:1rem;">✓</div>' : '';
        return '<div onclick="changeLang(\'' + code + '\')" style="flex:1;position:relative;padding:18px 10px 14px;text-align:center;border-radius:12px;cursor:pointer;background:' + bg + ';border:' + bord + ';box-shadow:' + sh + ';transition:all 0.2s;">' +
            tick +
            '<div style="font-size:2rem;margin-bottom:6px;line-height:1;">' + flag + '</div>' +
            '<div style="font-weight:700;font-size:0.95rem;color:' + col + ';">' + label + '</div>' +
            '</div>';
    }

    return '<div class="main-container">' +
        '<h1 style="font-size:2rem;">⚙️ ' + t('settings') + '</h1>' +
        '<p class="subtitle">' + t('setDesc') + '</p>' +

        '<div class="settings-group" style="margin-top:20px;">' +
        '<div class="section-title">' + t('st_lang') + '</div>' +
        '<p style="font-size:0.85rem;color:#94a3b8;margin:8px 0 14px;">' + t('setLangDesc') + '</p>' +
        '<div style="display:flex;gap:12px;">' +
        card('tr', '🇹🇷', 'Türkçe') +
        card('en', '🇬🇧', 'English') +
        card('es', '🇪🇸', 'Español') +
        '</div>' +
        '</div>' +

        '<div class="settings-group" style="margin-top:25px;">' +
        '<div class="section-title">' + t('st_groq') + '</div>' +
        '<p style="font-size:0.85rem;color:#94a3b8;margin-bottom:12px;">' + t('groqLinkDesc') + ' <a href="https://console.groq.com" target="_blank" style="color:#a855f7;">console.groq.com</a></p>' +
        '<input type="text" id="groq-key-input" placeholder="gsk_..." value="' + (state.groqKey || '') + '">' +
        '<button class="analyze-btn" style="padding:10px 20px;" onclick="saveGroqKeySettings(event)">' + t('save') + '</button>' +
        '</div>' +

        '<div class="settings-group" style="margin-top:25px;">' +
        '<div class="section-title">' + t('st_gemini') + '</div>' +
        '<p style="font-size:0.85rem;color:#94a3b8;margin-bottom:12px;">' + t('geminiLinkDesc') + ' <a href="https://aistudio.google.com/app/apikey" target="_blank" style="color:#a855f7;">aistudio.google.com</a></p>' +
        '<input type="text" id="gemini-key-input" placeholder="AIzaSy..." value="' + (state.geminiKey || '') + '">' +
        '<button class="analyze-btn" style="padding:10px 20px;" onclick="saveGeminiKeySettings()">' + t('save') + '</button>' +
        '</div>' +

        '<div class="settings-group" style="margin-top:25px;">' +
        '<div class="section-title">📧 Email (SMTP)</div>' +
        '<p style="font-size:0.85rem;color:#94a3b8;margin-bottom:12px;">' + (state.lang==='en' ? 'Gmail App Password enables email verification.' : state.lang==='es' ? 'Gmail App Password activa la verificación.' : 'Gmail App Password ile mail doğrulama aktif olur.') + '</p>' +
        '<input type="email" id="smtp-email-input" placeholder="' + (state.lang==='en' ? 'Your Gmail (example@gmail.com)' : state.lang==='es' ? 'Tu Gmail (ejemplo@gmail.com)' : 'Gmail adresin (ornek@gmail.com)') + '" style="margin-bottom:8px;">' +
        '<input type="password" id="smtp-pass-input" placeholder="' + (state.lang==='en' ? 'App Password (16 chars)' : state.lang==='es' ? 'App Password (16 caracteres)' : 'Gmail App Password (16 haneli)') + '">' +
        '<button class="analyze-btn" style="padding:10px 20px;" onclick="saveSmtpSettings()">💾 ' + t('save') + '</button>' +
        '</div>' +

        '<div class="settings-group" style="margin-top:25px;">' +
        '<div class="section-title">' + t('st_acc') + '</div>' +
        '<p style="color:#94a3b8;margin-bottom:12px;">' + t('accUser') + ' <strong style="color:white;">' + (state.currentUser && state.currentUser.username ? state.currentUser.username : '') + '</strong></p>' +
        '<button class="retry-btn" onclick="logOut()" style="width:auto;padding:10px 20px;">🚪 ' + t('logout') + '</button>' +
        '</div>' +
        '</div>';
}

function changeLang(val) {
    localStorage.setItem('ytlang', val);
    state.lang = val;
    render();
}

async function saveGroqKeySettings(event) {
    const btn = event?.currentTarget || event?.target;
    let val = document.getElementById('groq-key-input')?.value.trim();
    if (!val) val = document.getElementById('groqKeyInput')?.value.trim();
    if (!val) { alert(t('inputKey')); return; }

    if (btn) { btn.textContent = t('verifying'); btn.disabled = true; }
    try {
        const fd = new FormData(); fd.append('key', val);
        const res = await fetch(`${API_URL}/api/settings/groq`, { method: 'POST', body: fd });
        const data = await res.json();
        if (data.success) {
            state.groqKey = val;
            hasGroqKey = true;
            if (btn) { btn.textContent = t('saved'); btn.disabled = false; }
            try {
                await loadChatSessions();
                if (chatSessions.length === 0) { await newChatSession(); }
                else if (!currentSessionId) { await loadSession(chatSessions[0].id); }
                renderChatbot();
            } catch (e) { }
            setTimeout(() => { if (btn) btn.textContent = t('save'); }, 2500);
        } else {
            alert(t('error') + ': ' + (data.error || 'Bilinmeyen'));
            if (btn) { btn.textContent = t('save'); btn.disabled = false; }
        }
    } catch (e) {
        alert('Bağlantı hatası!');
        if (btn) { btn.textContent = t('save'); btn.disabled = false; }
    }
}

async function saveGeminiKeySettings() {
    const val = document.getElementById('gemini-key-input')?.value.trim();
    if (!val) { alert(t('inputKey')); return; }
    try {
        const fd = new FormData(); fd.append('key', val);
        const res = await fetch(`${API_URL}/api/settings/gemini`, { method: 'POST', body: fd });
        const data = await res.json();
        if (data.success) { state.geminiKey = val; alert(t('saved')); }
        else alert(t('error') + ': ' + (data.error || 'Bilinmeyen'));
    } catch (e) { alert('Bağlantı hatası!'); }
}

async function saveSmtpSettings() {
    const email = document.getElementById('smtp-email-input')?.value.trim();
    const password = document.getElementById('smtp-pass-input')?.value.trim();
    if (!email || !password) { alert('Email ve şifre boş olamaz.'); return; }
    try {
        const res = await fetch(`${API_URL}/api/settings/smtp`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ email, password })
        });
        const data = await res.json();
        if (data.success) alert('✅ SMTP ayarları kaydedildi!');
        else alert('Hata: ' + (data.error || 'Bilinmeyen'));
    } catch (e) { alert('Bağlantı hatası!'); }
}


// ═══════════════════════════════════════════════════════════
// CONTENT FINDER
// ═══════════════════════════════════════════════════════════
function renderContentFinder() {
    const data = state.contentFinderData;
    const isSearching = state.isSearchingContent;
    let contentHTML = '';

    if (isSearching) {
        contentHTML = `
            <div style="text-align:center;padding:60px 20px;">
                <div class="spinner"></div>
                <h2 style="margin-top:20px;font-size:1.5rem;background:linear-gradient(135deg,#a855f7,#ec4899);-webkit-background-clip:text;-webkit-text-fill-color:transparent;">
                    ${t('scan1')}
                </h2>
                <p style="color:#94a3b8;margin-top:10px;">${t('scan2')}</p>
            </div>`;
    } else if (data) {
        if (data.error) {
            contentHTML = `<div class="warning-box" style="display:block;margin-top:20px;">⚠️ ${data.error}</div>`;
        } else {
            const videoList = data.videos.map(v => `
                <div class="content-video-row ${v.is_outlier ? 'outlier' : ''}">
                    <div style="flex:1;">
                        <a href="${escapeHTML(v.url)}" target="_blank" style="color:white;text-decoration:none;font-weight:600;display:block;margin-bottom:4px;">${escapeHTML(v.title)}</a>
                        <div style="font-size:0.8rem;color:#94a3b8;">📺 ${escapeHTML(v.channel)} • 🔥 ${v.views.toLocaleString()} izlenme • ⏱️ ${v.days_passed} gün</div>
                    </div>
                    <div class="velocity-badge ${v.is_outlier ? 'outlier' : ''}">${v.is_outlier ? '🔥 ' : ''}Hız: ${v.view_velocity}/gün</div>
                </div>
            `).join('');

            let aiCards = '';
            if (!data.has_api_key) {
                aiCards = `<div style="text-align:center;padding:30px;background:rgba(239,68,68,0.1);border:1px solid rgba(239,68,68,0.3);border-radius:12px;">
                    <span style="font-size:2rem;display:block;margin-bottom:10px;">🤖</span>
                    <h3 style="color:#fca5a5;margin-bottom:8px;">${t('aiOff')}</h3>
                    <p style="color:#94a3b8;font-size:0.9rem;">${t('aiOffDesc')}</p>
                </div>`;
            } else if (data.ai_ideas && data.ai_ideas.length > 0) {
                aiCards = `<div style="display:flex;flex-direction:column;gap:16px;">
                    ${data.ai_ideas.map(idea => `
                        <div class="ai-idea-card">
                            <h4 style="color:white;font-size:1.1rem;margin-bottom:10px;border-bottom:1px solid rgba(168,85,247,0.2);padding-bottom:8px;">💡 ${idea.title || 'Yeni Fikir'}</h4>
                            <div style="margin-bottom:8px;">
                                <span style="font-size:0.8rem;color:#f59e0b;font-weight:bold;display:block;text-transform:uppercase;">${t('hookLabel')}</span>
                                <span style="font-size:0.9rem;color:#d8b4fe;">"${idea.hook || ''}"</span>
                            </div>
                            <div>
                                <span style="font-size:0.8rem;color:#10b981;font-weight:bold;display:block;text-transform:uppercase;">${t('thumbLabel')}</span>
                                <span style="font-size:0.85rem;color:#94a3b8;">${idea.thumbnail || ''}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>`;
            } else {
                aiCards = `<p style="color:#94a3b8;text-align:center;">${t('noAiIdea')}</p>`;
            }

            contentHTML = `
                <div class="content-finder-results">
                    <div class="cfr-left">
                        <div class="section-title" style="margin-top:0;">${t('marketAna')}</div>
                        <div class="video-list-container">${videoList}</div>
                    </div>
                    <div class="cfr-right">
                        <div class="section-title" style="margin-top:0;">${t('aiIdeas')}</div>
                        ${aiCards}
                    </div>
                </div>`;
        }
    } else {
        contentHTML = `
            <div style="text-align:center;padding:40px 20px;">
                <span style="font-size:4rem;display:block;margin-bottom:15px;opacity:0.8;">🚀</span>
                <p style="color:#94a3b8;max-width:400px;margin:0 auto;">${t('finderEmpty')}</p>
            </div>`;
    }

    return `
        <div class="main-container" style="max-width:950px;">
            <h1 style="font-size:2.2rem;text-align:left;">${t('finderTitle')}</h1>
            <p class="subtitle" style="text-align:left;margin-bottom:25px;">${t('finderSub')}</p>
            <div class="search-bar-container">
                <input type="text" id="cf-keyword" placeholder="${t('searchPh')}" value="${state.cfLastKeyword || ''}"
                    style="flex:1 !important;width:0 !important;min-width:0 !important;margin-bottom:0 !important;padding:14px 18px !important;font-size:1rem !important;border-radius:10px !important;background:rgba(20,10,30,0.9) !important;border:1px solid rgba(168,85,247,0.5) !important;color:#fff !important;">
                <button onclick="startContentSearch()"
                    style="flex-shrink:0;width:auto;padding:14px 24px;background:linear-gradient(90deg,#9333ea,#db2777);border:none;border-radius:10px;color:white;font-weight:800;font-size:1rem;cursor:pointer;white-space:nowrap;box-shadow:0 6px 20px rgba(147,51,234,0.35);">
                    ${t('searchBtn')}
                </button>
            </div>
            ${contentHTML}
        </div>`;
}

async function startContentSearch() {
    const input = document.getElementById('cf-keyword');
    const kw = input ? input.value.trim() : '';
    if (!kw) return alert(t('emptySearch'));
    state.cfLastKeyword = kw;
    state.isSearchingContent = true;
    state.contentFinderData = null;
    render();
    try {
        const res = await fetch(`${API_URL}/api/content_finder`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                keyword: kw,
                user_id: state.currentUser ? state.currentUser.user_id : 1,
                lang: state.lang
            })
        });
        state.contentFinderData = await res.json();
    } catch (e) {
        state.contentFinderData = { error: t('serverErr') };
    } finally {
        state.isSearchingContent = false;
        render();
    }
}

// ═══════════════════════════════════════════════════════════
// CHANNEL MANAGEMENT
// ═══════════════════════════════════════════════════════════
function renderCreateChannel() {
    const isEdit = !!state.editingChannel;
    const ch = state.editingChannel || { name: '', content_type: '', target_audience: '', purpose: '', channel_rules: '' };
    return `
        <div class="main-container">
            <h1>${isEdit ? t('editCh') : t('newCh')}</h1>
            <p class="subtitle">${t('chDesc')}</p>
            <input type="text" id="channelName" placeholder="${t('chNamePh')}" value="${escapeHTML(ch.name)}">
            <input type="text" id="contentType" placeholder="${t('chTypePh')}" value="${escapeHTML(ch.content_type || '')}">
            <input type="text" id="targetAudience" placeholder="${t('chAudPh')}" value="${escapeHTML(ch.target_audience || '')}">
            <textarea id="purpose" placeholder="${t('chPurpPh')}">${escapeHTML(ch.purpose || '')}</textarea>

            <div style="margin-top:20px;">
                <label style="display:flex;align-items:center;gap:8px;font-weight:700;color:#a855f7;font-size:1rem;margin-bottom:8px;">
                    🧠 AI Koç Özel Talimatları (Hafıza)
                </label>
                <p style="font-size:0.82rem;color:#94a3b8;margin-bottom:8px;line-height:1.5;">
                    AI Koç'un bu kanal için her zaman hatırlamasını istediğin özel kuralları buraya yaz.<br>
                    <em>Örnek: "Ben asla Rocket League oynamam, sadece L4D2 oynarım." veya "Kanalımın dili her zaman Türkçedir."</em>
                </p>
                <textarea id="channelRules"
                    placeholder="AI Koç'un bu kanalı tanıması için özel talimatlar... (isteğe bağlı)"
                    style="min-height:110px;border-color:rgba(168,85,247,0.4);background:rgba(88,28,135,0.08);">${escapeHTML(ch.channel_rules || '')}</textarea>
            </div>

            <button class="analyze-btn" onclick="saveChannel()" style="margin-top:20px;">
                ${isEdit ? t('saveCh') : t('createChAcc')}
            </button>
        </div>`;
}

async function saveChannel() {
    const fields = {
        name: document.getElementById('channelName').value.trim(),
        content_type: document.getElementById('contentType').value.trim(),
        target_audience: document.getElementById('targetAudience').value.trim(),
        purpose: document.getElementById('purpose').value.trim(),
        channel_rules: document.getElementById('channelRules')?.value.trim() || ''
    };

    if (!fields.name) return alert(t('nameReq'));

    const uid = state.currentUser ? state.currentUser.user_id : 1;
    const isEdit = !!state.editingChannel;
    const url = isEdit ? `${API_URL}/channels/${state.editingChannel.id}` : `${API_URL}/create_channel`;

    const bodyParams = new URLSearchParams(fields);
    bodyParams.append('user_id', uid);

    try {
        const res = await fetch(url, {
            method: isEdit ? 'PUT' : 'POST',
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: bodyParams
        });

        const data = await res.json();
        if (res.ok) {
            state.isCreatingChannel = false;
            state.editingChannel = null;
            if (!isEdit) currentChannelId = data.channel_id;

            await loadChannels();
            if (typeof loadDashboard === 'function') await loadDashboard();

            alert(t('saved'));
            render();
        } else {
            alert(data.detail || t('error'));
        }
    } catch (e) {
        alert(t('connErr'));
    }
}

async function deleteChannel(id) {
    if (!confirm(t('delWarn'))) return;
    try {
        await fetch(`${API_URL}/channels/${id}`, { method: 'DELETE' });
        await loadChannels();
    } catch (e) { alert(t('error')); }
}

function startEditChannel(id) {
    const ch = state.channels.find(c => c.id === id);
    if (ch) { state.editingChannel = ch; state.isCreatingChannel = true; render(); }
}

// ── PDF EXPORT — with lang parameters (UPDATED) ──
function exportPDF() {
    if (!state.result || !state.result.analysis_id) return alert(t('error'));
    window.location.href = `${API_URL}/export_pdf/${state.result.analysis_id}?lang=${state.lang}`;
}

async function resendReportMail(analysisId) {
    const btn = document.getElementById('btnResendMail');
    if (!btn) return;

    btn.disabled = true;
    const oldText = btn.innerHTML;
    btn.innerHTML = `⏳ ${t('reportResending')}`;

    try {
        const res = await fetch(`${API_URL}/api/send_report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                analysis_id: analysisId,
                user_id: state.currentUser ? state.currentUser.user_id : 1,
                lang: state.lang
            })
        });
        const data = await res.json();
        if (data.success) {
            btn.innerHTML = `✅ ${t('reportSent')}`;
            btn.style.background = 'linear-gradient(90deg, #059669, #10b981)';
            setTimeout(() => {
                btn.innerHTML = oldText;
                btn.disabled = false;
            }, 3000);
        } else {
            alert(data.error || "Hata oluştu.");
            btn.innerHTML = oldText;
            btn.disabled = false;
        }
    } catch (e) {
        alert(t('connErr'));
        btn.innerHTML = oldText;
        btn.disabled = false;
    }
}

function exportChannelPDF(id) {
    window.location.href = `${API_URL}/export_channel_pdf/${id}?lang=${state.lang}`;
}

function renderChannelSelection() {
    return `
        <div class="main-container">
            <h1>${t('chListTitle')}</h1>
            <p class="subtitle">${t('chListSub')}</p>
            <div style="display:flex;flex-direction:column;gap:15px;">
                ${state.channels.map(ch => `
                    <div style="display:flex;align-items:center;justify-content:space-between;background:rgba(30,20,50,0.8);border:1px solid #6b21a8;border-radius:12px;padding:10px;">
                        <div style="flex:1;cursor:pointer;font-size:1.2rem;font-weight:bold;color:white;padding:10px;" onclick="selectChannel(${ch.id})">
                            📺 ${ch.name} <span style="font-size:0.9rem;color:#a855f7;">(${ch.content_type || 'Genel'})</span>
                        </div>
                        <div style="display:flex;gap:8px;">
                            <button onclick="exportChannelPDF(${ch.id})" style="background:#22c55e;border:none;padding:8px 12px;border-radius:6px;color:white;cursor:pointer;font-weight:bold;">${t('repBtn')}</button>
                            <button onclick="startEditChannel(${ch.id})" style="background:#f59e0b;border:none;padding:8px 12px;border-radius:6px;color:white;cursor:pointer;font-weight:bold;">${t('editBtn')}</button>
                            <button onclick="deleteChannel(${ch.id})" style="background:#ef4444;border:none;padding:8px 12px;border-radius:6px;color:white;cursor:pointer;font-weight:bold;">${t('delBtn')}</button>
                        </div>
                    </div>
                `).join('')}
                <button class="retry-btn" onclick="state.isCreatingChannel=true;render();" style="margin-top:15px;border-radius:12px;">
                    ${t('newChBtn')}
                </button>
            </div>
        </div>`;
}

function selectChannel(id) { currentChannelId = id; render(); }

// ═══════════════════════════════════════════════════════════
// ANALYSIS FORM
// ═══════════════════════════════════════════════════════════
function renderFormScreen() {
    const isShorts = state.mode === "shorts";
    const isPro = state.proMode;
    return `
        <div class="main-container">
            <h1>${t('formTitle')}</h1>
            <p class="subtitle">${t('formSub')}</p>
            <div style="display:flex;gap:12px;margin-bottom:20px;justify-content:center;">
                <button class="analyze-btn" style="flex:1;${!isShorts ? '' : 'opacity:0.6;background:linear-gradient(90deg,#6b21a8,#9333ea);'}" onclick="state.mode='long';render();">${t('longVid')}</button>
                <button class="analyze-btn" style="flex:1;${isShorts ? '' : 'opacity:0.6;background:linear-gradient(90deg,#6b21a8,#9333ea);'}" onclick="state.mode='shorts';render();">${t('shorts')}</button>
            </div>
            <div style="background:rgba(0,0,0,0.3);padding:15px;border-radius:10px;margin-bottom:20px;border:1px solid ${isPro ? '#f59e0b' : '#333'};cursor:pointer;" onclick="state.proMode=!state.proMode;render();">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <strong style="color:${isPro ? '#f59e0b' : 'white'};font-size:1.1rem;">${t('proMode')}</strong>
                    <span style="font-size:1.5rem;">${isPro ? '☑️' : '⬛'}</span>
                </div>
                <p style="font-size:0.85rem;margin-top:5px;color:#aaa;">${t('proDesc')}</p>
            </div>
            <div class="section-title">${t('fileIn')}</div>
            <label class="file-label">${t('vidLbl')}</label>
            
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <label for="video" style="background:linear-gradient(90deg,#7c3aed,#a855f7);color:white;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:0.9rem;font-weight:bold;white-space:nowrap;">
                    📁 ${state.lang==='en' ? 'Choose File' : state.lang==='es' ? 'Seleccionar' : 'Dosya Seç'}
                </label>
                <input type="file" id="video" accept="video/mp4" required style="display:none;" onchange="document.getElementById('video-name').textContent=this.files[0]?this.files[0].name:'${state.lang==='en' ? 'No file selected' : state.lang==='es' ? 'Ningún archivo' : 'Dosya seçilmedi'}'">
                <span id="video-name" style="color:#94a3b8;font-size:0.85rem;">${state.lang==='en' ? 'No file selected' : state.lang==='es' ? 'Ningún archivo seleccionado' : 'Dosya seçilmedi'}</span>
            </div>
            ${!isShorts ? `
            <label class="file-label">${t('thumbLbl')}</label>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <label for="thumb" style="background:linear-gradient(90deg,#7c3aed,#a855f7);color:white;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:0.9rem;font-weight:bold;white-space:nowrap;">
                    📁 ${state.lang==='en' ? 'Choose File' : state.lang==='es' ? 'Seleccionar' : 'Dosya Seç'}
                </label>
                <input type="file" id="thumb" accept="image/*" style="display:none;" onchange="document.getElementById('thumb-name').textContent=this.files[0]?this.files[0].name:'${state.lang==='en' ? 'No file selected' : state.lang==='es' ? 'Ningún archivo' : 'Dosya seçilmedi'}'">
                <span id="thumb-name" style="color:#94a3b8;font-size:0.85rem;">${state.lang==='en' ? 'No file selected' : state.lang==='es' ? 'Ningún archivo seleccionado' : 'Dosya seçilmedi'}</span>
            </div>` : ''}
            <label class="file-label">${t('csvLbl')}${isShorts ? (state.lang==='en' ? ' (optional)' : state.lang==='es' ? ' (opcional)' : ' (isteğe bağlı)') : ''}</label>
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:12px;">
                <label for="csv" style="background:linear-gradient(90deg,#7c3aed,#a855f7);color:white;padding:8px 16px;border-radius:8px;cursor:pointer;font-size:0.9rem;font-weight:bold;white-space:nowrap;">
                    📁 ${state.lang==='en' ? 'Choose File' : state.lang==='es' ? 'Seleccionar' : 'Dosya Seç'}
                </label>
                <input type="file" id="csv" accept=".csv" style="display:none;" onchange="document.getElementById('csv-name').textContent=this.files[0]?this.files[0].name:'${state.lang==='en' ? 'No file selected' : state.lang==='es' ? 'Ningún archivo' : 'Dosya seçilmedi'}'">
                <span id="csv-name" style="color:#94a3b8;font-size:0.85rem;">${state.lang==='en' ? 'No file selected' : state.lang==='es' ? 'Ningún archivo seleccionado' : 'Dosya seçilmedi'}</span>
            </div>
            <div class="section-title" style="margin-top:20px;">${t('compAna')}</div>
            <p style="font-size:0.85rem;color:#aaa;margin-top:-10px;margin-bottom:10px;">${t('compDesc')}</p>
            <input type="text" id="competitor_url" placeholder="${t('compPh')}">
            <div class="section-title">${t('seoInfo')}</div>
            <input type="text" id="title" placeholder="${t('titlePh')}">
            <textarea id="desc" placeholder="${t('descPh')}"></textarea>
            <input type="text" id="tags" placeholder="${t('tagsPh')}">
            <button class="analyze-btn" onclick="startAnalysis()">${isShorts ? t('startShorts') : t('startLong')}</button>
        </div>`;
}

// ═══════════════════════════════════════════════════════════
// LOADING & RESULT
// ═══════════════════════════════════════════════════════════
function renderLoadingScreen() {
    const analysisSteps = getAnalysisSteps();
    const stepsHTML = analysisSteps.map((step, index) => {
        const isActive = index === state.currentStep;
        const isCompleted = index < state.currentStep;
        const statusClass = isCompleted ? 'completed' : (isActive ? 'active' : '');
        const icon = isCompleted ? '✓' : (isActive ? '●' : '○');
        return `<div class="loading-step ${statusClass}"><div class="loading-step-icon">${icon}</div><span>${step.text}</span></div>`;
    }).join('');

    return `
        <div class="main-container">
            <div class="loading-container">
                <div class="loading-title">${state.proMode ? t('loadingPro') : t('loadingStd')}</div>
                <div class="progress-wrapper">
                    <div class="progress-bar-container">
                        <div id="progressBarFill" class="progress-bar" style="width:${state.progress}%"></div>
                    </div>
                    <div id="progressBarText" class="progress-text">%${Math.round(state.progress)} ${t('completedPerc')}</div>
                </div>
                <div id="loadingStepsList" class="loading-steps">${stepsHTML}</div>
            </div>
        </div>`;
}

function getVideoSpecificFeedback(res) {
    const ret = res.retention_data || {};
    const isEn = state.lang === 'en', isEs = state.lang === 'es';
    const tech = res.tech_data || {};
    const vTempo = res.visual_tempo || [];
    const aTempo = res.audio_tempo || [];
    const reasons = [], actions = [], positives = [];
    const langKey = `dynamic_feedback_${state.lang}`;
    const feedbackText = res[langKey] || res.dynamic_feedback;
    if (feedbackText) reasons.push(feedbackText);
    if (res.golden_frame_sec > 0) actions.push(isEn ? `🎬 GOLDEN FRAME: Highest visual tempo is at second ${res.golden_frame_sec}. You could use this frame for your thumbnail.` : isEs ? `🎬 FOTOGRAMA DORADO: El tempo visual más alto está en el segundo ${res.golden_frame_sec}. Podrías usar este fotograma para tu miniatura.` : `🎬 ALTIN KARE ÖNERİSİ: En yüksek görsel tempo ${res.golden_frame_sec}. saniyede. Thumbnail için bu kareyi kullanabilirsin.`);
    if (res.seo_score >= 8.5) positives.push(isEn ? `🔍 SEO IS PERFECT (${res.seo_score}/10): Title, description and tags are flawlessly aligned.` : isEs ? `🔍 SEO PERFECTO (${res.seo_score}/10): Título, descripción y etiquetas perfectamente alineados.` : `🔍 SEO BOMBA GİBİ (${res.seo_score}/10): Başlık, açıklama ve etiketler kusursuz uyumlu.`);
    else if (res.seo_score < 5.5) { reasons.push(isEn ? `🔍 WEAK SEO (${res.seo_score}/10).` : isEs ? `🔍 SEO DÉBIL (${res.seo_score}/10).` : `🔍 SEO ZAYIF (${res.seo_score}/10).`); actions.push(isEn ? `🔍 SEO SUGGESTION: You could place your title keywords in the first 200 characters of the description.` : isEs ? `🔍 SUGERENCIA SEO: Podrías colocar las palabras clave del título en los primeros 200 caracteres de la descripción.` : `🔍 SEO ÖNERİSİ: Açıklamanın ilk 200 karakterine başlık kelimelerini yerleştirebilirsin.`); }
    if (vTempo.length > 0 && vTempo[0] < 1.8) { reasons.push(isEn ? `Intro is visually static.` : isEs ? `La intro es visualmente estática.` : `Giriş görsel olarak durağan.`); actions.push(isEn ? `🎬 EDIT SUGGESTION: You could add a dynamic zoom or transition at 00:01.` : isEs ? `🎬 SUGERENCIA DE EDICIÓN: Podrías añadir un zoom dinámico o una transición en 00:01.` : `🎬 EDİT ÖNERİSİ: 00:01'e dinamik zoom veya geçiş ekleyebilirsin.`); }
    let deadZoneFound = false;
    vTempo.forEach((val, idx) => {
        if (!deadZoneFound && idx > 2 && val < 1.1 && (aTempo[idx] || 0) < 1.5) {
            reasons.push(isEn ? `Dead zone at second ${idx}.` : isEs ? `Zona muerta en el segundo ${idx}.` : `${idx}. saniyede ölü bölge.`);
            actions.push(isEn ? `🎬 CUT SUGGESTION: You could trim the scene between ${idx-1}-${idx+1}.` : isEs ? `🎬 SUGERENCIA DE CORTE: Podrías recortar la escena entre ${idx-1}-${idx+1}.` : `🎬 KESİM ÖNERİSİ: ${idx - 1}-${idx + 1} arası sahneyi kısaltabilirsin.`);
            deadZoneFound = true;
        }
    });
    if (res.coaching_mode === "PROACTIVE" && ret.worst_drop_sec > 0) {
        reasons.push(isEn ? `${ret.drop_percent}% audience loss at second ${ret.worst_drop_sec}.` : isEs ? `${ret.drop_percent}% pérdida de audiencia en el segundo ${ret.worst_drop_sec}.` : `${ret.worst_drop_sec}. saniyede %${ret.drop_percent} kitle kaybı.`);
        actions.push(isEn ? `📊 RETENTION SUGGESTION: You could replace this second with one of your most exciting frames.` : isEs ? `📊 SUGERENCIA DE RETENCIÓN: Podrías reemplazar este segundo con uno de tus fotogramas más emocionantes.` : `📊 RETENTION ÖNERİSİ: Bu saniyeyi videonun en heyecanlı karelerinden biriyle değiştirebilirsin.`);
    } else if (res.coaching_mode === "PREDICTIVE" && ret.score < 6.5) {
        reasons.push(isEn ? `Estimated retention is low.` : isEs ? `La retención estimada es baja.` : `Tahmini retention düşük.`);
        actions.push(isEn ? `📊 INTRO SUGGESTION: You could re-shoot the first 10 seconds.` : isEs ? `📊 SUGERENCIA DE INTRO: Podrías volver a grabar los primeros 10 segundos.` : `📊 GİRİŞ ÖNERİSİ: İlk 10 sn'yi baştan çekmeyi deneyebilirsin.`);
    }
    if (res.thumb_score !== null && res.thumb_score < 4.5) {
        reasons.push(isEn ? `Weak thumbnail (${res.thumb_score}/10).` : isEs ? `Miniatura débil (${res.thumb_score}/10).` : `Thumbnail zayıf (${res.thumb_score}/10).`);
        actions.push(isEn ? `📸 LIGHT SUGGESTION: You could increase the brightness and color saturation.` : isEs ? `📸 SUGERENCIA DE LUZ: Podrías aumentar el brillo y la saturación de color.` : `📸 IŞIK ÖNERİSİ: Parlaklık ve renk doygunluğunu artırabilirsin.`);
    } else if (res.thumb_score !== null && res.thumb_score >= 7.5) positives.push(isEn ? `📸 Strong thumbnail (${res.thumb_score}/10).` : isEs ? `📸 Miniatura fuerte (${res.thumb_score}/10).` : `📸 Thumbnail güçlü (${res.thumb_score}/10).`);
    if (res.tech_score < 7) {
        if (tech.max_gap > 8) { reasons.push(isEn ? `${tech.max_gap}s dead zone in video.` : isEs ? `Zona muerta de ${tech.max_gap}s en el video.` : `Videonda ${tech.max_gap} sn ölü bölge.`); actions.push(isEn ? `🎬 TEMPO SUGGESTION: You could cut this gap or fill it with effects.` : isEs ? `🎬 SUGERENCIA DE TEMPO: Podrías cortar este espacio o rellenarlo con efectos.` : `🎬 TEMPO ÖNERİSİ: Bu boşluğu kesebilir veya efektle doldurabilirsin.`); }
        if (tech.peaks < 8) { reasons.push(isEn ? `Only ${tech.peaks} peaks.` : isEs ? `Solo ${tech.peaks} picos.` : `Sadece ${tech.peaks} patlama.`); actions.push(isEn ? `⚡ PEAK SUGGESTION: You could add a cut/zoom/sound effect every 6-8 seconds.` : isEs ? `⚡ SUGERENCIA DE PICOS: Podrías añadir un corte/zoom/efecto de sonido cada 6-8 segundos.` : `⚡ PATLAMA ÖNERİSİ: Her 6-8 sn'ye cut/zoom/ses efekti ekleyebilirsin.`); }
    }
    if (res.retention_score >= 7.0) positives.push(isEn ? `Strong intro – retention ${res.retention_score}/10.` : isEs ? `Intro fuerte – retención ${res.retention_score}/10.` : `Giriş güçlü – retention ${res.retention_score}/10.`);
    if (res.tech_score >= 7.5) positives.push(isEn ? `Perfect tempo – ${tech.peaks} peaks.` : isEs ? `Tempo perfecto – ${tech.peaks} picos.` : `Tempo mükemmel – ${tech.peaks} patlama.`);

    let feedbackHTML = '';
    if (positives.length > 0) feedbackHTML += `<div style="margin:24px 0;padding:20px;background:rgba(34,197,94,0.15);border:1px solid #22c55e;border-radius:14px;line-height:1.6;"><strong style="color:#4ade80;font-size:1.15rem;">${t('strongPts')}</strong><br><br>${positives.map(p => `• ${p}`).join('<br><br>')}</div>`;
    if (reasons.length > 0) feedbackHTML += `<div style="margin:24px 0;padding:20px;background:rgba(220,38,38,0.12);border:1px solid #ef4444;border-radius:14px;line-height:1.6;"><strong style="color:#f87171;font-size:1.15rem;">${t('weakPts')}</strong><br><br>${reasons.map(r => `• ${r}`).join('<br><br>')}<br><br><strong style="color:#fbbf24;">${t('doThese')}</strong><ul style="margin-top:12px;padding-left:24px;line-height:1.7;">${actions.map(a => `<li>${a}</li>`).join('')}</ul></div>`;
    return feedbackHTML;
}

// ═══════════════════════════════════════════════════════════
// RESULT SCREEN
// ═══════════════════════════════════════════════════════════
function renderResultScreen() {
    const res = state.result;
    let warningClass = 'good';
    if (res.retention_score < 4) warningClass = 'critical';
    else if (res.overall_score < 7.5) warningClass = 'warning';
    const commentHTML = getVideoSpecificFeedback(res);

    if (!res || res.error) {
        return `
            <div class="main-container">
                <div class="score-card" style="border: 2px solid #ef4444; background: rgba(220, 38, 38, 0.1);">
                    <h2 style="color: #ef4444;">⚠️ Analiz Başarısız</h2>
                    <p style="color: #fca5a5; margin-top: 10px;">Sunucu tarafında bir hata oluştu:</p>
                    <code style="display: block; background: #000; padding: 15px; border-radius: 8px; margin-top: 10px; color: #ff7b72; font-family: monospace;">
                        ${escapeHTML(res ? res.error : 'Sunucudan yanıt alınamadı')}
                    </code>
                    <button class="retry-btn" style="margin-top: 20px;" onclick="reset()">🔄 Geri Dön ve Tekrar Dene</button>
                </div>
            </div>
        `;
    }

    const isShorts = res.is_shorts_mode === true;

    let gridItems = `
        <div class="detail-item"><span class="detail-item-label tt" data-tip="${tip('retention')}">${t('retScore')} <span class="tt-icon">?</span></span><div class="detail-item-value">${res.retention_score}/10</div></div>
        <div class="detail-item"><span class="detail-item-label tt" data-tip="${tip('techTempo')}">${t('techTempo')} <span class="tt-icon">?</span></span><div class="detail-item-value">${res.tech_score}/10</div></div>
        <div class="detail-item"><span class="detail-item-label tt" data-tip="${tip('seoPower')}">${t('seoPower')} <span class="tt-icon">?</span></span><div class="detail-item-value">${res.seo_score}/10</div></div>
        <div class="detail-item"><span class="detail-item-label tt" data-tip="${tip('peakCount')}">${t('peakCount')} <span class="tt-icon">?</span></span><div class="detail-item-value">${res.peaks}</div></div>`;
    if (!isShorts) gridItems = `<div class="detail-item"><span class="detail-item-label tt" data-tip="${tip('thumbQual')}">${t('thumbQual')} <span class="tt-icon">?</span></span><div class="detail-item-value">${res.thumb_score}/10</div></div>` + gridItems;

    let shortsHTML = '';
    if (res.viral_segments && res.viral_segments.length > 0) {
        const hasTimeline = state.clientCombined && state.clientCombined.length > 0;
        const timelineHTML = hasTimeline ? `
            <div style="margin-bottom:16px;">
                <div style="font-size:0.8rem;color:#94a3b8;margin-bottom:6px;text-transform:uppercase;letter-spacing:1px;">⚡ Enerji Zaman Çizelgesi</div>
                <div id="viral-timeline-wrap" style="position:relative;border-radius:10px;overflow:hidden;background:#0a1224;cursor:pointer;"
                     onclick="handleTimelineCanvasClick(event)">
                    <canvas id="viral-timeline-canvas" style="display:block;width:100%;height:90px;"></canvas>
                </div>
            </div>` : '';

        const segmentsHTML = res.viral_segments.map((seg, idx) => {
        const scorePercent = seg.score > 1 ? Math.round(seg.score) : Math.round((seg.score || 0) * 100);
        const thumbHTML = seg.thumbnail
            ? `<img src="${seg.thumbnail}" alt="Kare ${idx + 1}" style="width:100%;height:100%;object-fit:cover;border-radius:8px 8px 0 0;">`
            : `<div style="width:100%;height:100%;display:flex;align-items:center;justify-content:center;color:#6b7280;font-size:2rem;">🎬</div>`;
        return `
        <div class="ai-idea-card" style="margin-bottom:14px;padding:0;overflow:hidden;">
            <div style="position:relative;aspect-ratio:16/9;background:#000;">
                ${thumbHTML}
                <div style="position:absolute;top:.5rem;left:.5rem;background:linear-gradient(135deg,#9333ea,#db2777);color:#fff;
                    font-weight:700;font-size:.7rem;padding:.2rem .6rem;border-radius:8px;display:flex;align-items:center;gap:.3rem;">
                    🔥 #${seg.rank || (idx + 1)}
                </div>
                <div style="position:absolute;bottom:.5rem;right:.5rem;background:rgba(0,0,0,.8);color:#fff;
                    font-family:'Courier New',monospace;font-size:.72rem;padding:.2rem .5rem;border-radius:6px;">
                    ${poeFormatTime(seg.start_sec)} — ${poeFormatTime(seg.end_sec)}
                </div>
            </div>
            <div style="padding:14px;">
                <div style="height:3px;background:rgba(255,255,255,.1);border-radius:2px;margin-bottom:10px;overflow:hidden;">
                    <div style="height:100%;border-radius:2px;background:linear-gradient(90deg,#a855f7,#ec4899);width:${Math.min(100, scorePercent)}%"></div>
                </div>
                <div style="display:flex;align-items:center;justify-content:space-between;margin-bottom:10px;flex-wrap:wrap;gap:6px;">
                    <span class="velocity-badge">⏱️ ${seg.suggested_duration}s · ${t('peak_label')}: ${poeFormatTime(seg.peakTime || seg.start_sec)}</span>
                    <span class="velocity-badge outlier tt" data-tip="${tip('energy')}">${scorePercent}% ${t('energy_label')} <span class="tt-icon">?</span></span>
                </div>
                <div style="display:flex; gap:8px;">
                    <button class="create-short-btn" style="background: #eab308; color: #000; flex:0.4;"
                            onclick="previewClip(${seg.start_sec}, ${seg.end_sec})">
                        ${t('preview')}
                    </button>
                    <button class="create-short-btn" id="short-btn-${idx}" style="flex:1;"
                        onclick="createShortFromMoment(${idx}, this)"
                        ${!res.ffmpeg_available ? 'disabled' : ''}>
                        ${res.ffmpeg_available ? '✂️ ' + t('extract_clip') : t('ffmpegReq')}
                    </button>
                </div>
            </div>
        </div>`;
    }).join('');

        const manualCutHTML = res.ffmpeg_available ? `
            <div id="manualCutBox" style="margin-top:18px;background:rgba(139,92,246,0.1);border:1px dashed #7c3aed;border-radius:10px;padding:14px 16px;">
                <div style="color:#c4b5fd;font-weight:bold;margin-bottom:10px;font-size:0.95rem;">${t('manualCut')}</div>
                <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap;">
                    <label style="color:#e2e8f0;font-size:0.88rem;">${t('start')}</label>
                    <input id="manualStart" type="text" placeholder="1:08" style="width:90px;background:#1e1b4b;border:1px solid #6d28d9;color:white;padding:6px 8px;border-radius:6px;font-size:0.9rem;"/>
                    <label style="color:#e2e8f0;font-size:0.88rem;">${t('end')}</label>
                    <input id="manualEnd" type="text" placeholder="1:19" style="width:90px;background:#1e1b4b;border:1px solid #6d28d9;color:white;padding:6px 8px;border-radius:6px;font-size:0.9rem;"/>
                    <button id="manualCutBtn" onclick="createManualShort(this)" style="background:linear-gradient(90deg,#7c3aed,#a855f7);border:none;color:white;padding:7px 18px;border-radius:7px;font-weight:bold;cursor:pointer;font-size:0.9rem;">${t('cutDl')}</button>
                </div>
                <div style="color:#9ca3af;font-size:0.78rem;margin-top:7px;">${t('cutTip')}</div>
            </div>` : '';

        shortsHTML = `<div class="viral-box">
            <div class="viral-box-title" style="color:#22c55e;">${t('dynScenes')}</div>
            <div class="viral-box-subtitle">${t('dynDesc')}</div>
            ${timelineHTML}
            ${segmentsHTML}
            ${manualCutHTML}
        </div>`;
    }

    const videoModalHTML = `
        <div id="videoModal" style="display:none;position:fixed;inset:0;z-index:9999;background:rgba(0,0,0,0.92);align-items:center;justify-content:center;flex-direction:column;gap:16px;">
            <button onclick="closeVideoModal()" style="position:absolute;top:18px;right:22px;background:#ef4444;border:none;color:white;font-size:1.4rem;font-weight:bold;border-radius:50%;width:44px;height:44px;cursor:pointer;z-index:10000;">✕</button>
            <p style="color:#a855f7;font-weight:bold;font-size:1rem;margin:0;">${t('clipPrev')}</p>
            <video id="modalVideo" style="max-width:90vw;max-height:78vh;border-radius:12px;border:2px solid #6b21a8;background:#000;" controls controlslist="nofullscreen nodownload" disablepictureinpicture></video>
            <a id="modalDownloadBtn" href="#" download style="background:linear-gradient(90deg,#16a34a,#22c55e);color:white;padding:10px 28px;border-radius:8px;font-weight:bold;font-size:1rem;text-decoration:none;">${t('dlPc')}</a>
        </div>`;

    const comp = res.competitor_data;
    let compHTML = '';
    const myVideoHTML = state.videoFile ? `
            <div style="margin-top:16px;background:rgba(0,0,0,0.4);border:1px solid rgba(168,85,247,0.3);border-radius:10px;overflow:hidden;">
                <div style="padding:8px 12px;font-size:0.78rem;color:#a78bfa;font-weight:bold;background:rgba(168,85,247,0.1);display:flex;align-items:center;gap:6px;">
                    🎬 ${t('you')} — ${res.title || 'Videon'}
                    <span style="font-size:0.7rem;color:#6b7280;font-weight:normal;">(Manuel kesme için saniyeleri buradan takip et)</span>
                </div>
                <video id="reference-player"
                    src="${getVideoObjectURL()}"
                    style="width:100%;max-height:220px;background:#000;display:block;"
                    controls
                    controlslist="nodownload"
                    disablepictureinpicture>
                </video>
            </div>` : '';

    if (comp) {
        const killSwitchHTML = res.kill_switch_active ? `<div style="background:rgba(239,68,68,0.15);border:2px solid #ef4444;padding:14px 18px;border-radius:10px;margin-top:12px;"><strong style="color:#ef4444;">${t('killSwitchWarn')}</strong><br><span style="color:#fca5a5;font-size:0.9rem;">${t('killSwitchDesc')}</span></div>` : `<div style="text-align:center;margin-top:12px;font-size:0.95rem;color:#e2e8f0;background:rgba(0,0,0,0.3);padding:10px;border-radius:8px;">🎯 <em>${t('aiScanned')}</em></div>`;

        compHTML = `
            <div style="background:linear-gradient(135deg,#1e1b4b,#312e81);border:2px solid #6366f1;padding:20px;border-radius:12px;margin-top:25px;box-shadow:0 4px 15px rgba(99,102,241,0.3);">
                <div style="text-align:center;margin-bottom:15px;">
                    <span class="tt" data-tip="${state.lang==='en' ? 'AI found your competitor and analyzed their tags, title strategy and engagement. Check the PDF for full details.' : state.lang==='es' ? 'La IA encontró a tu competidor y analizó sus etiquetas, estrategia de título e interacción. Consulta el PDF para más detalles.' : 'AI rakibini buldu ve etiketlerini, başlık stratejisini ve etkileşimini analiz etti. Tam detaylar için PDF\'i incele.'}" style="background:#ef4444;color:white;padding:5px 15px;border-radius:20px;font-weight:bold;font-size:0.9rem;cursor:help;">
                        ${t('compActive')} <span class="tt-icon">?</span>
                    </span>
                </div>
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div style="flex:1;text-align:center;"><div style="font-size:2.5rem;margin-bottom:5px;">😎</div><strong style="color:#a855f7;font-size:1.1rem;">${t('you')}</strong></div>
                    <div style="font-size:2.5rem;font-weight:900;color:#f59e0b;font-style:italic;">VS</div>
                    <div style="flex:1;text-align:center;"><div style="font-size:2.5rem;margin-bottom:5px;">🥷</div><strong style="color:#ef4444;font-size:1.1rem;">${(comp.channel || '').toUpperCase()}</strong><div style="font-size:0.8rem;color:#aaa;margin-top:3px;">🔥 ${(comp.views || 0).toLocaleString()} ${t('compViews')}</div></div>
                </div>
                ${killSwitchHTML}
                ${myVideoHTML}
            </div>`;
    } else {
        // No rival attached: say so plainly instead of inventing a comparison.
        // The analysis itself is complete, so this is a note, not an error.
        const noCompKey = res.competitor_status === 'manual_url_failed' ? 'compUrlFailed'
            : res.competitor_status === 'lookup_failed' ? 'compLookupFailed'
            : 'compNoMatch';
        compHTML = `
            <div style="background:rgba(30,27,75,0.6);border:1px solid rgba(99,102,241,0.45);padding:18px 20px;border-radius:12px;margin-top:25px;">
                <div style="font-weight:bold;color:#a5b4fc;font-size:1rem;margin-bottom:6px;">🔍 ${t('compSkipped')}</div>
                <div style="color:#cbd5e1;font-size:0.9rem;line-height:1.5;">${t(noCompKey)}</div>
                ${myVideoHTML}
            </div>`;
    }

    // Email Notification HTML
    let emailBoxHTML = '';
    if (res.user_has_email) {
        emailBoxHTML = `
            <div class="email-notification">
                <div class="email-icon">📧</div>
                <div class="email-text">
                    ${res.email_sent ? t('reportSent') : "Rapor oluşturuldu. PDF'i buradan indirebilirsiniz."}
                </div>
                <button class="email-resend-btn" id="btnResendMail" onclick="resendReportMail(${res.analysis_id})">
                    ${t('reportResend')}
                </button>
            </div>
        `;
    }

    // System Caps Badge HTML
    let sysCapsHTML = '';
    if (res.system_caps) {
        const caps = res.system_caps;
        const gpuTxt = caps.gpu_codec !== "libx264" ? `GPU: ${caps.gpu_codec}` : `CPU: ${caps.cpu_cores} Çekirdek`;
        sysCapsHTML = `
            <div style="text-align:center; margin-top:15px; margin-bottom:5px;">
                <div class="system-badge" title="${t('sysProfile')}">
                    🖥️ ${gpuTxt} • RAM: ${caps.ram_gb > 0 ? caps.ram_gb + 'GB' : '?'} • ⚡ ${caps.fast_mode ? 'Fast Mode' : 'Normal'}
                </div>
            </div>
        `;
    }

    return `
        ${videoModalHTML}
        <div class="main-container">
            <div class="result-container">
                <div class="score-card">
                    <h2>📊 ${t('resScoreTitle')}</h2>
                    <div class="big-score">${res.overall_score}</div>
                    <div class="warning-box ${warningClass}">${t('critical_warn_fmt').replace('{ret}', res.retention_score).replace('{tech}', res.tech_score).replace('{peaks}', res.peaks)}</div>
                </div>
                <div class="results-grid">${gridItems}</div>
                ${commentHTML}
                ${compHTML}
                ${shortsHTML}
                ${emailBoxHTML}
                <button class="analyze-btn" style="margin-top:20px;width:100%;" onclick="exportPDF()">${t('pdfBtn')}</button>
                ${sysCapsHTML}
                <button class="retry-btn" onclick="reset()">${t('newAnaBtn')}</button>
            </div>
        </div>`;
}

// ── VIDEO MODAL ──
function openVideoModal(downloadUrl) {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('modalVideo');
    const dlBtn = document.getElementById('modalDownloadBtn');
    if (!modal || !video) return;
    video.src = downloadUrl;
    if (dlBtn) { dlBtn.href = downloadUrl; dlBtn.style.display = 'inline-block'; }
    modal.style.display = 'flex';
    video.play().catch(() => { });
}

function previewClip(startSec, endSec) {
    if (!state.videoFile) return alert("Önizleme için video dosyası bulunamadı!");
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('modalVideo');
    const dlBtn = document.getElementById('modalDownloadBtn');
    if (!modal || !video) return;
    if (dlBtn) dlBtn.style.display = 'none';
    video.src = getVideoObjectURL();
    modal.style.display = 'flex';
    video.currentTime = startSec;
    video.play().catch(() => { });
    const stopPreview = () => {
        if (video.currentTime >= endSec) { video.pause(); video.removeEventListener('timeupdate', stopPreview); }
    };
    video.addEventListener('timeupdate', stopPreview);
}

function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('modalVideo');
    if (video) { video.pause(); video.src = ''; }
    if (modal) modal.style.display = 'none';
}

document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeVideoModal(); });

function playAnalysisCompleteSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        function playTone(freq, startTime, duration, gainVal, type = 'sine') {
            const osc = ctx.createOscillator(), gain = ctx.createGain();
            osc.connect(gain); gain.connect(ctx.destination);
            osc.type = type;
            osc.frequency.setValueAtTime(freq, ctx.currentTime + startTime);
            osc.frequency.linearRampToValueAtTime(freq * 1.06, ctx.currentTime + startTime + duration * 0.6);
            gain.gain.setValueAtTime(0, ctx.currentTime + startTime);
            gain.gain.linearRampToValueAtTime(gainVal, ctx.currentTime + startTime + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + startTime + duration);
            osc.start(ctx.currentTime + startTime); osc.stop(ctx.currentTime + startTime + duration + 0.05);
        }
        playTone(520, 0.00, 0.18, 0.35); playTone(660, 0.14, 0.20, 0.45); playTone(880, 0.26, 0.30, 0.55);
        playTone(1760, 0.26, 0.25, 0.15, 'triangle');
        setTimeout(() => ctx.close(), 1200);
    } catch (e) { }
}

let progressIntervalId = null;
function startProgressBar() {
    if (progressIntervalId) clearInterval(progressIntervalId);
    progressIntervalId = null;
    state.progress = 0; state.currentStep = 0;
    const analysisSteps = getAnalysisSteps();
    const totalSteps = analysisSteps.length;
    const INTERVAL_MS = 300;
    const FAST_STEP = state.proMode ? 0.71 : 0.38;
    const SLOW_STEP = 0.04;
    const BRAKE_POINT = 95;
    progressIntervalId = setInterval(() => {
        if (!state.loading) { clearInterval(progressIntervalId); progressIntervalId = null; return; }
        const step = state.progress < BRAKE_POINT ? FAST_STEP : SLOW_STEP;
        state.progress = Math.min(99, state.progress + step);
        state.currentStep = Math.min(totalSteps - 2, Math.floor((state.progress / 99) * (totalSteps - 1)));
        const fill = document.getElementById('progressBarFill');
        const text = document.getElementById('progressBarText');
        const list = document.getElementById('loadingStepsList');
        if (fill && text && list) {
            fill.style.width = state.progress + '%';
            text.textContent = '%' + Math.round(state.progress) + ' ' + t('completedPerc');
            const items = list.querySelectorAll('.loading-step');
            items.forEach((el, i) => {
                const isActive = i === state.currentStep, isCompleted = i < state.currentStep;
                const newClass = 'loading-step ' + (isCompleted ? 'completed' : isActive ? 'active' : '');
                const newIcon = isCompleted ? '✓' : isActive ? '●' : '○';
                if (el.className !== newClass) el.className = newClass;
                const iconEl = el.querySelector('.loading-step-icon');
                if (iconEl && iconEl.textContent !== newIcon) iconEl.textContent = newIcon;
            });
        } else { render(); }
    }, INTERVAL_MS);
}

function finishProgressBar() {
    if (progressIntervalId) { clearInterval(progressIntervalId); progressIntervalId = null; }
    state.progress = 100; state.currentStep = getAnalysisSteps().length - 1;
    // completion animation
    const fill = document.getElementById('progressBarFill');
    const text = document.getElementById('progressBarText');
    if (fill) {
        fill.style.width = '100%';
        fill.classList.add('completed');
    }
    if (text) {
        text.classList.add('completed');
        text.textContent = `✅ %100 ${t('completedPerc')}`;
    }
    render();
    setTimeout(playAnalysisCompleteSound, 80);
}

// ═══════════════════════════════════════════════════════════
// POE ANALYSIS ENGINE — CLIENT-SIDE
// ═══════════════════════════════════════════════════════════
async function poeAnalyzeAudio(file) {
    try {
        const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
        const arrayBuf = await file.arrayBuffer();
        const audioBuf = await audioCtx.decodeAudioData(arrayBuf);
        const data = audioBuf.getChannelData(0);
        const sr = audioBuf.sampleRate;
        const windowSize = Math.floor(sr * 0.5);
        const energy = [];
        for (let i = 0; i < data.length; i += windowSize) {
            let sum = 0;
            const end = Math.min(i + windowSize, data.length);
            for (let j = i; j < end; j++) sum += data[j] * data[j];
            energy.push(Math.sqrt(sum / (end - i)));
        }
        audioCtx.close();
        return energy;
    } catch (_e) { return []; }
}

async function poeAnalyzeVisual(vid, duration, interval, onProgress) {
    const cvs = document.createElement('canvas');
    cvs.width = 160; cvs.height = 90;
    const ctx = cvs.getContext('2d', { willReadFrequently: true });
    const totalFrames = Math.floor(duration / interval);
    const changes = [];
    let prevData = null;
    for (let i = 0; i <= totalFrames; i++) {
        const t = Math.min(i * interval, duration - 0.01);
        vid.currentTime = t;
        await new Promise(r => { vid.onseeked = r; });
        ctx.drawImage(vid, 0, 0, 160, 90);
        const imgData = ctx.getImageData(0, 0, 160, 90).data;
        if (prevData) {
            let diff = 0;
            for (let j = 0; j < imgData.length; j += 16) {
                diff += Math.abs(imgData[j] - prevData[j]) +
                    Math.abs(imgData[j + 1] - prevData[j + 1]) +
                    Math.abs(imgData[j + 2] - prevData[j + 2]);
            }
            changes.push(diff / (160 * 90 * 3 / 16));
        } else { changes.push(0); }
        prevData = new Uint8ClampedArray(imgData);
        if (onProgress) onProgress(i / totalFrames);
    }
    return changes;
}

function poeNormalize(arr) {
    if (!arr.length) return [];
    const mx = Math.max(...arr);
    return mx === 0 ? arr.map(() => 0) : arr.map(v => v / mx);
}

function poeCombineScores(audio, visual) {
    const aN = poeNormalize(audio);
    const vN = poeNormalize(visual);
    const len = Math.max(aN.length, vN.length);
    const combined = [];
    for (let i = 0; i < len; i++) {
        const a = i < aN.length ? aN[i] : 0;
        const v = i < vN.length ? vN[i] : 0;
        const hasAudio = audio.length > 0;
        combined.push(hasAudio ? 0.55 * a + 0.45 * v : v);
    }
    return combined;
}

async function poeGenerateThumbnail(vid, time, duration) {
    vid.currentTime = Math.min(time, duration - 0.01);
    await new Promise(r => { vid.onseeked = r; });
    const cvs = document.createElement('canvas');
    cvs.width = 640; cvs.height = 360;
    const ctx = cvs.getContext('2d');
    ctx.drawImage(vid, 0, 0, 640, 360);
    return cvs.toDataURL('image/jpeg', 0.8);
}

function poeFormatTime(s) {
    const m = Math.floor(s / 60);
    const sec = Math.floor(s % 60);
    return String(m).padStart(2, '0') + ':' + String(sec).padStart(2, '0');
}

function drawViralTimeline(canvasId, combined, moments, duration, currentTime) {
    const canvas = document.getElementById(canvasId);
    if (!canvas || !combined.length) return;
    const wrap = canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    const w = wrap.clientWidth || 700;
    const h = 90;
    canvas.width = w * dpr; canvas.height = h * dpr;
    canvas.style.width = w + 'px'; canvas.style.height = h + 'px';
    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.fillStyle = '#0a1224'; ctx.fillRect(0, 0, w, h);
    const maxH = h * 0.42;
    ctx.beginPath();
    combined.forEach((s, i) => {
        const x = (i / combined.length) * w, bh = s * maxH;
        if (i === 0) ctx.moveTo(x, h / 2 - bh); else ctx.lineTo(x, h / 2 - bh);
    });
    for (let i = combined.length - 1; i >= 0; i--) {
        const x = (i / combined.length) * w, bh = combined[i] * maxH;
        ctx.lineTo(x, h / 2 + bh);
    }
    ctx.closePath();
    const grad = ctx.createLinearGradient(0, 0, 0, h);
    grad.addColorStop(0, 'rgba(168,85,247,.45)'); grad.addColorStop(0.5, 'rgba(168,85,247,.08)'); grad.addColorStop(1, 'rgba(168,85,247,.45)');
    ctx.fillStyle = grad; ctx.fill();
    ctx.beginPath();
    combined.forEach((s, i) => {
        const x = (i / combined.length) * w, bh = s * maxH;
        if (i === 0) ctx.moveTo(x, h / 2 - bh); else ctx.lineTo(x, h / 2 - bh);
    });
    ctx.strokeStyle = 'rgba(168,85,247,.6)'; ctx.lineWidth = 1.5; ctx.stroke();
    if (moments && moments.length) {
        moments.forEach(m => {
            if (!duration) return;
            const x = (m.peakTime / duration) * w;
            const grd = ctx.createRadialGradient(x, h / 2, 0, x, h / 2, 28);
            grd.addColorStop(0, 'rgba(236,72,153,.35)'); grd.addColorStop(1, 'rgba(236,72,153,0)');
            ctx.fillStyle = grd; ctx.fillRect(x - 28, 0, 56, h);
            ctx.strokeStyle = '#ec4899'; ctx.lineWidth = 2;
            ctx.beginPath(); ctx.moveTo(x, 0); ctx.lineTo(x, h); ctx.stroke();
            ctx.beginPath(); ctx.arc(x, 7, 4, 0, Math.PI * 2); ctx.fillStyle = '#ec4899'; ctx.fill();
        });
    }
    if (duration > 0 && currentTime !== undefined) {
        const px = (currentTime / duration) * w;
        ctx.strokeStyle = 'rgba(255,255,255,0.7)'; ctx.lineWidth = 1.5; ctx.setLineDash([4, 3]);
        ctx.beginPath(); ctx.moveTo(px, 0); ctx.lineTo(px, h); ctx.stroke(); ctx.setLineDash([]);
    }
}

async function startAnalysis() {
    const videoInput = document.getElementById('video');
    const thumbInput = document.getElementById('thumb');
    const csvInput = document.getElementById('csv');
    const uid = state.currentUser ? state.currentUser.user_id : 1;

    if (!videoInput?.files?.[0]) { alert(t('selectVidWarn')); return; }

    state.videoFile = videoInput.files[0];

    const formData = new FormData();
    formData.append('video_file', videoInput.files[0]);
    if (thumbInput?.files[0]) formData.append('thumb_file', thumbInput.files[0]);
    if (csvInput?.files[0]) formData.append('csv_file', csvInput.files[0]);

    formData.append('title', document.getElementById('title')?.value || '');
    formData.append('description', document.getElementById('desc')?.value || '');
    formData.append('tags', document.getElementById('tags')?.value || '');
    formData.append('channel_id', currentChannelId);
    formData.append('pro_mode', state.proMode);
    formData.append('is_shorts', state.mode === 'shorts');
    formData.append('competitor_url', document.getElementById('competitor_url')?.value || '');
    formData.append('user_id', uid);
    formData.append('lang', state.lang);
    console.log('Gönderilen lang:', state.lang);
    console.log('lang gönderiliyor:', state.lang);

    state.loading = true;
    state.progress = 0;
    render();

    const xhr = new XMLHttpRequest();
    let processingInterval = null;

    xhr.upload.onprogress = (e) => {
        if (e.lengthComputable) { state.progress = (e.loaded / e.total) * 50; updateUIProgress(); }
    };

    xhr.upload.onload = () => {
        if (processingInterval) clearInterval(processingInterval);
        processingInterval = setInterval(() => {
            if (!state.loading || state.progress >= 99) { clearInterval(processingInterval); return; }
            state.progress += 0.2;
            updateUIProgress();
        }, 400);
    };

    xhr.onload = function () {
        if (processingInterval) clearInterval(processingInterval);
        if (xhr.status === 200) {
            const result = JSON.parse(xhr.responseText);
            state.result = result;
            state.tempVideoName = result.temp_video_name;
            state.progress = 100;
            updateUIProgress();
            setTimeout(() => { state.loading = false; render(); playAnalysisCompleteSound(); }, 600);
        } else {
            alert("Hata: " + xhr.statusText);
            state.loading = false; render();
        }
    };

    xhr.onerror = () => {
        if (processingInterval) clearInterval(processingInterval);
        alert(t('connErr')); state.loading = false; render();
    };

    xhr.open('POST', `${API_URL}/analyze`, true);
    xhr.send(formData);
}

function updateUIProgress() {
    const totalSteps = getAnalysisSteps().length;
    state.currentStep = Math.min(totalSteps - 2, Math.floor((state.progress / 100) * totalSteps));
    const fill = document.getElementById('progressBarFill');
    const text = document.getElementById('progressBarText');
    const list = document.getElementById('loadingStepsList');
    if (fill) {
        fill.style.width = state.progress + '%';
        if (state.progress >= 100) {
            fill.classList.add('completed');
        }
    }
    if (text) {
        if (state.progress >= 100) {
            text.classList.add('completed');
            text.textContent = `✅ %100 ${t('completedPerc')}`;
        } else {
            const statusLabel = t('loadingText');
            text.textContent = `%${Math.round(state.progress)} ${statusLabel}`;
        }
    }
    if (list) renderStepsOnly();
}

function renderStepsOnly() {
    const list = document.getElementById('loadingStepsList');
    if (!list) return;
    const analysisSteps = getAnalysisSteps();
    const stepsHTML = analysisSteps.map((step, index) => {
        const isActive = index === state.currentStep;
        const isCompleted = index < state.currentStep;
        const statusClass = isCompleted ? 'completed' : (isActive ? 'active' : '');
        const icon = isCompleted ? '✓' : (isActive ? '●' : '○');
        return `<div class="loading-step ${statusClass}"><div class="loading-step-icon">${icon}</div><span>${step.text}</span></div>`;
    }).join('');
    list.innerHTML = stepsHTML;
}

function parseTimeInput(val) {
    const s = String(val).trim();
    if (/^\d+\.\d{2}$/.test(s)) { const parts = s.split('.'); return parseInt(parts[0]) * 60 + parseInt(parts[1]); }
    if (s.includes(':')) { const parts = s.split(':'); return (parseFloat(parts[0]) || 0) * 60 + (parseFloat(parts[1]) || 0); }
    return parseFloat(s);
}

async function createManualShort(btn) {
    const startVal = parseTimeInput(document.getElementById('manualStart')?.value);
    const endVal = parseTimeInput(document.getElementById('manualEnd')?.value);
    if (isNaN(startVal) || isNaN(endVal)) { alert(t('error')); return; }
    if (endVal <= startVal) { alert(t('error')); return; }
    if (endVal - startVal > 180) { alert(t('error')); return; }
    const duration = Math.round((endVal - startVal) * 10) / 10;
    const tempFilename = state.tempVideoName || (state.result ? state.result.temp_video_name : null);
    if (!tempFilename && !state.videoFile) { alert("Video referansı bulunamadı. Lütfen sayfayı yenilemeden önce analiz yapın."); return; }
    const originalText = btn.textContent;
    btn.textContent = "⌛ İşleniyor..."; btn.disabled = true;

    const doFetch = async (useFile) => {
        const fd = new FormData();
        fd.append('start', startVal); fd.append('duration', duration);
        fd.append('aspect_ratio', '16:9'); fd.append('format', 'landscape');
        if (useFile) { fd.append('temp_filename', 'MISSING'); fd.append('video_file', state.videoFile); }
        else { fd.append('temp_filename', tempFilename); }
        const res = await fetch(`${API_URL}/create_short`, { method: 'POST', body: fd });
        return res.json();
    };

    try {
        let data = await doFetch(false);
        if (!data.success && data.error?.includes('bulunamadı') && state.videoFile) {
            btn.textContent = "📤 Dosya yükleniyor...";
            data = await doFetch(true);
        }
        if (data.success) {
            const timeLabel = (typeof poeFormatTime === 'function') ?
                `${poeFormatTime(startVal)}–${poeFormatTime(endVal)}` : `${startVal}s–${endVal}s`;
            btn.textContent = `✅ ${timeLabel}`;
            btn.style.background = 'linear-gradient(90deg,#16a34a,#22c55e)';
            btn.style.boxShadow = '0 0 10px rgba(34,197,94,0.5)';
            btn.disabled = false;
            btn.onclick = () => openVideoModal(data.download_url);
            openVideoModal(data.download_url);
            const si = document.getElementById('manualStart'), ei = document.getElementById('manualEnd');
            if (si) si.value = ''; if (ei) ei.value = '';
            const cutBox = document.getElementById('manualCutBox');
            if (cutBox) {
                const newBtn = document.createElement('button');
                newBtn.textContent = t('cutDl');
                newBtn.style.cssText = 'background:linear-gradient(90deg,#7c3aed,#a855f7);border:none;color:white;padding:7px 18px;border-radius:7px;font-weight:bold;cursor:pointer;font-size:0.9rem;margin-top:6px;';
                newBtn.onclick = () => createManualShort(newBtn);
                btn.insertAdjacentElement('afterend', newBtn);
            }
        } else { throw new Error(data.error || 'Bilinmeyen bir hata oluştu'); }
    } catch (error) {
        alert("Kesme Hatası: " + error.message);
        btn.textContent = originalText; btn.disabled = false;
        btn.onclick = () => createManualShort(btn);
    }
}

async function createShortFromMoment(segmentIndex, btn) {
    const res = state.result;
    const seg = res && res.viral_segments ? res.viral_segments[segmentIndex] : null;
    if (!seg) { alert(t('error')); return; }
    const startVal = seg.start_sec, endVal = seg.end_sec;
    const duration = Math.round((endVal - startVal) * 10) / 10;
    if (isNaN(startVal) || isNaN(endVal) || endVal <= startVal) { alert(t('error')); return; }
    const tempFilename = state.tempVideoName;
    if (!tempFilename && !state.videoFile) { alert(t('error')); return; }
    const originalText = btn.textContent;
    btn.textContent = t('wait'); btn.disabled = true;

    const doFetch = async (useFile) => {
        const fd = new FormData();
        fd.append('start', startVal); fd.append('duration', duration);
        if (useFile) { fd.append('temp_filename', 'MISSING'); fd.append('video_file', state.videoFile); }
        else { fd.append('temp_filename', tempFilename); }
        const res = await fetch(`${API_URL}/create_short`, { method: 'POST', body: fd });
        return res.json();
    };

    try {
        let data = await doFetch(!tempFilename);
        if (!data.success && data.error?.includes('bulunamadı') && state.videoFile) {
            btn.textContent = t('wait');
            data = await doFetch(true);
        }
        if (data.success) {
            btn.textContent = `✅ ${poeFormatTime(startVal)}–${poeFormatTime(endVal)}`;
            btn.style.background = 'linear-gradient(90deg,#16a34a,#22c55e)';
            btn.style.boxShadow = '0 0 10px rgba(34,197,94,0.5)';
            btn.disabled = false;
            btn.onclick = () => openVideoModal(data.download_url);
            openVideoModal(data.download_url);
        } else { throw new Error(data.error || 'Bilinmeyen hata'); }
    } catch (error) {
        alert(t('error') + ': ' + error.message);
        btn.textContent = originalText; btn.disabled = false;
        btn.onclick = () => createShortFromMoment(segmentIndex, btn);
    }
}

async function createShort(segmentIndex, btn) { return createShortFromMoment(segmentIndex, btn); }

function handleTimelineCanvasClick(e) {
    const wrap = e.currentTarget;
    if (!wrap || !state.clientVideoDuration) return;
    const rect = wrap.getBoundingClientRect();
    const pct = (e.clientX - rect.left) / rect.width;
    const seekTime = pct * state.clientVideoDuration;
    const mainVid = document.getElementById('__poe_analysis_video');
    if (mainVid) mainVid.currentTime = Math.max(0, Math.min(seekTime, state.clientVideoDuration - 0.01));
}

function reset() {
    revokeVideoObjectURL();
    state.result = null; state.loading = false; state.progress = 0;
    state.currentStep = 0; state.videoFile = null; state.tempVideoName = null;
    state.clientMoments = []; state.clientCombined = []; state.clientVideoDuration = 0;
    render();
}

// ═══════════════════════════════════════════════════════════
// GROQ CHATBOT
// ═══════════════════════════════════════════════════════════
let chatOpen = false, chatExpanded = false, chatSideOpen = false;
function getCoachWelcome() {
    if (state.lang === 'en') return '👋 Hello! I am your YouTube AI Coach. You can ask me anything about your video strategy, SEO or the algorithm.';
    if (state.lang === 'es') return '👋 ¡Hola! Soy tu Entrenador AI de YouTube. Puedes preguntarme cualquier cosa sobre tu estrategia de video, SEO o el algoritmo.';
    return '👋 Merhaba! Ben YouTube AI Koçun. Video stratejin, SEO veya algoritma hakkında soru sorabilirsin.';
}
let chatMessages = [{ sender: 'bot', text: getCoachWelcome() }];
let hasGroqKey = false, checkingKey = true;
let currentSessionId = null, chatSessions = [];

async function initChatbot() {
    try {
        const res = await fetch(`${API_URL}/api/settings/groq`);
        const data = await res.json();
        hasGroqKey = data.has_key;
    } catch (e) { console.error("Chatbot init hatası", e); }
    checkingKey = false;
    let container = document.getElementById('chatbot-container');
    if (!container) { container = document.createElement('div'); container.id = 'chatbot-container'; document.body.appendChild(container); }
    if (hasGroqKey) await loadChatSessions();
    renderChatbot();
}

async function loadChatSessions() {
    const uid = state.currentUser ? state.currentUser.user_id : 1;
    try { const res = await fetch(`${API_URL}/api/chat/sessions?user_id=${uid}`); chatSessions = await res.json(); }
    catch (e) { chatSessions = []; }
}

async function newChatSession() {
    const uid = state.currentUser ? state.currentUser.user_id : 1;
    try {
        const res = await fetch(`${API_URL}/api/chat/sessions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: 'Yeni Sohbet', user_id: uid }) });
        const data = await res.json();
        currentSessionId = data.id;
        const msgText = state.lang === 'en' ? '👋 New chat started. What would you like to ask?' : state.lang === 'es' ? '👋 Nueva conversación iniciada. ¿Qué quieres preguntar?' : '👋 Merhaba! Yeni sohbete başladık. Ne sormak istersin?';
        chatMessages = [{ sender: 'bot', text: msgText }];
        await fetch(`${API_URL}/api/chat/sessions/${currentSessionId}/messages`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sender: 'bot', text: msgText })
        });
        await loadChatSessions(); renderChatbot();
    } catch (e) { console.error("Yeni sohbet hatası", e); }
}

async function loadSession(id) {
    try {
        const res = await fetch(`${API_URL}/api/chat/sessions/${id}/messages`);
        const msgs = await res.json();
        currentSessionId = id;
        chatMessages = msgs.length > 0 ? msgs : [{ sender: 'bot', text: '👋 Bu sohbet boş. Bir şeyler sor!' }];
        chatSideOpen = false; renderChatbot();
    } catch (e) { console.error("Oturum yüklenemedi", e); }
}

async function deleteSession(id, e) {
    e.stopPropagation();
    if (!confirm(t('delWarn'))) return;
    try {
        await fetch(`${API_URL}/api/chat/sessions/${id}`, { method: 'DELETE' });
        if (currentSessionId === id) { currentSessionId = null; chatMessages = [{ sender: 'bot', text: '👋 Merhaba! Ben YouTube AI Koçun. Ne sormak istersin?' }]; }
        await loadChatSessions(); renderChatbot();
    } catch (e) { console.error("Sohbet silinemedi", e); }
}

async function saveMessageToSession(sender, text) {
    if (!currentSessionId) return;
    try {
        await fetch(`${API_URL}/api/chat/sessions/${currentSessionId}/messages`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ sender, text })
        });
        const userMsgs = chatMessages.filter(m => m.sender === 'user');
        if (sender === 'user' && userMsgs.length === 1) {
            const title = text.length > 45 ? text.substring(0, 42) + '...' : text;
            await fetch(`${API_URL}/api/chat/sessions/${currentSessionId}`, {
                method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title })
            });
            await loadChatSessions();
        }
    } catch (e) { }
}

function toggleChat() { chatOpen = !chatOpen; if (!chatOpen) { chatExpanded = false; chatSideOpen = false; } renderChatbot(); }
function toggleExpand() { chatExpanded = !chatExpanded; renderChatbot(); }
function toggleSide() { chatSideOpen = !chatSideOpen; renderChatbot(); }

let chatAttachedFile = null;

function handleChatFile(input) {
    const file = input.files[0];
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) { alert('Dosya en fazla 10MB olabilir.'); input.value = ''; return; }
    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result.split(',')[1];
        const isImage = file.type.startsWith('image/');
        chatAttachedFile = { type: isImage ? 'image' : 'text', base64, name: file.name, mimeType: file.type || 'application/octet-stream' };
        const preview = document.getElementById('chat-file-preview');
        const nameEl = document.getElementById('chat-file-name');
        if (preview && nameEl) { nameEl.textContent = (isImage ? '🖼️ ' : '📄 ') + file.name; preview.style.display = 'flex'; }
    };
    reader.readAsDataURL(file);
    input.value = '';
}





function removeChatFile() {
    chatAttachedFile = null;
    const preview = document.getElementById('chat-file-preview');
    if (preview) preview.style.display = 'none';
}

async function sendChat() {
    const input = document.getElementById('chatInput');
    const text = input ? input.value.trim() : '';
    if (!text && !chatAttachedFile) return;
    if (input) { input.value = ''; input.style.height = 'auto'; }

    const attachedFileSnapshot = chatAttachedFile ? { ...chatAttachedFile } : null;
    if (chatAttachedFile) removeChatFile();

    if (!currentSessionId) {
        try {
            const r = await fetch(`${API_URL}/api/chat/sessions`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title: 'Yeni Sohbet' }) });
            const d = await r.json(); currentSessionId = d.id; await loadChatSessions();
        } catch (e) { }
    }

    const userText = text || (attachedFileSnapshot ? (attachedFileSnapshot.type === 'image' ? '🖼️ ' + attachedFileSnapshot.name : '📄 ' + attachedFileSnapshot.name) : '');
    chatMessages.push({ sender: 'user', text: userText });
    saveMessageToSession('user', userText);
    chatMessages.push({ sender: 'bot', text: t('typing'), isTyping: true });
    renderChatbot();

    try {
        const res = await fetch(`${API_URL}/api/chat`, {
            method: 'POST', headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                history: chatMessages.slice(0, -1),
                channel_type: "Genel",
                analysis_context: state.result
                    ? `Video: ${state.result.title}. Puan: ${state.result.overall_score}/10. SEO: ${state.result.seo_score}. Patlama Sayısı: ${state.result.peaks}. Geri Bildirim: ${state.result.dynamic_feedback}`
                    : "",
                attached_file: attachedFileSnapshot ? {
                    type: attachedFileSnapshot.type,
                    base64: attachedFileSnapshot.base64,
                    mime_type: attachedFileSnapshot.mimeType,
                    name: attachedFileSnapshot.name
                } : null
            })
        });
        const data = await res.json();
        chatMessages.pop();
        if (data.error) {
            chatMessages.push({ sender: 'bot', text: `⚠️ ${data.details}` });
            if (data.error === 'INVALID_KEY') setTimeout(() => { hasGroqKey = false; renderChatbot(); }, 2500);
        } else {
            chatMessages.push({ sender: 'bot', text: data.reply });
            saveMessageToSession('bot', data.reply);
        }
    } catch (e) {
        chatMessages.pop();
        chatMessages.push({ sender: 'bot', text: `⚠️ ${t('error')}` });
    }
    renderChatbot();
    setTimeout(() => { const msgs = document.getElementById('chatMsgs'); if (msgs) msgs.scrollTop = msgs.scrollHeight; }, 50);
}

function chatKeyPress(e) { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); sendChat(); } }

function renderChatbot() {
    const container = document.getElementById('chatbot-container');
    if (!container || checkingKey) return;

    let bodyHTML = '';
    if (!hasGroqKey) {
        bodyHTML = `
            <div style="padding:18px;display:flex;flex-direction:column;gap:11px;height:calc(100% - 48px);justify-content:center;">
                <div style="text-align:center;font-size:2rem;">🤖</div>
                <div style="font-weight:bold;text-align:center;color:#f0abfc;font-size:1rem;">${t('aiCoachSetup')}</div>
                <div style="font-size:0.82rem;color:#c4b5fd;text-align:center;line-height:1.5;">${t('aiCoachSetupDesc')}</div>
                <div style="background:rgba(139,92,246,0.15);border:1px solid #7c3aed;border-radius:8px;padding:11px;font-size:0.8rem;color:#ddd;line-height:1.8;">
                    1️⃣ <a href="https://console.groq.com" target="_blank" style="color:#a78bfa;">console.groq.com</a>'a git<br/>
                    2️⃣ Google ile kayıt ol (ücretsiz)<br/>
                    3️⃣ <b>API Keys → Create API Key</b><br/>
                    4️⃣ Key'i kopyala, buraya yapıştır
                </div>
                <input type="text" id="groqKeyInput" placeholder="gsk_..." style="padding:9px;background:#1e1b4b;border:1px solid #6d28d9;color:white;border-radius:7px;font-size:0.85rem;outline:none;"/>
                <button id="saveKeyBtn" onclick="saveGroqKeySettings(event)" style="padding:10px;background:linear-gradient(90deg,#7c3aed,#ec4899);border:none;color:white;border-radius:7px;font-weight:bold;cursor:pointer;font-size:0.9rem;">${t('saveStartBtn')}</button>
            </div>`;
    } else {
        const formatMsg = (text) => text
            .replace(/</g, '&lt;').replace(/>/g, '&gt;')
            .replace(/\*\*(.*?)\*\*/g, '<b style="color:#f0abfc;">$1</b>')
            .replace(/\*(.*?)\*/g, '<i>$1</i>')
            .replace(/^[-•] /gm, '• ')
            .replace(/\n/g, '<br/>');

        const msgsHTML = chatMessages.map(m => `
            <div style="margin:4px 0;padding:9px 13px;border-radius:12px;font-size:0.84rem;line-height:1.6;max-width:88%;word-break:break-word;
                ${m.sender === 'user' ? 'background:linear-gradient(90deg,#7c3aed,#ec4899);margin-left:auto;border-bottom-right-radius:3px;' : 'background:rgba(255,255,255,0.09);margin-right:auto;border-bottom-left-radius:3px;'}">
                ${m.isTyping ? '<span style="letter-spacing:3px;opacity:0.7;">●●●</span>' : formatMsg(m.text)}
            </div>`).join('');

        const sessionsHTML = chatSessions.length > 0
            ? chatSessions.map(s => `
                <div onclick="loadSession(${s.id})" style="padding:8px 10px;border-radius:8px;cursor:pointer;font-size:0.8rem;display:flex;align-items:center;justify-content:space-between;gap:6px;background:${s.id === currentSessionId ? 'rgba(139,92,246,0.3)' : 'rgba(255,255,255,0.05)'};border:1px solid ${s.id === currentSessionId ? '#7c3aed' : 'transparent'};margin-bottom:4px;"
                    onmouseover="this.style.background='rgba(139,92,246,0.2)'" onmouseout="this.style.background='${s.id === currentSessionId ? 'rgba(139,92,246,0.3)' : 'rgba(255,255,255,0.05)'}'">
                    <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap;flex:1;color:#e2e8f0;">💬 ${s.title}</span>
                    <span onclick="deleteSession(${s.id},event)" style="color:#ef4444;font-size:0.9rem;flex-shrink:0;padding:2px 5px;border-radius:4px;" onmouseover="this.style.background='rgba(239,68,68,0.2)'" onmouseout="this.style.background='transparent'">🗑</span>
                </div>`).join('')
            : `<div style="color:#6b7280;font-size:0.8rem;text-align:center;padding:10px;">${t('emptyChat')}</div>`;

        const sidePanel = `
            <div style="position:absolute;top:0;left:0;bottom:0;width:${chatSideOpen ? '200px' : '0'};overflow:hidden;background:#0f0a1a;border-right:${chatSideOpen ? '1px solid #2d1b4e' : 'none'};transition:width 0.25s;display:flex;flex-direction:column;z-index:2;">
                ${chatSideOpen ? `
                <div style="padding:10px 10px 6px;font-size:0.78rem;font-weight:bold;color:#a78bfa;border-bottom:1px solid #2d1b4e;">${t('chatHist')}</div>
                <div style="flex:1;overflow-y:auto;padding:8px;">${sessionsHTML}</div>
                <div style="padding:8px;border-top:1px solid #2d1b4e;">
                    <button onclick="newChatSession()" style="width:100%;padding:7px;background:linear-gradient(90deg,#7c3aed,#ec4899);border:none;color:white;border-radius:7px;font-size:0.8rem;font-weight:bold;cursor:pointer;">${t('newChatBtn')}</button>
                </div>` : ''}
            </div>`;

        bodyHTML = `
            <div style="flex:1;display:flex;overflow:hidden;position:relative;">
                ${sidePanel}
                <div style="flex:1;display:flex;flex-direction:column;overflow:hidden;margin-left:${chatSideOpen ? '200px' : '0'};transition:margin-left 0.25s;">
                    <div id="chatMsgs" style="flex:1;overflow-y:auto;padding:10px 12px;display:flex;flex-direction:column;gap:3px;">${msgsHTML}</div>
                    <div style="padding:8px 10px;border-top:1px solid #2d1b4e;display:flex;flex-direction:column;gap:6px;">
                        <div id="chat-file-preview" style="display:none;padding:6px 10px;background:rgba(139,92,246,0.15);border:1px solid #7c3aed;border-radius:8px;font-size:0.78rem;color:#d8b4fe;align-items:center;justify-content:space-between;gap:8px;">
                            <span id="chat-file-name">📎 dosya</span>
                            <span onclick="removeChatFile()" style="cursor:pointer;color:#ef4444;font-size:1rem;">✕</span>
                        </div>
                        <div style="display:flex;gap:6px;align-items:flex-end;">
                            <label for="chatFileInput" style="cursor:pointer;padding:8px;background:rgba(139,92,246,0.2);border:1px solid #6d28d9;border-radius:8px;font-size:1rem;flex-shrink:0;height:36px;display:flex;align-items:center;" title="Görsel veya dosya ekle">📎</label>
                            <input type="file" id="chatFileInput" accept="image/*,.csv,.txt,.pdf" style="display:none;" onchange="handleChatFile(this)">
                            <textarea id="chatInput" placeholder="${t('chatPh')}"
                                onkeypress="chatKeyPress(event)" oninput="this.style.height='auto';this.style.height=Math.min(this.scrollHeight,100)+'px'" rows="1"
                                style="flex:1;padding:8px 10px;background:#1e1b4b;border:1px solid #6d28d9;color:white;border-radius:8px;font-size:0.85rem;resize:none;overflow-y:auto;max-height:100px;outline:none;font-family:inherit;line-height:1.4;"></textarea>
                            <button onclick="sendChat()" style="padding:8px 13px;background:linear-gradient(90deg,#7c3aed,#ec4899);border:none;color:white;border-radius:8px;cursor:pointer;font-size:1.1rem;flex-shrink:0;height:36px;">➤</button>
                        </div>
                    </div>
                </div>
            </div>`;
    }

    const normalStyle = `position:fixed;bottom:88px;right:24px;width:325px;height:460px;`;
    const expandedStyle = `position:fixed;top:50%;left:50%;transform:translate(-50%,-50%);width:min(660px,92vw);height:min(700px,88vh);`;

    container.innerHTML = `
        <div onclick="toggleChat()" style="position:fixed;bottom:24px;right:24px;width:52px;height:52px;background:linear-gradient(135deg,#7c3aed,#ec4899);border-radius:50%;cursor:pointer;display:flex;justify-content:center;align-items:center;font-size:22px;z-index:9999;box-shadow:0 4px 15px rgba(168,85,247,0.5);transition:transform 0.2s;" onmouseover="this.style.transform='scale(1.1)'" onmouseout="this.style.transform='scale(1)'">${chatOpen ? '✕' : '💬'}</div>
        <div style="${chatExpanded ? expandedStyle : normalStyle}background:#16101f;border:1px solid #4c1d95;border-radius:14px;${chatOpen ? 'display:flex;' : 'display:none;'}flex-direction:column;z-index:9998;color:white;overflow:hidden;box-shadow:0 8px 40px rgba(0,0,0,0.7);">
            <div style="padding:10px 12px;background:linear-gradient(90deg,#4c1d95,#831843);display:flex;justify-content:space-between;align-items:center;flex-shrink:0;">
                <div style="display:flex;align-items:center;gap:7px;">
                    ${hasGroqKey ? `<div onclick="event.stopPropagation();toggleSide()" title="Sohbet Geçmişi" style="cursor:pointer;background:rgba(255,255,255,0.18);border-radius:5px;padding:3px 8px;font-size:0.85rem;user-select:none;border:1px solid rgba(255,255,255,0.15);" onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.18)'">${chatSideOpen ? '✕' : '☰'}</div>` : ''}
                    <span style="font-weight:bold;font-size:0.88rem;">🤖 ${t('coachTitle')}</span>
                </div>
                <div style="display:flex;align-items:center;gap:5px;">
                    <span style="font-size:0.65rem;color:#f9a8d4;opacity:0.8;">Groq · Llama 3.3</span>
                    ${hasGroqKey ? `<div onclick="event.stopPropagation();newChatSession()" title="Yeni Sohbet" style="cursor:pointer;background:rgba(255,255,255,0.18);border-radius:5px;padding:3px 8px;font-size:0.8rem;user-select:none;border:1px solid rgba(255,255,255,0.15);" onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.18)'">✏️</div>` : ''}
                    <div onclick="event.stopPropagation();toggleExpand()" style="cursor:pointer;background:rgba(255,255,255,0.18);border-radius:5px;padding:3px 8px;font-size:0.8rem;user-select:none;border:1px solid rgba(255,255,255,0.15);" onmouseover="this.style.background='rgba(255,255,255,0.3)'" onmouseout="this.style.background='rgba(255,255,255,0.18)'">${chatExpanded ? '🗗' : '🗖'}</div>
                    <div onclick="event.stopPropagation();toggleChat()" style="cursor:pointer;background:rgba(239,68,68,0.3);border-radius:5px;padding:3px 8px;font-size:0.85rem;user-select:none;border:1px solid rgba(239,68,68,0.4);" onmouseover="this.style.background='rgba(239,68,68,0.6)'" onmouseout="this.style.background='rgba(239,68,68,0.3)'">✕</div>
                </div>
            </div>
            ${bodyHTML}
        </div>`;

     if (chatOpen && hasGroqKey) {
        setTimeout(() => {
            const msgs = document.getElementById('chatMsgs');
            if (msgs) msgs.scrollTop = msgs.scrollHeight;
            const inp = document.getElementById('chatInput');
            if (inp) inp.focus();
        }, 40);
    }
}   // ← renderChatbot function closes here

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🎬 YouTube Analiz Pro V4.0 — SaaS Edition başlatıldı');
    await loadTranslations();

    try {
        const sessRes = await fetch(`${API_URL}/api/session`);
        const sessData = await sessRes.json();
        if (sessData.session && sessData.session.user_id) {
            const s = sessData.session;
            if (s.username && s.username !== 'undefined' && s.username !== 'null') {
                state.currentUser = s;
            } else {
                try {
                    const pRes = await fetch(`${API_URL}/api/profile?user_id=${s.user_id}`);
                    const pData = await pRes.json();
                    if (pData.username) {
                        state.currentUser = { user_id: s.user_id, username: pData.username };
                        fetch(`${API_URL}/api/session`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(state.currentUser) }).catch(() => { });
                    } else {
                        state.currentUser = { user_id: s.user_id, username: 'User' };
                    }
                } catch (e) { state.currentUser = { user_id: s.user_id, username: 'User' }; }
            }
        }
    } catch (e) { }

    if (!state.currentUser) {
        try {
            let saved = localStorage.getItem('yt_user') || sessionStorage.getItem('yt_user');
            if (saved) {
                const parsed = JSON.parse(saved);
                if (parsed && parsed.user_id && parsed.username && parsed.username !== 'undefined') {
                    state.currentUser = parsed;
                    fetch(`${API_URL}/api/session`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: saved }).catch(() => { });
                }
            }
        } catch (e) { }
    }

    try {
        const groqRes = await fetch(`${API_URL}/api/settings/groq`);
        const groqData = await groqRes.json();
        if (groqData.has_key) state.groqKey = groqData.key || '(kayıtlı)';
    } catch (e) { }
    try {
        const gemRes = await fetch(`${API_URL}/api/settings/gemini`);
        const gemData = await gemRes.json();
        if (gemData.has_key) state.geminiKey = gemData.key || '(kayıtlı)';
    } catch (e) { }

    if (state.currentUser) { await loadChannels(); loadDashboard(); }

    render();
    await initChatbot();
});