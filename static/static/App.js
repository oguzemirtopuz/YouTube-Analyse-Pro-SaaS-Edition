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
    proMode: false
};

const analysisSteps = [
    { text: "📦 Video yükleniyor..." },
    { text: "🧠 AI Rakip Taraması & Sektör Verileri Çekiliyor..." },
    { text: "🎵 Ses ve Görsel Pikseller İşleniyor..." },
    { text: "📊 Retention hesaplanıyor..." },
    { text: "🔍 SEO değerlendiriliyor..." },
    { text: "🔥 Akıllı Viral potansiyel analiz ediliyor..." },
    { text: "✅ Sonuçlar hazırlanıyor..." }
];

async function loadChannels() {
    try {
        const res = await fetch(`${API_URL}/channels`);
        state.channels = await res.json();
        render();
    } catch (e) {
        console.error("Kanallar yüklenemedi", e);
    }
}

function goHome() {
    currentChannelId = null;
    state.isCreatingChannel = false;
    state.editingChannel = null;
    state.loading = false;
    state.result = null;
    state.progress = 0;
    state.videoFile = null;
    render();
}

function render() {
    const root = document.getElementById('root');
    if (!root) return;
    const homeBtnHTML = `<div style="position:fixed; top:20px; left:20px; cursor:pointer; background:linear-gradient(90deg, #6b21a8, #9333ea); padding:10px 15px; border-radius:8px; color:white; font-weight:bold; z-index:1000; box-shadow: 0 4px 6px rgba(0,0,0,0.3); border: 1px solid #c084fc;" onclick="goHome()">🏠 Ana Menü</div>`;
    if (state.isCreatingChannel) {
        root.innerHTML = homeBtnHTML + renderCreateChannel();
    } else if (currentChannelId === null) {
        if (state.channels.length > 0) {
            root.innerHTML = renderChannelSelection();
        } else {
            root.innerHTML = renderCreateChannel();
        }
    } else if (state.loading) {
        root.innerHTML = homeBtnHTML + renderLoadingScreen();
    } else if (state.result) {
        root.innerHTML = homeBtnHTML + renderResultScreen();
    } else {
        root.innerHTML = homeBtnHTML + renderFormScreen();
    }
}

function renderCreateChannel() {
    const isEdit = !!state.editingChannel;
    const ch = state.editingChannel || { name: '', content_type: '', target_audience: '', purpose: '' };
    return `
        <div class="main-container">
            <h1>${isEdit ? '✏️ Kanalı Düzenle' : '🎬 Yeni Kanal Profili Oluştur'}</h1>
            <p class="subtitle">AI Coach'un seni tanıması için kanal bilgilerini gir</p>
            <input type="text" id="channelName" placeholder="Kanal Adı (ör: BabaClutch)" value="${ch.name}">
            <input type="text" id="contentType" placeholder="İçerik Türü (Gaming, Vlog, Shorts vb.)" value="${ch.content_type || ''}">
            <input type="text" id="targetAudience" placeholder="Hedef Kitle (13-18 yaş erkek vb.)" value="${ch.target_audience || ''}">
            <textarea id="purpose" placeholder="Kanalın genel amacı / tarzı">${ch.purpose || ''}</textarea>
            <button class="analyze-btn" onclick="saveChannel()">
                ${isEdit ? '💾 Değişiklikleri Kaydet' : 'Hesap Oluştur ve Devam Et'}
            </button>
        </div>
    `;
}

async function saveChannel() {
    const name = document.getElementById('channelName').value.trim();
    const content_type = document.getElementById('contentType').value.trim();
    const target_audience = document.getElementById('targetAudience').value.trim();
    const purpose = document.getElementById('purpose').value.trim();
    if (!name) return alert("Kanal adı zorunlu!");
    const isEdit = !!state.editingChannel;
    const url = isEdit ? `${API_URL}/channels/${state.editingChannel.id}` : `${API_URL}/create_channel`;
    const method = isEdit ? 'PUT' : 'POST';
    try {
        const res = await fetch(url, {
            method: method,
            headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
            body: new URLSearchParams({ name, content_type, target_audience, purpose })
        });
        const data = await res.json();
        if (data.success || isEdit) {
            state.isCreatingChannel = false;
            state.editingChannel = null;
            if (!isEdit) currentChannelId = data.channel_id;
            await loadChannels();
        } else {
            alert(data.detail || data.error || "Hata oluştu");
        }
    } catch (e) {
        alert("İşlem başarısız!");
    }
}

async function deleteChannel(id) {
    if (!confirm("⚠️ DİKKAT! Bu kanalı ve ona ait tüm analiz geçmişini kalıcı olarak silmek istediğine emin misin?")) return;
    try {
        await fetch(`${API_URL}/channels/${id}`, { method: 'DELETE' });
        await loadChannels();
    } catch (e) {
        alert("Kanal silinemedi!");
    }
}

function startEditChannel(id) {
    const ch = state.channels.find(c => c.id === id);
    if (ch) {
        state.editingChannel = ch;
        state.isCreatingChannel = true;
        render();
    }
}

