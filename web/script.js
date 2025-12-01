// 전역 상태
let isLoggedIn = false;
let subscriptionsLoaded = false;
let currentSubscriptions = [];

// DOM 요소
const loginSection = document.getElementById('login-section');
const searchSection = document.getElementById('search-section');
const btnLogin = document.getElementById('btn-login');
const btnSetup = document.getElementById('btn-setup');
const btnLogout = document.getElementById('btn-logout');
const btnLoadSubs = document.getElementById('btn-load-subs');
const btnViewSubs = document.getElementById('btn-view-subs');
const btnRefreshSubs = document.getElementById('btn-refresh-subs');
const btnSearch = document.getElementById('btn-search');
const configStatus = document.getElementById('config-status');
const subsInfo = document.getElementById('subs-info');
const progressSection = document.getElementById('progress-section');
const progressFill = document.getElementById('progress-fill');
const progressText = document.getElementById('progress-text');
const resultsSection = document.getElementById('results-section');
const resultsCount = document.getElementById('results-count');
const resultsStats = document.getElementById('results-stats');
const resultsList = document.getElementById('results-list');

// 구독 목록 모달
const subsModal = document.getElementById('subs-modal');
const btnCloseSubsModal = document.getElementById('btn-close-subs-modal');
const subsModalCount = document.getElementById('subs-modal-count');
const subsList = document.getElementById('subs-list');

// API 설정 모달
const setupModal = document.getElementById('setup-modal');
const btnCloseSetupModal = document.getElementById('btn-close-setup-modal');
const btnSaveConfig = document.getElementById('btn-save-config');
const inputClientId = document.getElementById('input-client-id');
const inputClientSecret = document.getElementById('input-client-secret');
const inputApiKey = document.getElementById('input-api-key');

// 초기화
document.addEventListener('DOMContentLoaded', async () => {
    await checkConfigAndAuth();
    setupEventListeners();
});

async function checkConfigAndAuth() {
    const status = await eel.get_config_status()();

    if (status.isAuthenticated) {
        showSearchSection();
        // 자동으로 구독 채널 불러오기
        loadSubscriptions(false);
    } else {
        showLoginSection();
        updateConfigStatus(status);
    }
}

function updateConfigStatus(status) {
    if (status.isConfigured) {
        configStatus.textContent = 'API 설정 완료';
        configStatus.classList.add('ready');
        btnLogin.disabled = false;
        btnLogin.style.display = 'block';
        btnSetup.style.display = 'none';
    } else {
        configStatus.textContent = '먼저 API 설정이 필요합니다.';
        configStatus.classList.remove('ready');
        btnLogin.disabled = true;
        btnLogin.style.display = 'none';
        btnSetup.style.display = 'block';
    }
}

function setupEventListeners() {
    // 로그인
    btnLogin.addEventListener('click', async () => {
        btnLogin.disabled = true;
        btnLogin.textContent = '로그인 중...';

        try {
            const result = await eel.do_login()();

            if (result.success) {
                showSearchSection();
                loadSubscriptions(false);
                return;
            } else {
                alert('로그인 실패: ' + result.error);
            }
        } catch (e) {
            console.error('로그인 오류:', e);
            alert('로그인이 취소되었거나 오류가 발생했습니다.');
        }

        // 실패 또는 취소 시 버튼 복구
        btnLogin.disabled = false;
        btnLogin.textContent = 'Google 계정으로 로그인';
    });

    // 로그아웃
    btnLogout.addEventListener('click', async () => {
        if (confirm('로그아웃하시겠습니까? 캐시도 함께 삭제됩니다.')) {
            await eel.do_logout()();
            showLoginSection();
            subscriptionsLoaded = false;
            currentSubscriptions = [];
            await checkConfigAndAuth();
        }
    });

    // 구독 채널 불러오기
    btnLoadSubs.addEventListener('click', () => loadSubscriptions(false));
    btnRefreshSubs.addEventListener('click', () => loadSubscriptions(true));

    // 채널 목록 보기
    btnViewSubs.addEventListener('click', openSubsModal);
    btnCloseSubsModal.addEventListener('click', closeSubsModal);
    subsModal.addEventListener('click', (e) => {
        if (e.target === subsModal) closeSubsModal();
    });

    // 필터 타입 변경
    document.querySelectorAll('input[name="filter-type"]').forEach(radio => {
        radio.addEventListener('change', (e) => {
            const isNormal = e.target.value === 'normal';
            document.getElementById('normal-filter').style.display = isNormal ? 'flex' : 'none';
            document.getElementById('mutation-filter').style.display = isNormal ? 'none' : 'flex';
        });
    });

    // 검색
    btnSearch.addEventListener('click', searchVideos);

    // API 설정 모달
    btnSetup.addEventListener('click', openSetupModal);
    btnCloseSetupModal.addEventListener('click', closeSetupModal);
    setupModal.addEventListener('click', (e) => {
        if (e.target === setupModal) closeSetupModal();
    });
    btnSaveConfig.addEventListener('click', saveConfig);
}

