/**
 * translations.js — YT Analiz Pro i18n (Internationalization)
 * v6.0.0 — TR / EN çoklu dil desteği
 *
 * Kullanım:
 *   t('key')           → Seçili dildeki metni döner
 *   setLang('en')      → Dili değiştirir, storage'a kaydeder
 *   applyTranslations() → Tüm [data-i18n] elementlerini günceller
 */

const TRANSLATIONS = {
  tr: {
    // ── Header ──
    logo_sub:             'Viral Klonlama Motoru',
    btn_info_title:       'Nasıl Çalışır?',
    btn_fullscreen_title: 'Tam Ekranda Aç',
    server_checking:      'Kontrol ediliyor...',
    server_online:        '● Çevrimiçi',
    server_offline:       '● Çevrimdışı',
    footer_server:        'Sunucu:',

    // ── Login ──
    login_hint:          'Ekosisteme bağlanmak için giriş yapın.',
    login_username_ph:   'Kullanıcı Adı',
    login_password_ph:   'Şifre',
    btn_login:           'Giriş Yap',
    login_loading:       'Giriş yapılıyor...',
    login_error_empty:   'Kullanıcı adı ve şifre zorunludur.',
    login_error_server:  'Sunucuya bağlanılamadı.',
    login_error_fail:    'Giriş başarısız.',

    // ── Dashboard ──
    welcome_text:        'Hoş geldin,',
    btn_logout_title:    'Çıkış Yap',
    recent_title:        'Son Analizlerim',
    recent_loading:      'Yükleniyor...',
    recent_empty:        'Henüz analiz yok.',
    recent_error:        'Veriler çekilemedi.',

    // ── Rabbit Hole ──
    rabbit_title:        '🐇 Tavşan Deliği (Niş Bulucu)',
    rabbit_placeholder:  'Örn: Kripto Para',
    btn_rabbit:          'Bul',

    // ── Buttons ──
    btn_clone:           '🚀 Klonla',
    btn_debate:          '⚔️ Tartış',
    btn_dna:             '🧬 DNA',
    btn_analyze:         '⚔️ Gerilla Stratejisi',
    btn_channel_dna:     '📊 Başarı Formülü',

    // ── Loading ──
    loading_main:        'AI senaryoyu analiz ediyor',
    loading_sub_default: 'Transcript çekiliyor...',
    loading_sub_page:    'Sayfa verisi okunuyor...',
    loading_sub_ai:      'AI konsept üretiyor...',
    loading_sub_channel: 'Rakip verileri sömürülüyor... Savaş Raporu hazırlanıyor!',
    loading_sub_rabbit:  "YouTube'un derinliklerine iniliyor... (Bu işlem 15-30 sn sürebilir)",
    loading_sub_debate:  'Persona A vs B savaşıyor...',
    loading_sub_battle:  '⚔️ Ajanlar Kapışıyor... Hakem Karar Veriyor...',

    // ── Result ──
    result_badge:        '✅ Konsept Hazır!',
    btn_reset:           '↩ Yeni Video',

    // ── Debate ──
    debate_badge:        '⚔️ Tartışma Tamamlandı!',
    debate_critic_label: '🔬 Eleştirmen',
    debate_wizard_label: '🪄 Büyücü',
    debate_winner_label: '🏆 KAZANAN FİKİR',
    debate_hook_tag:     'KANCA',
    btn_debate_reset:    '↩ Yeni Video',

    // ── DNA ──
    dna_badge:           '🧬 DNA Analizi Tamamlandı!',
    dna_hook_label:      'KANCA',
    dna_tempo_label:     'TEMPO',
    dna_cta_label:       'CTA',
    dna_emotion_label:   'DUYGU',
    dna_howto_btn:       'ℹ️ Puan nasıl hesaplanır?',
    dna_anatomy_label:   '🔬 VİRAL ANATOMİ (DNA Özeti)',
    dna_prompt_label:    '🔑 DNA MASTER PROMPT',
    btn_copy_dna:        '📋 DNA PROMPT\'U KOPYALA',
    btn_dna_reset:       '↩ Yeni Video',
    copied:              'Kopyalandı!',
    info_strat_mode:     'Şu an Strateji Modundasın.',
    info_strat_desc:     'Video sayfasındasın. <strong>Akıllı Butonlar</strong> devrede.',
    info_strat_v_ana:    'Viral Anatomi:</strong> Videonun neden patladığını (veya neden çöktüğünü) anla.',
    info_intel_mode:     'Şu an İstihbarat Modundasın.',
    info_intel_desc:     'Kanal sayfasındasın.',

    info_clone_desc:     'Açık YouTube videosunu analiz eder ve kanalınıza özel <strong>3 viral içerik fikri</strong> üretir. Her fikir; bir başlık, kanca cümlesi ve thumbnail önerisi içerir. Sistem videonun izlenme sayısına göre onu otomatik olarak <strong>5 katmana</strong> (Dead / Potential / Rising / Viral / Mega Viral) sınıflandırır.',
    info_debate_desc:    'İki farklı AI kişiliğini birbirine karşı koyar: <strong style="color:#f87171;">🔬 Acımasız Eleştirmen</strong> (neyin işe yaramayacağını söyler) ve <strong style="color:#a78bfa;">🪄 Viral Büyücü</strong> (yüksek potansiyelli öneriyi sunar). En güçlü tek fikir 🏆 "Kazanan Fikir" olarak sentezlenir.',
    info_dna_desc:       'Videonun altyazısını analiz ederek 4 puan ölçer: <span style="color:#f43f5e;">🪝 Kanca</span> (ilk %20), <span style="color:#06b6d4;">⏱️ Tempo</span> (ritim), <span style="color:#22c55e;">📣 CTA</span> (aksiyon çağrısı), <span style="color:#a855f7;">💥 Duygu</span>. Ardından bu yapıyı başka bir AI\'ya vererek aynı kalitede içerik üretmenizi sağlayan <strong>Master Prompt</strong> oluşturulur. Altyazı yoksa başlık ve açıklamadan <strong>tahmini analiz</strong> yapılır (sarı uyarı gösterilir).',
    info_guerrilla_desc: 'Bir rakip kanalın sayfasındayken çalışır. Bu kanalda en hızlı ivmelenen videoları tespit eder ve size "<strong>Rakibin neyi doğru yapıyor?</strong>" sorusunun yanıtını verir. Kanallar arası içerik boşluklarını görmek için idealdir.',
    info_channel_dna_desc: 'Kanalın son 5 videosunu otomatik olarak analiz eder. Her videonun DNA puanını hesaplar ve kanalın ortalama <strong>Kanca, Tempo, CTA ve Duygu</strong> skorlarını çıkarır. Groq AI, bu verilerden kanalın "Başarı Formülü"nü üç-dört cümleyle özetler.',
    info_rabbit_desc:    'Arama kutusu: bir anahtar kelime yazın (örn: "Kripto Para"). Sistem, o nişdeki en hızlı ivmelenen (<strong>Outlier</strong>) videoyu tespit eder ve size klonlanabilir içerik fikirleri sunar. Trend bir konuya girmeden önce görme aracı olarak kullanın.',
    info_matrix_desc:    'Herhangi bir butona basmadan çalışır. YouTube ana sayfasında gezinirken, saatte <strong>5.000+ izlenme</strong> hızına ulaşan videolara otomatik olarak 🔥 TREND rozeti ve yeşil neon çerçeve ekler. Viral içerikleri tek bakışta tanımanızı sağlar.',
    info_dna_method_desc:'Genel DNA Skoru basit ortalama değildir. Viral başarı bilimine göre ağırlıklandırılmıştır:<br><br><span style="color:#f43f5e;">Kanca ×0.40</span> + <span style="color:#06b6d4;">Tempo ×0.40</span> + <span style="color:#a855f7;">Duygu ×0.10</span> + <span style="color:#22c55e;">CTA ×0.10</span><br><br>🔥 <strong>Viral Canavar Bonusu:</strong> Kanca ve Tempo ikisi birden >75 ise +20 puan.<br>🛡️ <strong>Elite Koruma:</strong> İkisi birden ≥80 ise CTA/Duygu minimum 50 kredi alır.<br>👑 90+ Efsanevi  🔥 75-89 Viral  ✅ 50-74 Güçlü  ⚠️ 0-49 Geliştirilebilir',
    info_intel_chaos:    'Kaos Metriği:</strong> Rakibin öfke ve tempo analizini gör.',
    info_exp_mode:       'Şu an Keşif Modundasın.',
    info_exp_desc:       'YouTube Ana Sayfası veya Arama sonuçlarındasın. Serbest dolaşım.',



    // ── Missing from patch ──
    sugg_video:          'Bu videoyu analiz etmeye hazır mısın?',
    sugg_channel:        'Kanalın en hızlı yükselen videosunu klonla!',
    views_per_day:       'izlenme/gün',
    no_views_data:       'izlenme verisi yok',
    views:               'izlenme',
    sub_ratio:           'Abone oranı',
    algo_spread:         'Algoritma yayılımı',
    velocity:            'Hız',
    channel:             'Kanal',
    watch:               'İzle',
    compat_analysis:     'Uyumluluk Analizi',
    chaos_metric:        'KAOS METRİĞİ',
    viral_anatomy_hit:   'VİRAL ANATOMİ: Bu Video Neden Patladı?',
    std_anatomy:         'STANDART ANATOMİ: Bu Video Nasıl Kurgulanmış?',
    loading_sub_channel_dna: 'Kanalın son 5 videosunun altyazıları çekiliyor ve DNA puanları hesaplanıyor... (Bu işlem 30-60 sn sürebilir)',
    channel_dna_title:   'KANAL DNA\'SI',
    vids_analyzed:       'video analiz edildi',
    weighted_dna_avg:    'Ağırlıklı DNA Ortalaması',
    no_sub_warning:      'videoda altyazı bulunamadı; bu videolar başlık verisiyle tahmini olarak dahil edildi.',
    success_formula:     'BAŞARI FORMÜLÜ',
    overall_dna_score:   'Genel DNA Skoru',
    tier_mega_viral:     'MEGA VİRAL',
    tier_viral_pot_high: 'VİRAL POTANSİYEL (Yüksek izlenme potansiyeli)',
    tier_viral_pot:      'VİRAL POTANSİYEL',
    tier_strong:         'GÜÇLÜ KANAL',
    tier_improve_full:   'GELİŞTİRİLEBİLİR (Güçlenebilecek yönler var)',
    tier_improve:        'GELİŞTİRİLEBİLİR',
    hook_power:          'Kanca Gücü',
    tempo_rhythm:        'Tempo Ritmi',
    emotion_load:        'Duygu Yükü',
    cta_power:           'CTA Gücü',
    desc_hook:           'Giriş bölümündeki tetikleyici yoğunluğu',
    desc_tempo:          'Cümle varyansı ve geçiş akışkanlığı',
    desc_emotion:        'Duygusal kelime yoğunluğu',
    desc_cta:            'Sonuçtaki aksiyon çağrısı etkinliği',
    error_not_ch_msg:    'Kanal DNA analizi yalnızca YouTube kanal sayfalarında çalışır.',
    error_login_ch_msg:  'Kanal DNA analizi için giriş yapmanız gerekir.',
    algo_breaker:        'Algoritma kırıcı — sistemi çıkart, kazayı kopyalama.',


    // ── Missing from patch ──
    sugg_video:          'Would you like to analyze this video?',
    sugg_channel:        'Clone the fastest growing video of the channel!',
    views_per_day:       'views/day',
    no_views_data:       'no views data',
    views:               'views',
    sub_ratio:           'Sub ratio',
    algo_spread:         'Algorithm spread',
    velocity:            'Velocity',
    channel:             'Channel',
    watch:               'Watch',
    compat_analysis:     'Compatibility Analysis',
    chaos_metric:        'CHAOS METRIC',
    viral_anatomy_hit:   'VIRAL ANATOMY: Why Did This Video Blow Up?',
    std_anatomy:         'STANDARD ANATOMY: How Is This Video Structured?',
    loading_sub_channel_dna: 'Extracting subtitles of the last 5 videos and calculating DNA scores... (This may take 30-60 secs)',
    channel_dna_title:   'CHANNEL DNA',
    vids_analyzed:       'videos analyzed',
    weighted_dna_avg:    'Weighted DNA Average',
    no_sub_warning:      'videos had no subtitles; they were estimated using title data.',
    success_formula:     'SUCCESS FORMULA',
    overall_dna_score:   'Overall DNA Score',
    tier_mega_viral:     'MEGA VIRAL',
    tier_viral_pot_high: 'VIRAL POTENTIAL (Strong view potential)',
    tier_viral_pot:      'VIRAL POTENTIAL',
    tier_strong:         'STRONG CHANNEL',
    tier_improve_full:   'ROOM TO IMPROVE (Some areas could be stronger)',
    tier_improve:        'ROOM TO IMPROVE',
    hook_power:          'Hook Power',
    tempo_rhythm:        'Tempo Rhythm',
    emotion_load:        'Emotion Load',
    cta_power:           'CTA Power',
    desc_hook:           'Trigger density in the intro',
    desc_tempo:          'Sentence variance and transition fluidity',
    desc_emotion:        'Emotional word density',
    desc_cta:            'Call to action effectiveness at the end',
    error_not_ch_msg:    'Channel DNA analysis only works on YouTube channel pages.',
    error_login_ch_msg:  'You must log in for Channel DNA analysis.',
    algo_breaker:        'Algorithm breaker — take out the system, copy the accident.',
    // ── Missing from patch ──
    sugg_video:          'Bu videoyu analiz etmeye hazır mısın?',
    sugg_channel:        'Kanalın en hızlı yükselen videosunu klonla!',
    views_per_day:       'izlenme/gün',
    no_views_data:       'izlenme verisi yok',
    views:               'izlenme',
    sub_ratio:           'Abone oranı',
    algo_spread:         'Algoritma yayılımı',
    velocity:            'Hız',
    channel:             'Kanal',
    watch:               'İzle',
    compat_analysis:     'Uyumluluk Analizi',
    chaos_metric:        'KAOS METRİĞİ',
    viral_anatomy_hit:   'VİRAL ANATOMİ: Bu Video Neden Patladı?',
    std_anatomy:         'STANDART ANATOMİ: Bu Video Nasıl Kurgulanmış?',
    loading_sub_channel_dna: 'Kanalın son 5 videosunun altyazıları çekiliyor ve DNA puanları hesaplanıyor... (Bu işlem 30-60 sn sürebilir)',
    channel_dna_title:   'KANAL DNA\'SI',
    vids_analyzed:       'video analiz edildi',
    weighted_dna_avg:    'Ağırlıklı DNA Ortalaması',
    no_sub_warning:      'videoda altyazı bulunamadı; bu videolar başlık verisiyle tahmini olarak dahil edildi.',
    success_formula:     'BAŞARI FORMÜLÜ',
    overall_dna_score:   'Genel DNA Skoru',
    tier_mega_viral:     'MEGA VİRAL',
    tier_viral_pot_high: 'VİRAL POTANSİYEL (Yüksek izlenme potansiyeli)',
    tier_viral_pot:      'VİRAL POTANSİYEL',
    tier_strong:         'GÜÇLÜ KANAL',
    tier_improve_full:   'GELİŞTİRİLEBİLİR (Güçlenebilecek yönler var)',
    tier_improve:        'GELİŞTİRİLEBİLİR',
    hook_power:          'Kanca Gücü',
    tempo_rhythm:        'Tempo Ritmi',
    emotion_load:        'Duygu Yükü',
    cta_power:           'CTA Gücü',
    desc_hook:           'Giriş bölümündeki tetikleyici yoğunluğu',
    desc_tempo:          'Cümle varyansı ve geçiş akışkanlığı',
    desc_emotion:        'Duygusal kelime yoğunluğu',
    desc_cta:            'Sonuçtaki aksiyon çağrısı etkinliği',
    error_not_ch_msg:    'Kanal DNA analizi yalnızca YouTube kanal sayfalarında çalışır.',
    error_login_ch_msg:  'Kanal DNA analizi için giriş yapmanız gerekir.',
    algo_breaker:        'Algoritma kırıcı — sistemi çıkart, kazayı kopyalama.',


    // ── Error ──
    error_default_title: 'Bir hata oluştu',
    btn_retry:           '↩ Tekrar Dene',
    error_server_off:    '🔴 Sunucu Çevrimdışı',
    error_server_msg:    'YT Analiz Pro masaüstü uygulaması çalışmıyor.',
    error_no_tab:        '🔗 Sekme Bulunamadı',
    error_no_tab_msg:    'Analiz edilecek YouTube video sekmesi bulunamadı.',
    error_not_yt:        '📺 YouTube Sayfası Gerekli',
    error_not_yt_msg:    'Bu eklenti yalnızca YouTube video sayfalarında çalışır.',
    error_not_ch:        '📺 Kanal Sayfası Gerekli',
    error_not_ch_msg:    'Bu işlem yalnızca YouTube kanal sayfalarında çalışır.',
    error_login_req:     '🔐 Giriş Gerekli',
    error_login_ch_msg:  'Kanal analizi için giriş yapmalısınız.',
    error_extract:       '❌ Veri Çekme Hatası',
    error_script:        '❌ Script Hatası',
    error_video_notfound:'❌ Video Verisi Bulunamadı',
    error_video_refresh: 'Video sayfasını yenileyin.',
    error_op_fail:       '⚠️ İşlem Başarısız',
    error_connect:       '🔌 Bağlantı Hatası',
    error_no_keyword:    '⚠️ Eksik Bilgi',
    error_no_keyword_msg:'Lütfen aramak için bir kelime (niş) girin.',
    error_debate_fail:   '⚠️ Tartışma Başarısız',

    // ── Info Panel ──
    info_title:          'ℹ️ YT Analiz Pro — Buton Rehberi',
    info_video_btns:     '🎥 Video sayfasında görünen butonlar',
    info_channel_btns:   '📺 Kanal sayfasında görünen butonlar',
    info_always_btns:    '🛠️ Her zaman görünen araçlar',
    info_dna_method:     '🧬 DNA Puan Metodolojisi',
    btn_info_close:      '↩ Geri Dön',

    // ── Smart Suggestion ──
    suggestion_badge:    '🔥 AKILLI SEÇİM',
    btn_dismiss:         'Kapat',
  },

  en: {
    // ── Header ──
    logo_sub:             'Viral Cloning Engine',
    btn_info_title:       'How It Works?',
    btn_fullscreen_title: 'Open Fullscreen',
    server_checking:      'Checking...',
    server_online:        '● Online',
    server_offline:       '● Offline',
    footer_server:        'Server:',

    // ── Login ──
    login_hint:          'Log in to connect to the ecosystem.',
    login_username_ph:   'Username',
    login_password_ph:   'Password',
    btn_login:           'Login',
    login_loading:       'Logging in...',
    login_error_empty:   'Username and password are required.',
    login_error_server:  'Could not connect to server.',
    login_error_fail:    'Login failed.',

    // ── Dashboard ──
    welcome_text:        'Welcome,',
    btn_logout_title:    'Logout',
    recent_title:        'My Recent Analyses',
    recent_loading:      'Loading...',
    recent_empty:        'No analyses yet.',
    recent_error:        'Could not fetch data.',

    // ── Rabbit Hole ──
    rabbit_title:        '🐇 Rabbit Hole (Niche Finder)',
    rabbit_placeholder:  'e.g. Crypto',
    btn_rabbit:          'Find',

    // ── Buttons ──
    btn_clone:           '🚀 Clone',
    btn_debate:          '⚔️ Debate',
    btn_dna:             '🧬 DNA',
    btn_analyze:         '⚔️ Guerrilla Strategy',
    btn_channel_dna:     '📊 Success Formula',

    // ── Loading ──
    loading_main:        'AI is analyzing the concept',
    loading_sub_default: 'Fetching transcript...',
    loading_sub_page:    'Reading page data...',
    loading_sub_ai:      'AI is generating concepts...',
    loading_sub_channel: 'Exploiting competitor data... Preparing Battle Report!',
    loading_sub_rabbit:  'Diving deep into YouTube... (This may take 15-30 sec)',
    loading_sub_debate:  'Persona A vs B battling...',
    loading_sub_battle:  '⚔️ Agents Clashing... Judge Deciding...',

    // ── Result ──
    result_badge:        '✅ Concept Ready!',
    btn_reset:           '↩ New Video',

    // ── Debate ──
    debate_badge:        '⚔️ Debate Completed!',
    debate_critic_label: '🔬 Critic',
    debate_wizard_label: '🪄 Wizard',
    debate_winner_label: '🏆 WINNING IDEA',
    debate_hook_tag:     'HOOK',
    btn_debate_reset:    '↩ New Video',

    // ── DNA ──
    dna_badge:           '🧬 DNA Analysis Complete!',
    dna_hook_label:      'HOOK',
    dna_tempo_label:     'TEMPO',
    dna_cta_label:       'CTA',
    dna_emotion_label:   'EMOTION',
    dna_howto_btn:       'ℹ️ How is the score calculated?',
    dna_anatomy_label:   '🔬 VIRAL ANATOMY (DNA Summary)',
    dna_prompt_label:    '🔑 DNA MASTER PROMPT',
    btn_copy_dna:        '📋 COPY DNA PROMPT',
    btn_dna_reset:       '↩ New Video',
    copied:              'Copied!',
    info_strat_mode:     'You are in Strategy Mode.',
    info_strat_desc:     'You are on a video page. <strong>Smart Buttons</strong> are active.',
    info_strat_v_ana:    'Viral Anatomy:</strong> Understand why the video blew up (or why it flopped).',
    info_intel_mode:     'You are in Intelligence Mode.',
    info_intel_desc:     'You are on a channel page.',

    info_clone_desc:     'Analyzes the open YouTube video and generates <strong>3 viral content ideas</strong> tailored to your channel. Each idea includes a title, a hook, and a thumbnail suggestion. The system automatically classifies the video into <strong>5 tiers</strong> based on its view velocity.',
    info_debate_desc:    'Pits two distinct AI personas against each other: <strong style="color:#f87171;">🔬 Ruthless Critic</strong> (tells you what won\'t work) and <strong style="color:#a78bfa;">🪄 Viral Wizard</strong> (offers high-potential concepts). The single strongest idea is synthesized as the 🏆 "Winning Idea".',
    info_dna_desc:       'Analyzes the video\'s subtitles to measure 4 metrics: <span style="color:#f43f5e;">🪝 Hook</span> (first 20%), <span style="color:#06b6d4;">⏱️ Tempo</span> (rhythm), <span style="color:#22c55e;">📣 CTA</span> (call to action), and <span style="color:#a855f7;">💥 Emotion</span>. This structure is then fed into an AI to generate a <strong>Master Prompt</strong>. If there are no subtitles, an <strong>estimated analysis</strong> is performed from the title and description (yellow warning).',
    info_guerrilla_desc: 'Works when you are on a competitor channel\'s page. It identifies their fastest-accelerating videos and answers "<strong>What is the competitor doing right?</strong>" Ideal for spotting content gaps.',
    info_channel_dna_desc: 'Automatically analyzes the channel\'s last 5 videos. Calculates the DNA score of each video and extracts the channel\'s average <strong>Hook, Tempo, CTA, and Emotion</strong> scores. The AI summarizes the channel\'s "Success Formula".',
    info_rabbit_desc:    'Search box: type a keyword (e.g., "Crypto"). The system identifies the fastest accelerating (<strong>Outlier</strong>) video in that niche and offers clonable ideas. Use as a visionary tool before jumping into a trend.',
    info_matrix_desc:    'Works without pressing any buttons. As you browse the YouTube homepage, it automatically adds a 🔥 TREND badge and neon green outline to videos reaching <strong>5,000+ views/hour</strong>. Spot viral content at a glance.',
    info_dna_method_desc:'The Overall DNA Score is not a simple average. It is weighted according to the science of viral success:<br><br><span style="color:#f43f5e;">Hook ×0.40</span> + <span style="color:#06b6d4;">Tempo ×0.40</span> + <span style="color:#a855f7;">Emotion ×0.10</span> + <span style="color:#22c55e;">CTA ×0.10</span><br><br>🔥 <strong>Viral Monster Bonus:</strong> If Hook and Tempo are both >75, +20 points.<br>🛡️ <strong>Elite Protection:</strong> If both are ≥80, CTA/Emotion receive a minimum of 50 credits.<br>👑 90+ Legendary  🔥 75-89 Viral  ✅ 50-74 Strong  ⚠️ 0-49 Room to Improve',
    info_intel_chaos:    'Chaos Metric:</strong> See competitor\'s anger and tempo analysis.',
    info_exp_mode:       'You are in Discovery Mode.',
    info_exp_desc:       'You are on the YouTube Home Page or Search results. Free roam.',



    // ── Missing from patch ──
    sugg_video:          'Bu videoyu analiz etmeye hazır mısın?',
    sugg_channel:        'Kanalın en hızlı yükselen videosunu klonla!',
    views_per_day:       'izlenme/gün',
    no_views_data:       'izlenme verisi yok',
    views:               'izlenme',
    sub_ratio:           'Abone oranı',
    algo_spread:         'Algoritma yayılımı',
    velocity:            'Hız',
    channel:             'Kanal',
    watch:               'İzle',
    compat_analysis:     'Uyumluluk Analizi',
    chaos_metric:        'KAOS METRİĞİ',
    viral_anatomy_hit:   'VİRAL ANATOMİ: Bu Video Neden Patladı?',
    std_anatomy:         'STANDART ANATOMİ: Bu Video Nasıl Kurgulanmış?',
    loading_sub_channel_dna: 'Kanalın son 5 videosunun altyazıları çekiliyor ve DNA puanları hesaplanıyor... (Bu işlem 30-60 sn sürebilir)',
    channel_dna_title:   'KANAL DNA\'SI',
    vids_analyzed:       'video analiz edildi',
    weighted_dna_avg:    'Ağırlıklı DNA Ortalaması',
    no_sub_warning:      'videoda altyazı bulunamadı; bu videolar başlık verisiyle tahmini olarak dahil edildi.',
    success_formula:     'BAŞARI FORMÜLÜ',
    overall_dna_score:   'Genel DNA Skoru',
    tier_mega_viral:     'MEGA VİRAL',
    tier_viral_pot_high: 'VİRAL POTANSİYEL (Yüksek izlenme potansiyeli)',
    tier_viral_pot:      'VİRAL POTANSİYEL',
    tier_strong:         'GÜÇLÜ KANAL',
    tier_improve_full:   'GELİŞTİRİLEBİLİR (Güçlenebilecek yönler var)',
    tier_improve:        'GELİŞTİRİLEBİLİR',
    hook_power:          'Kanca Gücü',
    tempo_rhythm:        'Tempo Ritmi',
    emotion_load:        'Duygu Yükü',
    cta_power:           'CTA Gücü',
    desc_hook:           'Giriş bölümündeki tetikleyici yoğunluğu',
    desc_tempo:          'Cümle varyansı ve geçiş akışkanlığı',
    desc_emotion:        'Duygusal kelime yoğunluğu',
    desc_cta:            'Sonuçtaki aksiyon çağrısı etkinliği',
    error_not_ch_msg:    'Kanal DNA analizi yalnızca YouTube kanal sayfalarında çalışır.',
    error_login_ch_msg:  'Kanal DNA analizi için giriş yapmanız gerekir.',
    algo_breaker:        'Algoritma kırıcı — sistemi çıkart, kazayı kopyalama.',


    // ── Missing from patch ──
    sugg_video:          'Would you like to analyze this video?',
    sugg_channel:        'Clone the fastest growing video of the channel!',
    views_per_day:       'views/day',
    no_views_data:       'no views data',
    views:               'views',
    sub_ratio:           'Sub ratio',
    algo_spread:         'Algorithm spread',
    velocity:            'Velocity',
    channel:             'Channel',
    watch:               'Watch',
    compat_analysis:     'Compatibility Analysis',
    chaos_metric:        'CHAOS METRIC',
    viral_anatomy_hit:   'VIRAL ANATOMY: Why Did This Video Blow Up?',
    std_anatomy:         'STANDARD ANATOMY: How Is This Video Structured?',
    loading_sub_channel_dna: 'Extracting subtitles of the last 5 videos and calculating DNA scores... (This may take 30-60 secs)',
    channel_dna_title:   'CHANNEL DNA',
    vids_analyzed:       'videos analyzed',
    weighted_dna_avg:    'Weighted DNA Average',
    no_sub_warning:      'videos had no subtitles; they were estimated using title data.',
    success_formula:     'SUCCESS FORMULA',
    overall_dna_score:   'Overall DNA Score',
    tier_mega_viral:     'MEGA VIRAL',
    tier_viral_pot_high: 'VIRAL POTENTIAL (Strong view potential)',
    tier_viral_pot:      'VIRAL POTENTIAL',
    tier_strong:         'STRONG CHANNEL',
    tier_improve_full:   'ROOM TO IMPROVE (Some areas could be stronger)',
    tier_improve:        'ROOM TO IMPROVE',
    hook_power:          'Hook Power',
    tempo_rhythm:        'Tempo Rhythm',
    emotion_load:        'Emotion Load',
    cta_power:           'CTA Power',
    desc_hook:           'Trigger density in the intro',
    desc_tempo:          'Sentence variance and transition fluidity',
    desc_emotion:        'Emotional word density',
    desc_cta:            'Call to action effectiveness at the end',
    error_not_ch_msg:    'Channel DNA analysis only works on YouTube channel pages.',
    error_login_ch_msg:  'You must log in for Channel DNA analysis.',
    algo_breaker:        'Algorithm breaker — take out the system, copy the accident.',
    // ── Missing from patch ──
    sugg_video:          'Would you like to analyze this video?',
    sugg_channel:        'Clone the fastest growing video of the channel!',
    views_per_day:       'views/day',
    no_views_data:       'no views data',
    views:               'views',
    sub_ratio:           'Sub ratio',
    algo_spread:         'Algorithm spread',
    velocity:            'Velocity',
    channel:             'Channel',
    watch:               'Watch',
    compat_analysis:     'Compatibility Analysis',
    chaos_metric:        'CHAOS METRIC',
    viral_anatomy_hit:   'VIRAL ANATOMY: Why Did This Video Blow Up?',
    std_anatomy:         'STANDARD ANATOMY: How Is This Video Structured?',
    loading_sub_channel_dna: 'Extracting subtitles of the last 5 videos and calculating DNA scores... (This may take 30-60 secs)',
    channel_dna_title:   'CHANNEL DNA',
    vids_analyzed:       'videos analyzed',
    weighted_dna_avg:    'Weighted DNA Average',
    no_sub_warning:      'videos had no subtitles; they were estimated using title data.',
    success_formula:     'SUCCESS FORMULA',
    overall_dna_score:   'Overall DNA Score',
    tier_mega_viral:     'MEGA VIRAL',
    tier_viral_pot_high: 'VIRAL POTENTIAL (Strong view potential)',
    tier_viral_pot:      'VIRAL POTENTIAL',
    tier_strong:         'STRONG CHANNEL',
    tier_improve_full:   'ROOM TO IMPROVE (Some areas could be stronger)',
    tier_improve:        'ROOM TO IMPROVE',
    hook_power:          'Hook Power',
    tempo_rhythm:        'Tempo Rhythm',
    emotion_load:        'Emotion Load',
    cta_power:           'CTA Power',
    desc_hook:           'Trigger density in the intro',
    desc_tempo:          'Sentence variance and transition fluidity',
    desc_emotion:        'Emotional word density',
    desc_cta:            'Call to action effectiveness at the end',
    error_not_ch_msg:    'Channel DNA analysis only works on YouTube channel pages.',
    error_login_ch_msg:  'You must log in for Channel DNA analysis.',
    algo_breaker:        'Algorithm breaker — take out the system, copy the accident.',


    // ── Error ──
    error_default_title: 'An error occurred',
    btn_retry:           '↩ Try Again',
    error_server_off:    '🔴 Server Offline',
    error_server_msg:    'YT Analyzer Pro desktop app is not running.',
    error_no_tab:        '🔗 Tab Not Found',
    error_no_tab_msg:    'Could not find the YouTube video tab to analyze.',
    error_not_yt:        '📺 YouTube Page Required',
    error_not_yt_msg:    'This extension only works on YouTube video pages.',
    error_not_ch:        '📺 Channel Page Required',
    error_not_ch_msg:    'This action only works on YouTube channel pages.',
    error_login_req:     '🔐 Login Required',
    error_login_ch_msg:  'You must be logged in for channel analysis.',
    error_extract:       '❌ Data Extraction Error',
    error_script:        '❌ Script Error',
    error_video_notfound:'❌ Video Data Not Found',
    error_video_refresh: 'Please refresh the video page.',
    error_op_fail:       '⚠️ Operation Failed',
    error_connect:       '🔌 Connection Error',
    error_no_keyword:    '⚠️ Missing Info',
    error_no_keyword_msg:'Please enter a keyword (niche) to search.',
    error_debate_fail:   '⚔️ Debate Failed',

    // ── Info Panel ──
    info_title:          'ℹ️ YT Analyzer Pro — Button Guide',
    info_video_btns:     '🎥 Buttons shown on video pages',
    info_channel_btns:   '📺 Buttons shown on channel pages',
    info_always_btns:    '🛠️ Always visible tools',
    info_dna_method:     '🧬 DNA Score Methodology',
    btn_info_close:      '↩ Go Back',

    // ── Smart Suggestion ──
    suggestion_badge:    '🔥 SMART PICK',
    btn_dismiss:         'Close',
  }
};