function exportChannelPDF(id) {
    window.location.href = `${API_URL}/export_channel_pdf/${id}`;
}

function renderChannelSelection() {
    return `
        <div class="main-container">
            <h1>🎬 Kanalların</h1>
            <p class="subtitle">Analiz yapmak istediğin kanalı seç veya yönet</p>
            <div style="display: flex; flex-direction: column; gap: 15px;">
                ${state.channels.map(ch => `
                    <div style="display:flex; align-items:center; justify-content:space-between; background:rgba(30,20,50,0.8); border:1px solid #6b21a8; border-radius:12px; padding:10px;">
                        <div style="flex:1; cursor:pointer; font-size:1.2rem; font-weight:bold; color:white; padding:10px;" onclick="selectChannel(${ch.id})">
                            📺 ${ch.name} <span style="font-size:0.9rem; color:#a855f7;">(${ch.content_type || 'Genel'})</span>
                        </div>
                        <div style="display:flex; gap:8px;">
                            <button onclick="exportChannelPDF(${ch.id})" style="background:#22c55e; border:none; padding:8px 12px; border-radius:6px; color:white; cursor:pointer; font-weight:bold;">📄 Rapor Al</button>
                            <button onclick="startEditChannel(${ch.id})" style="background:#f59e0b; border:none; padding:8px 12px; border-radius:6px; color:white; cursor:pointer; font-weight:bold;">✏️ Düzenle</button>
                            <button onclick="deleteChannel(${ch.id})" style="background:#ef4444; border:none; padding:8px 12px; border-radius:6px; color:white; cursor:pointer; font-weight:bold;">🗑️ Sil</button>
                        </div>
                    </div>
                `).join('')}
                <button class="retry-btn" onclick="state.isCreatingChannel = true; render();" style="margin-top:15px; border-radius:12px;">
                    ➕ Yeni Kanal Oluştur
                </button>
            </div>
        </div>
    `;
}

function selectChannel(id) {
    currentChannelId = id;
    render();
}

function renderFormScreen() {
    const isShorts = state.mode === "shorts";
    const isPro = state.proMode;
    return `
        <div class="main-container">
            <h1>🎬 YOUTUBE ANALİZ PRO V3.2</h1>
            <p class="subtitle">Video Performans, Gerçek Rakip Kıyaslama & Akıllı Viral Potansiyel</p>
            <div style="display:flex; gap:12px; margin-bottom:20px; justify-content:center;">
                <button class="analyze-btn" style="flex:1; ${!isShorts ? '' : 'opacity:0.6; background:linear-gradient(90deg,#6b21a8,#9333ea);'}"
                    onclick="state.mode='long'; render();">Uzun Video</button>
                <button class="analyze-btn" style="flex:1; ${isShorts ? '' : 'opacity:0.6; background:linear-gradient(90deg,#6b21a8,#9333ea);'}"
                    onclick="state.mode='shorts'; render();">Shorts</button>
            </div>
            <div style="background:rgba(0,0,0,0.3); padding:15px; border-radius:10px; margin-bottom:20px; border: 1px solid ${isPro ? '#f59e0b' : '#333'}; cursor:pointer;" onclick="state.proMode = !state.proMode; render();">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <strong style="color:${isPro ? '#f59e0b' : 'white'}; font-size:1.1rem;">🧠 Derin Analiz (Pro Mode)</strong>
                    <span style="font-size:1.5rem;">${isPro ? '☑️' : '⬛'}</span>
                </div>
                <p style="font-size:0.85rem; margin-top:5px; color:#aaa;">Bu özellik açıkken AI videoyu kare kare mikroskobik düzeyde inceler. İşlem daha uzun sürebilir ancak sonuçlar kusursuzdur.</p>
            </div>
            <div class="section-title">📁 Dosya Girişi</div>
            <label class="file-label">Video (.mp4) *</label>
            <input type="file" id="video" accept="video/mp4" required>
            ${!isShorts ? `
                <label class="file-label">Küçük Resim / Thumbnail</label>
                <input type="file" id="thumb" accept="image/*">
            ` : ''}
            <label class="file-label">Retention CSV (YouTube Analytics)${isShorts ? ' (isteğe bağlı)' : ''}</label>
            <input type="file" id="csv" accept=".csv">
            <div class="section-title" style="margin-top:20px;">🥊 Rakip Analizi (Opsiyonel)</div>
            <p style="font-size:0.85rem; color:#aaa; margin-top:-10px; margin-bottom:10px;">Boş bırakırsan Yapay Zeka senin için en dişli rakibi otomatik olarak bulur ve kıyaslar.</p>
            <input type="text" id="competitor_url" placeholder="Rakip Video Linki (örn: youtube.com/watch?v=...)">
            <div class="section-title">✏️ SEO Bilgileri</div>
            <input type="text" id="title" placeholder="Video Başlığı">
            <textarea id="desc" placeholder="Video Açıklaması ${isShorts ? '(kısa ve çarpıcı – 100-200 karakter ideal)' : '(150+ karakter önerilir)'}"></textarea>
            <input type="text" id="tags" placeholder="Etiketler (virgülle ayırın, AI araması için önemlidir)">
            <button class="analyze-btn" onclick="startAnalysis()">
                🚀 ${isShorts ? 'SHORTS ANALİZİ BAŞLAT' : 'UZUN VİDEO ANALİZİ BAŞLAT'}
            </button>
        </div>
    `;
}