// API 설정 모달 함수
async function openSetupModal() {
    // 기존 설정 불러오기
    const config = await eel.get_current_config()();
    inputClientId.value = config.clientId || '';
    inputClientSecret.value = config.clientSecret || '';
    inputApiKey.value = config.apiKey || '';
    setupModal.style.display = 'flex';
}

function closeSetupModal() {
    setupModal.style.display = 'none';
}

async function saveConfig() {
    const clientId = inputClientId.value.trim();
    const clientSecret = inputClientSecret.value.trim();
    const apiKey = inputApiKey.value.trim();

    if (!clientId || !clientSecret) {
        alert('Client ID와 Client Secret은 필수입니다.');
        return;
    }

    btnSaveConfig.disabled = true;
    btnSaveConfig.textContent = '저장 중...';

    try {
        const result = await eel.save_api_config(clientId, clientSecret, apiKey)();

        if (result.success) {
            alert('API 설정이 저장되었습니다.');
            closeSetupModal();
            await checkConfigAndAuth();
        } else {
            alert('저장 실패: ' + result.error);
        }
    } catch (e) {
        alert('오류가 발생했습니다.');
        console.error(e);
    }

    btnSaveConfig.disabled = false;
    btnSaveConfig.textContent = '저장';
}

function showLoginSection() {
    isLoggedIn = false;
    loginSection.style.display = 'flex';
    searchSection.style.display = 'none';
}

function showSearchSection() {
    isLoggedIn = true;
    loginSection.style.display = 'none';
    searchSection.style.display = 'flex';
    subsInfo.textContent = '';
}

async function loadSubscriptions(forceRefresh) {
    btnLoadSubs.disabled = true;
    btnLoadSubs.textContent = '로딩...';

    try {
        const result = await eel.load_subscriptions(forceRefresh)();

        if (result.success) {
            currentSubscriptions = result.subscriptions;
            subscriptionsLoaded = true;

            subsInfo.textContent = `${currentSubscriptions.length}개` +
                (result.fromCache ? ' (캐시)' : '');
            subsInfo.classList.add('loaded');

            btnSearch.disabled = false;
            btnViewSubs.style.display = 'inline-block';
            btnRefreshSubs.style.display = 'inline-block';
        } else {
            subsInfo.textContent = '오류';
            subsInfo.classList.remove('loaded');
            alert('오류: ' + result.error);
        }
    } catch (e) {
        subsInfo.textContent = '오류';
        console.error(e);
    }

    btnLoadSubs.disabled = false;
    btnLoadSubs.textContent = '채널 불러오기';
}

// 구독 목록 모달
function openSubsModal() {
    subsModal.style.display = 'flex';
    renderSubsList();
}

function closeSubsModal() {
    subsModal.style.display = 'none';
}

function renderSubsList() {
    subsModalCount.textContent = `(${currentSubscriptions.length}개)`;

    if (currentSubscriptions.length === 0) {
        subsList.innerHTML = '<p style="text-align:center;color:#666;padding:20px;">구독 채널이 없습니다.</p>';
        return;
    }

    // 구독자수 내림차순 정렬
    const sortedSubs = [...currentSubscriptions].sort((a, b) =>
        (b.subscriberCount || 0) - (a.subscriberCount || 0)
    );

    subsList.innerHTML = sortedSubs.map(sub => `
        <div class="subs-item" data-channel-id="${sub.id}">
            <img src="${sub.thumbnail}" alt="${escapeHtml(sub.title)}">
            <div class="subs-item-info">
                <div class="subs-item-title">${escapeHtml(sub.title)}</div>
                <div class="subs-item-count">구독자 ${formatSubscriberCount(sub.subscriberCount)}</div>
            </div>
            <button class="btn-unsubscribe" onclick="unsubscribeChannel('${sub.id}', this)">구독취소</button>
        </div>
    `).join('');
}

async function unsubscribeChannel(channelId, btn) {
    if (!confirm('이 채널의 구독을 취소하시겠습니까?')) {
        return;
    }

    btn.disabled = true;
    btn.textContent = '취소 중...';

    try {
        const result = await eel.unsubscribe_channel(channelId)();

        if (result.success) {
            // 로컬 목록에서 제거
            currentSubscriptions = currentSubscriptions.filter(s => s.id !== channelId);

            // UI 업데이트
            const item = btn.closest('.subs-item');
            item.style.opacity = '0.5';
            setTimeout(() => {
                item.remove();
                subsModalCount.textContent = `(${currentSubscriptions.length}개)`;
                subsInfo.textContent = `${currentSubscriptions.length}개 채널 로드됨 (캐시)`;
            }, 300);
        } else {
            alert('구독 취소 실패: ' + result.error);
            btn.disabled = false;
            btn.textContent = '구독취소';
        }
    } catch (e) {
        alert('오류가 발생했습니다.');
        console.error(e);
        btn.disabled = false;
        btn.textContent = '구독취소';
    }
}