// ── Active language state ──────────────────────────────────────────────────────
let _currentLang = 'tr';

/**
 * Translate key → current language string.
 * Fallback: TR string → raw key
 */
function t(key) {
  return (TRANSLATIONS[_currentLang] && TRANSLATIONS[_currentLang][key])
    || (TRANSLATIONS['tr'] && TRANSLATIONS['tr'][key])
    || key;
}

/**
 * Set language, save to chrome.storage.local, refresh UI.
 */
async function setLang(lang) {
  if (!TRANSLATIONS[lang]) return;
  _currentLang = lang;
  try {
    await chrome.storage.local.set({ ui_lang: lang });
  } catch (e) { /* storage not available in content scripts */ }
  applyTranslations();
  updateLangToggle();
}

/**
 * Load language from chrome.storage.local on startup.
 */
async function loadLang() {
  try {
    const res = await chrome.storage.local.get(['ui_lang']);
    if (res.ui_lang && TRANSLATIONS[res.ui_lang]) {
      _currentLang = res.ui_lang;
    }
  } catch (e) { /* ignore */ }
}

/**
 * Returns the current language code ('tr' or 'en').
 */
function getCurrentLang() {
  return _currentLang;
}

/**
 * Apply translations to all [data-i18n] elements in the DOM.
 */
function applyTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = t(key);
    if (el.tagName === 'INPUT' && el.hasAttribute('placeholder')) {
      el.placeholder = val;
    } else {
      el.textContent = val;
    }
  });

  // title attributes
  document.querySelectorAll('[data-i18n-title]').forEach(el => {
    el.title = t(el.getAttribute('data-i18n-title'));
  });
}

/**
 * Update the TR/EN toggle button appearance.
 */
function updateLangToggle() {
  const btn = document.getElementById('btn-lang-toggle');
  if (!btn) return;
  if (_currentLang === 'tr') {
    btn.textContent = 'EN';
    btn.title = 'Switch to English';
  } else {
    btn.textContent = 'TR';
    btn.title = "Türkçe'ye geç";
  }
}