function renderLoadingScreen() {
    const stepsHTML = analysisSteps.map((step, index) => {
        const isActive = index === state.currentStep;
        const isCompleted = index < state.currentStep;
        const statusClass = isCompleted ? 'completed' : (isActive ? 'active' : '');
        const icon = isCompleted ? '✓' : (isActive ? '●' : '○');
        return `
            <div class="loading-step ${statusClass}">
                <div class="loading-step-icon">${icon}</div>
                <span>${step.text}</span>
            </div>
        `;
    }).join('');
    return `
        <div class="main-container">
            <div class="loading-container">
                <div class="loading-title" style="color:#a855f7;">${state.proMode ? '🧠 PRO MOD: DERİN ANALİZ YAPILIYOR...' : '🎬 STANDART ANALİZ YAPILIYOR...'}</div>
                <div class="progress-wrapper">
                    <div class="progress-bar-container">
                        <div class="progress-bar" style="width: ${state.progress}%"></div>
                    </div>
                    <div class="progress-text">%${Math.round(state.progress)} tamamlandı</div>
                </div>
                <div class="loading-steps">${stepsHTML}</div>
            </div>
        </div>
    `;
}

function getVideoSpecificFeedback(res) {
    const ret = res.retention_data || {};
    const tech = res.tech_data || {};
    const vTempo = res.visual_tempo || [];
    const aTempo = res.audio_tempo || [];
    const reasons = [];
    const actions = [];
    const positives = [];

    if (res.dynamic_feedback) reasons.push(res.dynamic_feedback);
    if (res.golden_frame_sec > 0) {
        actions.push(`🎬 ALTIN KARE ÖNERİSİ: En yüksek görsel tempo ${res.golden_frame_sec}. saniyede. Thumbnail için bu kareyi kullanabilirsin.`);
    }
    if (res.seo_score >= 8.5) {
        positives.push(`🔍 SEO BOMBA GİBİ (${res.seo_score}/10): Başlık, açıklama ve etiketler kusursuz uyumlu.`);
    } else if (res.seo_score < 5.5) {
        reasons.push(`🔍 SEO ZAYIF (${res.seo_score}/10): Başlık kelimeleri açıklamada geçmiyor – video kitleye ulaşmakta zorlanabilir.`);
        actions.push(`🔍 SEO ÖNERİSİ: Açıklamanın ilk 200 karakterine başlık kelimelerini yerleştirebilirsin.`);
    }
    if (vTempo.length > 0 && vTempo[0] < 1.8) {
        reasons.push(`Giriş görsel olarak durağan. İzleyicinin erken ayrılma ihtimali artabilir.`);
        actions.push(`🎬 EDİT ÖNERİSİ: 00:01'e dinamik zoom veya geçiş ekleyebilirsin.`);
    }
    let deadZoneFound = false;
    vTempo.forEach((val, idx) => {
        if (!deadZoneFound && idx > 2 && val < 1.1 && (aTempo[idx] || 0) < 1.5) {
            reasons.push(`${idx}. saniyede ses ve görüntü durağan (Ölü Bölge).`);
            actions.push(`🎬 KESİM ÖNERİSİ: ${idx - 1} ile ${idx + 1} arası sahneyi kısaltabilir veya tempo katabilirsin.`);
            deadZoneFound = true;
        }
    });
    if (res.coaching_mode === "PROACTIVE" && ret.worst_drop_sec > 0) {
        reasons.push(`${ret.worst_drop_sec}. saniyede %${ret.drop_percent} kitle kaybı – gerçek veriyle tespit edildi.`);
        actions.push(`📊 RETENTION ÖNERİSİ: Bu saniyedeki sahneyi videonun en heyecanlı karelerinden biriyle değiştirebilirsin.`);
    } else if (res.coaching_mode === "PREDICTIVE" && ret.score < 6.5) {
        reasons.push("Tahmini retention düşük – giriş izleyiciyi yakalamakta zorlanıyor olabilir.");
        actions.push(`📊 GİRİŞ ÖNERİSİ: İlk 10 sn'yi baştan çekmeyi deneyebilirsin.`);
    }
    if (res.thumb_score !== null && res.thumb_score < 4.5) {
        reasons.push(`Thumbnail zayıf (${res.thumb_score}/10) – tıklanma oranını düşürebilir.`);
        actions.push(`📸 IŞIK ÖNERİSİ: Parlaklık ve renk doygunluğunu artırabilirsin.`);
    } else if (res.thumb_score !== null && res.thumb_score >= 7.5) {
        positives.push(`📸 Thumbnail güçlü (${res.thumb_score}/10) – yüksek tıklanma potansiyeli.`);
    }
    if (res.tech_score < 7) {
        if (tech.max_gap > 8) {
            reasons.push(`Videonda ${tech.max_gap} sn ölü bölge.`);
            actions.push(`🎬 TEMPO ÖNERİSİ: Bu boşluğu kesebilir veya efektle doldurabilirsin.`);
        }
        if (tech.peaks < 8) {
            reasons.push(`Sadece ${tech.peaks} patlama – video düz, enerjisiz.`);
            actions.push(`⚡ PATLAMA ÖNERİSİ: Her 6-8 sn'ye cut/zoom/ses efekti ekleyebilirsin.`);
        }
    }
    if (res.retention_score >= 7.0) positives.push(`Giriş güçlü – retention ${res.retention_score}/10, izleyici kalıyor.`);
    if (res.tech_score >= 7.5) positives.push(`Tempo mükemmel – ${tech.peaks} patlama, akıcı.`);

    let feedbackHTML = '';
    if (positives.length > 0) {
        feedbackHTML += `
            <div style="margin:24px 0; padding:20px; background:rgba(34,197,94,0.15); border:1px solid #22c55e; border-radius:14px; line-height:1.6;">
                <strong style="color:#4ade80; font-size:1.15rem;">Videodaki güçlü yönler</strong><br><br>
                ${positives.map(p => `• ${p}`).join('<br><br>')}
            </div>
        `;
    }
    if (reasons.length > 0) {
        feedbackHTML += `
            <div style="margin:24px 0; padding:20px; background:rgba(220,38,38,0.12); border:1px solid #ef4444; border-radius:14px; line-height:1.6;">
                <strong style="color:#f87171; font-size:1.15rem;">Videodaki geliştirilmesi gereken yönler</strong><br><br>
                ${reasons.map(r => `• ${r}`).join('<br><br>')}
                <br><br><strong style="color:#fbbf24;">Bu durumda şunları deneyebilirsin:</strong>
                <ul style="margin-top:12px; padding-left:24px; line-height:1.7;">
                    ${actions.map(a => `<li>${a}</li>`).join('')}
                </ul>
            </div>
        `;
    }
    return feedbackHTML;
}