async function searchVideos() {
    if (!subscriptionsLoaded) {
        alert('먼저 구독 채널을 불러와주세요.');
        return;
    }

    const filterType = document.querySelector('input[name="filter-type"]:checked').value;
    const filterConfig = {
        filterType: filterType,
        maxSubscribers: parseInt(document.getElementById('max-subscribers').value) || 10000,
        minViews: parseInt(document.getElementById('min-views').value) || 10000,
        daysWithin: parseInt(document.getElementById('days-within').value) || 15,
        mutationRatio: parseFloat(document.getElementById('mutation-ratio').value) || 1.0
    };

    btnSearch.disabled = true;
    progressSection.style.display = 'block';
    resultsSection.style.display = 'none';
    progressFill.style.width = '0%';
    progressText.textContent = '검색 준비 중...';

    try {
        const result = await eel.search_videos(filterConfig)();

        progressSection.style.display = 'none';

        if (result.success) {
            displayResults(result.videos, result.stats);
        } else {
            alert('검색 실패: ' + result.error);
        }
    } catch (e) {
        progressSection.style.display = 'none';
        alert('오류가 발생했습니다.');
        console.error(e);
    }

    btnSearch.disabled = false;
}

// Python에서 호출하는 진행률 업데이트 함수
eel.expose(update_progress);
function update_progress(text, percent) {
    progressFill.style.width = percent + '%';
    progressText.textContent = text;
}

function displayResults(videos, stats, filterType) {
    resultsSection.style.display = 'block';
    resultsCount.textContent = `(${videos.length}개)`;
    resultsStats.textContent = `전체 ${stats.total}개 중 ${stats.filtered}개 필터됨`;

    if (videos.length === 0) {
        resultsList.innerHTML = '<p style="text-align:center;color:#666;padding:40px;">조건에 맞는 영상이 없습니다.</p>';
        return;
    }

    // 정렬: 일반=조회수, 돌연변이=지수
    const currentFilter = document.querySelector('input[name="filter-type"]:checked').value;
    const sortedVideos = [...videos].sort((a, b) => {
        if (currentFilter === 'normal') {
            return b.viewCount - a.viewCount;
        } else {
            return b.ratio - a.ratio;
        }
    });

    resultsList.innerHTML = sortedVideos.map(video => `
        <div class="video-item" onclick="window.open('https://www.youtube.com/watch?v=${video.videoId}', '_blank')">
            <div class="video-thumbnail">
                <img src="${video.thumbnail}" alt="${escapeHtml(video.title)}">
                <span class="video-duration">${formatDuration(video.duration)}</span>
            </div>
            <div class="video-info">
                <div class="video-title">${escapeHtml(video.title)}</div>
                <div class="video-meta">
                    <span class="channel">${escapeHtml(video.channelTitle)}</span>
                    <span class="separator">|</span>
                    <span>조회수 <span class="highlight">${formatNumber(video.viewCount)}</span>회</span>
                    <span class="separator">|</span>
                    <span>구독자 ${formatNumber(video.subscriberCount)}명</span>
                    <span class="separator">|</span>
                    <span>돌연변이지수 <span class="highlight">${video.ratio}x</span></span>
                    <span class="separator">|</span>
                    <span>${formatDate(video.publishedAt)}</span>
                    <button class="btn-copy" onclick="copyTitle(event, '${escapeHtml(video.title).replace(/'/g, "\\'")}')">복사</button>
                </div>
            </div>
        </div>
    `).join('');
}

// 유틸리티 함수
function formatNumber(num) {
    if (num >= 10000) {
        return (num / 10000).toFixed(1) + '만';
    }
    return num.toLocaleString();
}

function formatSubscriberCount(count) {
    if (!count) return '비공개';
    if (count >= 10000) {
        return (count / 10000).toFixed(1) + '만명';
    }
    return count.toLocaleString() + '명';
}

function formatDuration(seconds) {
    const h = Math.floor(seconds / 3600);
    const m = Math.floor((seconds % 3600) / 60);
    const s = seconds % 60;

    if (h > 0) {
        return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`;
    }
    return `${m}:${s.toString().padStart(2, '0')}`;
}

function formatDate(isoString) {
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    const days = Math.floor(diff / (1000 * 60 * 60 * 24));

    if (days === 0) return '오늘';
    if (days === 1) return '어제';
    if (days < 7) return `${days}일 전`;
    if (days < 30) return `${Math.floor(days / 7)}주 전`;
    return `${Math.floor(days / 30)}개월 전`;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function copyTitle(event, title) {
    event.stopPropagation(); // 영상 클릭 방지
    navigator.clipboard.writeText(title).then(() => {
        const btn = event.target;
        const originalText = btn.textContent;
        btn.textContent = '복사됨!';
        btn.classList.add('copied');
        setTimeout(() => {
            btn.textContent = originalText;
            btn.classList.remove('copied');
        }, 1500);
    }).catch(err => {
        console.error('복사 실패:', err);
        alert('복사에 실패했습니다.');
    });
}