function renderResultScreen() {
    const res = state.result;
    const isShorts = res.is_shorts_mode === true;
    let warningClass = 'good';
    if (res.retention_score < 4) warningClass = 'critical';
    else if (res.overall_score < 7.5) warningClass = 'warning';

    const commentHTML = getVideoSpecificFeedback(res);

    let gridItems = `
        <div class="detail-item">
            <span class="detail-item-label">🚀 Retention Skoru</span>
            <div class="detail-item-value">${res.retention_score}/10</div>
        </div>
        <div class="detail-item">
            <span class="detail-item-label">🎬 Teknik Tempo</span>
            <div class="detail-item-value">${res.tech_score}/10</div>
        </div>
        <div class="detail-item">
            <span class="detail-item-label">🔍 SEO Gücü</span>
            <div class="detail-item-value">${res.seo_score}/10</div>
        </div>
        <div class="detail-item">
            <span class="detail-item-label">⚡ Patlama Sayısı</span>
            <div class="detail-item-value">${res.peaks}</div>
        </div>
    `;
    if (!isShorts) {
        gridItems = `
            <div class="detail-item">
                <span class="detail-item-label">🖼️ Thumbnail Kalite</span>
                <div class="detail-item-value">${res.thumb_score}/10</div>
            </div>
            ${gridItems}
        `;
    }

    let shortsHTML = '';
    if (res.viral_segments && res.viral_segments.length > 0) {
        const segmentsHTML = res.viral_segments.map((seg, idx) => `
            <div class="segment-item">
                <div class="segment-info">
                    <span class="segment-time">⏱️ ${seg.start_sec}s - ${seg.end_sec}s</span>
                    <span class="segment-duration">(${seg.suggested_duration}s — AI dinamik hesapladı)</span>
                </div>
                <button class="create-short-btn" id="short-btn-${idx}" onclick="createShort(${idx}, this)" ${!res.ffmpeg_available ? 'disabled' : ''}>
                    ${res.ffmpeg_available ? '✂️ Klibe Dönüştür' : '❌ FFmpeg Gerekli'}
                </button>
            </div>
        `).join('');

        /* Manuel kesme arayüzü */
        const manualCutHTML = res.ffmpeg_available ? `
            <div id="manualCutBox" style="margin-top:18px; background:rgba(139,92,246,0.1); border:1px dashed #7c3aed; border-radius:10px; padding:14px 16px;">
                <div style="color:#c4b5fd; font-weight:bold; margin-bottom:10px; font-size:0.95rem;">✂️ Manuel Kesme — Kendi Aralığını Gir</div>
                <div style="display:flex; align-items:center; gap:10px; flex-wrap:wrap;">
                    <label style="color:#e2e8f0; font-size:0.88rem;">Başlangıç:</label>
                    <input id="manualStart" type="text" placeholder="1:08 veya 1.08"
                        style="width:90px; background:#1e1b4b; border:1px solid #6d28d9; color:white; padding:6px 8px; border-radius:6px; font-size:0.9rem;"/>
                    <label style="color:#e2e8f0; font-size:0.88rem;">Bitiş:</label>
                    <input id="manualEnd" type="text" placeholder="1:19 veya 1.19"
                        style="width:90px; background:#1e1b4b; border:1px solid #6d28d9; color:white; padding:6px 8px; border-radius:6px; font-size:0.9rem;"/>
                    <button id="manualCutBtn" onclick="createManualShort(this)"
                        style="background:linear-gradient(90deg,#7c3aed,#a855f7); border:none; color:white; padding:7px 18px; border-radius:7px; font-weight:bold; cursor:pointer; font-size:0.9rem; box-shadow:0 0 8px rgba(168,85,247,0.4);">
                        ✂️ Kes & İndir
                    </button>
                </div>
                <div style="color:#9ca3af; font-size:0.78rem; margin-top:7px;">
                    💡 <b>1.08</b> veya <b>1:08</b> (dakika.saniye) ya da düz <b>68</b> (saniye) yazabilirsin.
                </div>
            </div>
        ` : '';

        shortsHTML = `
            <div class="viral-box">
                <div class="viral-box-title" style="color:#22c55e;">🔥 DİNAMİK SAHNELER TESPİT EDİLDİ!</div>
                <div class="viral-box-subtitle">AI her klibi için enerji düşene kadar izledi ve süreyi dinamik hesapladı. Kesmek ister misin?</div>
                ${segmentsHTML}
                ${manualCutHTML}
            </div>
        `;
    }

    const videoModalHTML = `
        <div id="videoModal" style="display:none; position:fixed; inset:0; z-index:9999; background:rgba(0,0,0,0.92); align-items:center; justify-content:center; flex-direction:column; gap:16px;">
            <button onclick="closeVideoModal()" style="position:absolute; top:18px; right:22px; background:#ef4444; border:none; color:white; font-size:1.4rem; font-weight:bold; border-radius:50%; width:44px; height:44px; cursor:pointer; z-index:10000; box-shadow:0 0 12px rgba(239,68,68,0.6);" title="Kapat (ESC)">✕</button>
            <p style="color:#a855f7; font-weight:bold; font-size:1rem; margin:0;">🎬 Klip Önizleme — Tam ekran KAPALI (pywebview uyumlu)</p>
            <video id="modalVideo" style="max-width:90vw; max-height:78vh; border-radius:12px; border:2px solid #6b21a8; background:#000;" controls controlslist="nofullscreen nodownload" disablepictureinpicture></video>
            <a id="modalDownloadBtn" href="#" download style="background:linear-gradient(90deg,#16a34a,#22c55e); color:white; padding:10px 28px; border-radius:8px; font-weight:bold; font-size:1rem; text-decoration:none; box-shadow:0 0 10px rgba(34,197,94,0.4);">
                📥 Bilgisayara İndir
            </a>
        </div>
    `;

    const comp = res.competitor_data;
    let compHTML = '';
    if (comp) {
        const fakeWarningHTML = comp.is_fake ? `
            <div style="background:rgba(245,158,11,0.15); border:1px solid #f59e0b; padding:12px 16px; border-radius:8px; margin-bottom:12px; font-size:0.9rem;">
                ⚠️ <b style="color:#f59e0b;">Rakip Verisi Çekilemedi!</b> İnternet bağlantısı veya yt-dlp sorunu nedeniyle gerçek rakip bulunamadı.
                Aşağıdaki veriler <b>sektör ortalamasıdır, gerçek değildir.</b> Gerçek analiz için rakip URL girerek yeniden dene.
            </div>
        ` : '';

        const killSwitchHTML = res.kill_switch_active ? `
            <div style="background:rgba(239,68,68,0.15); border:2px solid #ef4444; padding:14px 18px; border-radius:10px; margin-top:12px;">
                <strong style="color:#ef4444;">🚨 KONSEPT UYUMSUZLUĞU TESPİT EDİLDİ!</strong><br>
                <span style="color:#fca5a5; font-size:0.9rem;">
                    Senin başlığındaki anahtar kelimelerle rakibin konsepti arasında hiçbir bağlantı bulunamadı.
                    Bu rakibin etiketlerini kopyalamak algoritmayı karıştırır.<br><br>
                    <b>⛔ PDF Raporundaki Etiket Önerileri ve Başlık Üreticisi bu rakip için devre dışı bırakıldı!</b>
                    Kendi konseptine uygun bir rakip URL girerek yeniden analiz yap.
                </span>
            </div>
        ` : `
            <div style="text-align:center; margin-top:12px; font-size:0.95rem; color:#e2e8f0; background:rgba(0,0,0,0.3); padding:10px; border-radius:8px;">
                🎯 <em>Yapay zeka rakibi taradı! Etiket taktiklerini aşağıdaki PDF Raporuna işledi.</em>
            </div>
        `;

        compHTML = `
            <div style="background:linear-gradient(135deg,#1e1b4b,#312e81); border:2px solid #6366f1; padding:20px; border-radius:12px; margin-top:25px; box-shadow:0 4px 15px rgba(99,102,241,0.3);">
                <div style="text-align:center; margin-bottom:15px;">
                    <span style="background:#ef4444; color:white; padding:5px 15px; border-radius:20px; font-weight:bold; font-size:0.9rem; letter-spacing:1px;">🥊 RAKİP KAPIŞMASI AKTİF</span>
                </div>
                ${fakeWarningHTML}
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <div style="flex:1; text-align:center;">
                        <div style="font-size:2.5rem; margin-bottom:5px;">😎</div>
                        <strong style="color:#a855f7; font-size:1.1rem;">SEN</strong>
                        <div style="font-size:0.8rem; color:#aaa; margin-top:3px;">${res.title ? res.title.substring(0, 25) + '...' : 'Senin Videon'}</div>
                    </div>
                    <div style="font-size:2.5rem; font-weight:900; color:#f59e0b; font-style:italic; text-shadow:0 0 15px rgba(245,158,11,0.6);">VS</div>
                    <div style="flex:1; text-align:center;">
                        <div style="font-size:2.5rem; margin-bottom:5px;">🥷</div>
                        <strong style="color:#ef4444; font-size:1.1rem;">${(comp.channel || 'Rakip Kanal').toUpperCase()}</strong>
                        <div style="font-size:0.8rem; color:#aaa; margin-top:3px;">🔥 ${(comp.views || 0).toLocaleString()} İzlenme</div>
                    </div>
                </div>
                ${killSwitchHTML}
            </div>
        `;
    }

    return `
        ${videoModalHTML}
        <div class="main-container">
            <div class="result-container">
                <div class="score-card">
                    <h2>📊 ${isShorts ? 'SHORTS' : 'UZUN VİDEO'} PERFORMANS PUANI</h2>
                    <div class="big-score">${res.overall_score}</div>
                    <div class="warning-box ${warningClass}">${res.critical_warning}</div>
                </div>
                <div class="results-grid">${gridItems}</div>
                ${commentHTML}
                ${compHTML}
                ${shortsHTML}
                <button class="analyze-btn" style="margin-top:20px; width:100%;" onclick="exportPDF()">
                    📄 Bu Analizin Detaylı PDF Raporunu İndir
                </button>
                <button class="retry-btn" onclick="reset()">🔄 YENİ ANALİZ YAP</button>
            </div>
        </div>
    `;
}

function exportPDF() {
    if (!state.result || !state.result.analysis_id) return alert("Önce analiz yapmalısın!");
    window.location.href = `${API_URL}/export_pdf/${state.result.analysis_id}`;
}

function openVideoModal(downloadUrl) {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('modalVideo');
    const dlBtn = document.getElementById('modalDownloadBtn');
    if (!modal || !video) return;
    video.src = downloadUrl;
    dlBtn.href = downloadUrl;
    modal.style.display = 'flex';
    video.play().catch(() => { });
}

function closeVideoModal() {
    const modal = document.getElementById('videoModal');
    const video = document.getElementById('modalVideo');
    if (video) { video.pause(); video.src = ''; }
    if (modal) modal.style.display = 'none';
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') closeVideoModal();
});

function playAnalysisCompleteSound() {
    try {
        const ctx = new (window.AudioContext || window.webkitAudioContext)();
        function playTone(freq, startTime, duration, gainVal, type = 'sine') {
            const osc = ctx.createOscillator();
            const gain = ctx.createGain();
            osc.connect(gain);
            gain.connect(ctx.destination);
            osc.type = type;
            osc.frequency.setValueAtTime(freq, ctx.currentTime + startTime);
            osc.frequency.linearRampToValueAtTime(freq * 1.06, ctx.currentTime + startTime + duration * 0.6);
            gain.gain.setValueAtTime(0, ctx.currentTime + startTime);
            gain.gain.linearRampToValueAtTime(gainVal, ctx.currentTime + startTime + 0.02);
            gain.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + startTime + duration);
            osc.start(ctx.currentTime + startTime);
            osc.stop(ctx.currentTime + startTime + duration + 0.05);
        }
        playTone(520, 0.00, 0.18, 0.35);
        playTone(660, 0.14, 0.20, 0.45);
        playTone(880, 0.26, 0.30, 0.55);
        playTone(1760, 0.26, 0.25, 0.15, 'triangle');
        setTimeout(() => ctx.close(), 1200);
    } catch (e) { }
}

let progressIntervalId = null;

function startProgressBar() {
    if (progressIntervalId) clearInterval(progressIntervalId);
    progressIntervalId = null;
    state.progress = 0;
    state.currentStep = 0;
    const totalSteps = analysisSteps.length;
    const INTERVAL_MS = 80;
    const FAST_STEP = state.proMode ? 0.55 : 0.95;
    const SLOW_STEP = 0.06;
    const BRAKE_POINT = 95;

    progressIntervalId = setInterval(() => {
        if (!state.loading) {
            clearInterval(progressIntervalId);
            progressIntervalId = null;
            return;
        }
        const step = state.progress < BRAKE_POINT ? FAST_STEP : SLOW_STEP;
        state.progress = Math.min(99, state.progress + step);
        state.currentStep = Math.min(totalSteps - 2, Math.floor((state.progress / 99) * (totalSteps - 1)));
        render();
    }, INTERVAL_MS);
}

function finishProgressBar() {
    if (progressIntervalId) { clearInterval(progressIntervalId); progressIntervalId = null; }
    state.progress = 100;
    state.currentStep = analysisSteps.length - 1;
    render();
    setTimeout(playAnalysisCompleteSound, 80);
}

async function startAnalysis() {
    const videoInput = document.getElementById('video');
    if (!videoInput || !videoInput.files || videoInput.files.length === 0) {
        alert("⚠️ Lütfen bir video dosyası seçin!");
        return;
    }
    const videoFile = videoInput.files[0];
    state.videoFile = videoFile;
    const title = document.getElementById('title')?.value?.trim() || '';
    const desc = document.getElementById('desc')?.value?.trim() || '';
    const tags = document.getElementById('tags')?.value?.trim() || '';
    const thumbFile = document.getElementById('thumb')?.files?.[0] || null;
    const csvFile = document.getElementById('csv')?.files?.[0] || null;
    const compUrl = document.getElementById('competitor_url')?.value?.trim() || '';

    state.loading = true;
    state.result = null;
    state.progress = 0;
    state.currentStep = 0;
    render();
    startProgressBar();

    const formData = new FormData();
    formData.append('video_file', videoFile);
    if (csvFile) formData.append('csv_file', csvFile);
    if (thumbFile) formData.append('thumb_file', thumbFile);
    formData.append('title', title);
    formData.append('description', desc);
    formData.append('tags', tags);
    formData.append('is_shorts', state.mode === "shorts");
    formData.append('pro_mode', state.proMode);
    formData.append('competitor_url', compUrl);
    formData.append('channel_id', currentChannelId);

    try {
        const apiResponse = await fetch(`${API_URL}/analyze`, { method: 'POST', body: formData });
        finishProgressBar();
        if (!apiResponse.ok) throw new Error(`Sunucu hatası: ${apiResponse.status}`);
        const result = await apiResponse.json();
        if (result.error) throw new Error(result.error);
        state.tempVideoName = result.temp_video_name || null;
        state.result = result;
        state.loading = false;
        render();
    } catch (error) {
        console.error('Analiz hatası:', error);
        finishProgressBar();
        alert(`❌ Analiz başarısız!\n\n${error.message}`);
        state.loading = false;
        render();
    }
}

// MM:SS, M.SS or plain seconds — FIX: \d{1,2} with "0.5" → 5sec works correctly
function parseTimeInput(val) {
    const s = String(val).trim();
    if (/^\d+\.\d{1,2}$/.test(s)) {
        const parts = s.split('.');
        return parseInt(parts[0]) * 60 + parseInt(parts[1]);
    }
    if (s.includes(':')) {
        const parts = s.split(':');
        return (parseFloat(parts[0]) || 0) * 60 + (parseFloat(parts[1]) || 0);
    }
    return parseFloat(s);
}

async function createManualShort(btn) {
    const startVal = parseTimeInput(document.getElementById('manualStart')?.value);
    const endVal = parseTimeInput(document.getElementById('manualEnd')?.value);
    if (isNaN(startVal) || isNaN(endVal)) { alert("⚠️ Lütfen başlangıç ve bitiş değerlerini gir!\n\nFormat: 1.08 veya 1:08 veya 68"); return; }
    if (endVal <= startVal) { alert("⚠️ Bitiş, başlangıçtan büyük olmalı!"); return; }
    if (endVal - startVal > 180) { alert("⚠️ Maksimum 180 saniye (3 dakika) kesebilirsin."); return; }

    const duration = Math.round((endVal - startVal) * 10) / 10;
    const tempFilename = state.tempVideoName;
    if (!tempFilename && !state.videoFile) { alert("❌ Video bulunamadı. Yeniden analiz yap."); return; }

    const originalText = btn.textContent;
    const originalBg = btn.style.background || '';
    btn.textContent = '⏳ Kesiliyor...';
    btn.disabled = true;
    btn.style.background = 'linear-gradient(90deg,#4b5563,#6b7280)';

    const doFetch = async (useFile) => {
        const fd = new FormData();
        fd.append('start', startVal);
        fd.append('duration', duration);
        if (useFile) { fd.append('temp_filename', 'MISSING'); fd.append('video_file', state.videoFile); }
        else { fd.append('temp_filename', tempFilename); }
        const res = await fetch(`${API_URL}/create_short`, { method: 'POST', body: fd });
        return res.json();
    };

    try {
        let data = await doFetch(false);
        if (!data.success && data.error?.includes('bulunamadı') && state.videoFile) {
            btn.textContent = '🔄 Tekrar deneniyor...';
            data = await doFetch(true);
        }
        if (data.success) {
            btn.textContent = `✅ ${formatSec(startVal)}–${formatSec(endVal)} İndir`;
            btn.style.background = 'linear-gradient(90deg,#16a34a,#22c55e)';
            btn.style.boxShadow = '0 0 10px rgba(34,197,94,0.5)';
            btn.disabled = false;
            btn.onclick = () => openVideoModal(data.download_url);
            openVideoModal(data.download_url);
            const startInput = document.getElementById('manualStart');
            const endInput = document.getElementById('manualEnd');
            if (startInput) startInput.value = '';
            if (endInput) endInput.value = '';
            const cutBox = document.getElementById('manualCutBox');
            if (cutBox) {
                const newBtn = document.createElement('button');
                newBtn.textContent = '✂️ Kes & İndir';
                newBtn.style.cssText = 'background:linear-gradient(90deg,#7c3aed,#a855f7);border:none;color:white;padding:7px 18px;border-radius:7px;font-weight:bold;cursor:pointer;font-size:0.9rem;box-shadow:0 0 8px rgba(168,85,247,0.4);margin-top:6px;';
                newBtn.onclick = () => createManualShort(newBtn);
                btn.insertAdjacentElement('afterend', newBtn);
            }
        } else {
            throw new Error(data.error || 'Bilinmeyen hata');
        }
    } catch (error) {
        console.error('Manuel kesme hatası:', error);
        alert(`❌ Klip oluşturulamadı!\n\n${error.message}`);
        btn.textContent = originalText;
        btn.style.background = originalBg;
        btn.disabled = false;
        btn.onclick = () => createManualShort(btn);
    }
}

function formatSec(sec) {
    const m = Math.floor(sec / 60);
    const s = Math.floor(sec % 60);
    return m > 0 ? `${m}:${String(s).padStart(2, '0')}` : `${s}s`;
}

async function createShort(segmentIndex, btn) {
    const res = state.result;
    const seg = res.viral_segments[segmentIndex];
    if (!seg) { alert("❌ Segment bulunamadı!"); return; }

    const tempFilename = state.tempVideoName;
    if (!tempFilename && !state.videoFile) {
        alert("❌ Video dosyası bulunamadı! Lütfen sayfayı yenileyin ve tekrar analiz yapın.");
        return;
    }

    const confirmMsg = `Bu aralıktan (${seg.start_sec}s - ${seg.end_sec}s) Shorts oluşturulsun mu?\n\n⏱️ AI Dinamik Süre: ${seg.suggested_duration}s\n\nEvet dersen kesilecek.`;
    if (!confirm(confirmMsg)) return;

    const originalText = btn.textContent;
    btn.textContent = '⏳ Kesiliyor...';
    btn.disabled = true;

    const formData = new FormData();
    formData.append('start', seg.start_sec);
    formData.append('duration', seg.suggested_duration);
    if (tempFilename) {
        formData.append('temp_filename', tempFilename);
    } else {
        formData.append('temp_filename', 'MISSING');
        formData.append('video_file', state.videoFile);
    }

    try {
        const response = await fetch(`${API_URL}/create_short`, { method: 'POST', body: formData });
        const data = await response.json();
        if (data.success) {
            btn.textContent = '✅ İndir (Hazır)';
            btn.style.background = 'linear-gradient(90deg,#16a34a,#22c55e)';
            btn.style.boxShadow = '0 0 12px rgba(34,197,94,0.5)';
            btn.disabled = false;
            btn.onclick = () => openVideoModal(data.download_url);
            openVideoModal(data.download_url);
        } else {
            const isTempExpired = data.error && (data.error.includes('bulunamadı') || data.error.includes('not found') || data.error.includes('temp'));
            if (isTempExpired && state.videoFile) {
                btn.textContent = '🔄 Tekrar Deneniyor...';
                const retryForm = new FormData();
                retryForm.append('start', seg.start_sec);
                retryForm.append('duration', seg.suggested_duration);
                retryForm.append('temp_filename', 'MISSING');
                retryForm.append('video_file', state.videoFile);
                const retryRes = await fetch(`${API_URL}/create_short`, { method: 'POST', body: retryForm });
                const retryData = await retryRes.json();
                if (retryData.success) {
                    btn.textContent = '✅ İndir (Hazır)';
                    btn.style.background = 'linear-gradient(90deg,#16a34a,#22c55e)';
                    btn.style.boxShadow = '0 0 12px rgba(34,197,94,0.5)';
                    btn.disabled = false;
                    btn.onclick = () => openVideoModal(retryData.download_url);
                    openVideoModal(retryData.download_url);
                    return;
                }
            }
            throw new Error(data.error || 'Bilinmeyen hata');
        }
    } catch (error) {
        console.error('Shorts hatası:', error);
        alert(`❌ Shorts oluşturulamadı!\n\n${error.message}`);
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

function reset() {
    state.result = null;
    state.loading = false;
    state.progress = 0;
    state.currentStep = 0;
    state.videoFile = null;
    state.tempVideoName = null;
    render();
}

document.addEventListener('DOMContentLoaded', async () => {
    console.log('🎬 YouTube Analiz Pro V3.2 başlatıldı');
    await loadChannels();
    render();
});
