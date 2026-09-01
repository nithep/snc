
'use strict';
/* ═══════════════════════════ i18n ═══════════════════════════ */
const I18N = {
  th: {
    appTitle: 'Smart Nurse Call (SNC)', appSubtitle: 'ระบบเฝ้าระวังสายเรียกพยาบาลเรียลไทม์',
    connLive: 'เชื่อมต่อสด', connConnecting: 'กำลังเชื่อมต่อ...', connReconnect: 'กำลังเชื่อมต่อใหม่ (ครั้งที่ {n})...', connOffline: 'ออฟไลน์ — กำลังพยายามเชื่อมต่อ',
    backendOk: 'Backend ปกติ', backendSlow: 'Backend ช้า', backendDown: 'Backend ไม่ตอบสนอง',
    kpiTitle: 'ตัวชี้วัดประสิทธิภาพ (KPI)', roomsTitle: 'สถานะห้องพักตามเวลาจริง',
    historyTitle: 'ประวัติเหตุการณ์ล่าสุด', historyNote: 'แสดง 3 เหตุการณ์ล่าสุด',
    searchPlaceholder: 'ค้นหาเลขห้อง เช่น 0401...',
    filterAll: 'ทั้งหมด', filterActive: 'กำลังเรียก', filterAck: 'รับเรื่องแล้ว', filterResolved: 'เสร็จสิ้น',
    exportCsv: 'Export CSV',
    colTime: 'วัน-เวลา', colRoom: 'ห้อง', colType: 'ประเภทเหตุการณ์', colStatus: 'สถานะ',
    colAck: 'เวลารับเรื่อง', colRes: 'เวลาเคลียร์', colSla: 'SLA',
    loading: 'กำลังโหลดข้อมูล...', noEvents: 'ไม่พบเหตุการณ์ในฐานข้อมูล', noMatch: 'ไม่พบรายการที่ตรงกับการค้นหา',
    lastUpdated: 'อัปเดตล่าสุด', autoRefreshNote: 'รีเฟรชอัตโนมัติทุก 10 วินาที + เรียลไทม์ผ่าน WebSocket',
    activeCalls: 'สายค้าง', today: 'วันนี้', total: 'ทั้งหมด', breachCount: 'เกิน SLA', compliance: 'SLA ปฏิบัติตาม',
    avgAck: 'ค่าเฉลี่ยเวลารับเรื่อง', avgRes: 'ค่าเฉลี่ยเวลาเคลียร์',
    targetAck: 'เป้าหมาย ≤ 30 วิ', targetRes: 'เป้าหมาย ≤ 180 วิ', targetComp: 'เป้าหมาย ≥ 98%',
    statusNormal: 'ปกติ', statusEmergency: 'เรียกฉุกเฉิน', statusAck: 'รับเรื่องแล้ว',
    evBedside: 'เรียกข้างเตียง', evBathroom: 'ฉุกเฉินห้องน้ำ', evTalking: 'พยาบาลคุย',
    evCleared: 'เคลียร์สาย', evInfo: 'อัปเดตข้อมูล', evTriggered: 'เรียก (ทดสอบ)', evAck: 'รับเรื่อง',
    btnAck: 'รับเรื่อง', btnClear: 'เคลียร์สาย', btnIdle: 'พร้อมรับสาย',
    sinceLabel: 'เริ่มเมื่อ', ackBreach: 'เกินเกณฑ์รับเรื่อง', resBreach: 'เกินเกณฑ์เวลา',
    slaOk: 'ผ่าน', slaBreach: 'เกิน SLA', slaWithin: 'ภายใน SLA', slaPass: 'ผ่าน',
    statusPending: 'รอรับเรื่อง', statusResolved: 'เสร็จสิ้น', roomWord: 'ห้อง',
    evTitleBedside: 'เรียกพยาบาล — กดปุ่ม', evTitleBathroom: 'ฉุกเฉิน — ดึงสาย Call Cord', evTitleHandset: 'เรียกพยาบาล — ยกหูโทรศัพท์',
    devCord: 'NCX-CORD', devPull: 'NCX-PULL', devHandset: 'Handset',
    aiTitle: 'สรุปประจำวัน (AI)', aiHint: 'กดเพื่อโหลดบทสรุปจาก Gemini (ต้องตั้งค่า GEMINI_API_KEY บนเซิร์ฟเวอร์)', aiUnavailable: 'ไม่สามารถสร้างสรุป AI ได้ (ตรวจสอบ GEMINI_API_KEY บนเซิร์ฟเวอร์)',
    kpiViewOverall: 'รวมทั้งระบบ', kpiViewRoom: 'รายห้อง', kpiViewType: 'รายประเภทเหตุการณ์',
    statusStripTitle: 'สถานะห้องปัจจุบัน',
    settingsTitle: 'การตั้งค่า', settingsSub: 'ตั้งค่าเพื่อใช้งานบนระบบจริง — ค่าจะถูกบันทึกไว้ในเบราว์เซอร์นี้',
    apiKeyLabel: 'API Key (X-API-Key)', apiKeyHint: 'จำเป็นสำหรับปุ่มรับเรื่อง/เคลียร์/ทดสอบ ถ้าเซิร์ฟเวอร์ตั้ง SNC_API_KEY ไว้ (ถ้าไม่ตั้ง = ไม่ต้องกรอก)',
    hostLabel: 'Backend Host (ไม่บังคับ)', hostHint: 'เว้นว่าง = ใช้เซิร์ฟเวอร์เดียวกับที่เปิดหน้านี้ (รองรับ HTTPS tunnel อัตโนมัติ)',
    soundLabel: 'เสียงเตือนเรียกฉุกเฉิน',
    saveBtn: 'บันทึก', cancelBtn: 'ยกเลิก', settingsSaved: 'บันทึกการตั้งค่าแล้ว',
    authError: 'เซิร์ฟเวอร์ปฏิเสธการเขียน (401) — เปิดการตั้งค่า ⚙️ แล้วกรอก API Key ให้ถูกต้อง',
    opFailed: 'ดำเนินการไม่สำเร็จ', opOk: 'ดำเนินการสำเร็จ',
    ackDone: 'รับเรื่องห้อง {room} แล้ว', clearDone: 'เคลียร์สายห้อง {room} แล้ว', triggerDone: 'ส่งสัญญาณจำลองห้อง {room} แล้ว',
    demoTest: 'DEMO', demoTestSending: 'กำลังส่งสัญญาณจำลอง…', demoTestDone: 'ส่งสัญญาณจำลองแล้ว (DEMO — ไม่นับ KPI)', demoTestFail: 'ส่งสัญญาณจำลองไม่สำเร็จ', demoTestReset: 'DEMO เคลียร์แล้ว — ระบบพร้อมใช้งาน',
    footerNote: 'เซิร์ฟเวอร์หลัก Raspberry Pi 4', liveFeed: 'ฟีดสด WebSocket',
    eventsByType: 'จำนวนเหตุการณ์แยกตามประเภท',
    modeDemo: 'โหมดสาธิตจำลอง',
    modeReal: 'ระบบจริง (Production)'
  },
  en: {
    appTitle: 'Smart Nurse Call (SNC)', appSubtitle: 'Nurse Station Live Monitor',
    connLive: 'Live', connConnecting: 'Connecting...', connReconnect: 'Reconnecting (attempt {n})...', connOffline: 'Offline — retrying',
    backendOk: 'Backend OK', backendSlow: 'Backend Slow', backendDown: 'Backend Down',
    kpiTitle: 'Key Performance Indicators (KPI)', roomsTitle: 'Real-time Room Status',
    historyTitle: 'Recent Events', historyNote: 'Showing latest 3 events',
    searchPlaceholder: 'Search room e.g. 0401...',
    filterAll: 'All', filterActive: 'Active', filterAck: 'Acknowledged', filterResolved: 'Resolved',
    exportCsv: 'Export CSV',
    colTime: 'Timestamp', colRoom: 'Room', colType: 'Event Type', colStatus: 'Status',
    colAck: 'Ack Time', colRes: 'Resolution', colSla: 'SLA',
    loading: 'Loading...', noEvents: 'No events found', noMatch: 'No records match your search',
    lastUpdated: 'Last updated', autoRefreshNote: 'Auto-refresh every 10s + live via WebSocket',
    activeCalls: 'Active calls', today: 'Today', total: 'Total', breachCount: 'SLA breaches', compliance: 'SLA Compliance',
    avgAck: 'Avg Ack Time', avgRes: 'Avg Resolution Time',
    targetAck: 'Target ≤ 30s', targetRes: 'Target ≤ 180s', targetComp: 'Target ≥ 98%',
    statusNormal: 'Normal', statusEmergency: 'EMERGENCY', statusAck: 'Acknowledged',
    evBedside: 'Bedside Call', evBathroom: 'Bathroom Emergency', evTalking: 'Nurse Talking',
    evCleared: 'Call Cleared', evInfo: 'Info Update', evTriggered: 'Call (test)', evAck: 'Acknowledged',
    btnAck: 'Acknowledge', btnClear: 'Clear Call', btnIdle: 'Ready',
    sinceLabel: 'Since', ackBreach: 'Ack SLA exceeded', resBreach: 'Resolution SLA exceeded',
    slaOk: 'OK', slaBreach: 'BREACHED', slaWithin: 'Within SLA', slaPass: 'Pass',
    statusPending: 'Pending', statusResolved: 'Completed', roomWord: 'Room',
    evTitleBedside: 'Nurse Call — Button Press', evTitleBathroom: 'Emergency — Call Cord Pull', evTitleHandset: 'Nurse Call — Handset',
    devCord: 'NCX-CORD', devPull: 'NCX-PULL', devHandset: 'Handset',
    aiTitle: 'Daily AI Summary', aiHint: 'Click to load Gemini summary (requires GEMINI_API_KEY on server)', aiUnavailable: 'AI summary unavailable (check GEMINI_API_KEY on server)',
    kpiViewOverall: 'Overall', kpiViewRoom: 'By Room', kpiViewType: 'By Event Type',
    statusStripTitle: 'Current room status',
    settingsTitle: 'Settings', settingsSub: 'Configure for production use — values are saved in this browser',
    apiKeyLabel: 'API Key (X-API-Key)', apiKeyHint: 'Required for Ack/Clear/Test buttons if server has SNC_API_KEY set (leave blank if not configured)',
    hostLabel: 'Backend Host (optional)', hostHint: 'Leave empty = use the same server that serves this page (HTTPS tunnel auto-supported)',
    soundLabel: 'Emergency alarm sound',
    saveBtn: 'Save', cancelBtn: 'Cancel', settingsSaved: 'Settings saved',
    authError: 'Server rejected write (401) — open Settings ⚙️ and enter a valid API Key',
    opFailed: 'Operation failed', opOk: 'Operation succeeded',
    ackDone: 'Room {room} acknowledged', clearDone: 'Room {room} cleared', triggerDone: 'Simulated call sent for room {room}',
    demoTest: 'DEMO', demoTestSending: 'Sending demo call…', demoTestDone: 'Demo call sent (DEMO — not counted in KPI)', demoTestFail: 'Failed to send demo call', demoTestReset: 'DEMO cleared — system ready',
    footerNote: 'Primary server: Raspberry Pi 4', liveFeed: 'WebSocket Live Feed',
    eventsByType: 'Events by type',
    modeDemo: 'Demo Simulation Mode',
    modeReal: 'Production Active'
  }
};
let LANG = (localStorage.getItem('snc_lang') || 'th');
const t = (k, vars) => {
  let s = (I18N[LANG] && I18N[LANG][k]) || I18N.th[k] || k;
  if (vars) for (const key of Object.keys(vars)) s = s.split('{' + key + '}').join(vars[key]);
  return s;
};

/* ═══════════════════════════ Config ═══════════════════════════ */
const isFile = location.protocol === 'file:';
const q = new URLSearchParams(location.search);

let cfg = {
  apiKey: q.get('api_key') || q.get('key') || localStorage.getItem('snc_api_key') || '',
  host: localStorage.getItem('snc_backend_host') || '',
  sound: localStorage.getItem('snc_sound') !== '0',
  sourceMode: 'real' // Force Production Mode for index.html
};

function updateModeIndicator() {
  const badge = document.getElementById('modeBadge');
  if (badge) {
    badge.style.display = 'inline-flex';
    badge.className = 'mode-badge real';
    badge.textContent = t('modeReal');
  }
}

function apiUrl(path) {
  const host = cfg.host || (isFile ? '192.168.1.94:8000' : '');
  if (!host) return path; // served by backend → relative (works over HTTPS tunnel)
  // Use http for custom host (backend likely not https)
  const proto = cfg.host ? 'http://' : (location.protocol === 'https:' ? 'https://' : 'http://');
  return proto + host + path;
}
function wsUrl() {
  const host = cfg.host || (isFile ? '192.168.1.94:8000' : location.host);
  // Use ws for custom host (backend likely not wss)
  const proto = cfg.host ? 'ws://' : (location.protocol === 'https:' ? 'wss://' : 'ws://');
  return proto + host + '/ws/nurse-station';
}
function authHeaders(extra) {
  const h = Object.assign({}, extra || {});
  if (cfg.apiKey) h['X-API-Key'] = cfg.apiKey;
  return h;
}

/* ═══════════════════════════ State ═══════════════════════════ */
const roomStates = {};   // roomId -> {status, eventType, startedAt, source}
let allEvents = [];
let kpiData = null;
let ws = null;
let wsRetry = 0;
let wsReconnectTimer = null;
let wsManualClose = false;
let wsLastMsgAt = 0;             // ล่าสุดที่ได้รับข้อความ/pong จาก server (ตรวจจับสายค้างที่ onclose ไม่ fire)
let wsPongSeen = false;          // server ตอบ pong แล้ว (รองรับ heartbeat) — เท่านั้นที่จะบังคับ reconnect เอง
let alarmTimer = null;

/* ═══════════════════════════ Toast ═══════════════════════════ */
function toast(msg, type) {
  const wrap = document.getElementById('toastWrap');
  const el = document.createElement('div');
  el.className = 'toast ' + (type || '');
  el.textContent = msg;
  wrap.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity .4s'; setTimeout(() => el.remove(), 420); }, 3600);
}

/* ═══════════════════════════ API helpers ═══════════════════════════ */
async function apiGet(path) {
  const res = await fetch(apiUrl(path));
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}
async function apiWrite(path, body) {
  const opts = { method: 'POST', headers: authHeaders({ 'Content-Type': 'application/json' }) };
  if (body) opts.body = JSON.stringify(body);
  const res = await fetch(apiUrl(path), opts);
  if (res.status === 401) { toast(t('authError'), 'err'); openSettings(); throw new Error('401'); }
  if (!res.ok) throw new Error('HTTP ' + res.status);
  return res.json();
}

/* ═══════════════════════════ Formatters ═══════════════════════════ */
const fmtTime = new Intl.DateTimeFormat(LANG === 'th' ? 'th-TH' : 'en-US', { hour: '2-digit', minute: '2-digit', second: '2-digit' });
const fmtDT = new Intl.DateTimeFormat(LANG === 'th' ? 'th-TH' : 'en-US', { year: 'numeric', month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit', second: '2-digit' });
function formatDT(iso) { if (!iso) return '—'; const d = new Date(iso); return isNaN(d) ? iso : fmtDT.format(d); }
function formatClock(d) { return fmtTime.format(d); }
function formatTimer(secs) {
  secs = Math.max(0, Math.floor(secs));
  const h = Math.floor(secs / 3600), m = Math.floor((secs % 3600) / 60), s = secs % 60;
  return (h > 0 ? String(h).padStart(2, '0') + ':' : '') + String(m).padStart(2, '0') + ':' + String(s).padStart(2, '0');
}
function eventTypeMeta(evType, status) {
  const e = (evType || '').toUpperCase();
  if (status === 'acknowledged' || e === 'ACKNOWLEDGED' || e === 'NURSE_TALKING') return { icon: '📞', label: t('evAck') };
  if (e === 'CALL_BATHROOM_EMERGENCY') return { icon: '🚿', label: t('evBathroom') };
  if (e === 'CALL_BEDSIDE') return { icon: '🛎️', label: t('evBedside') };
  if (e === 'CALL_TRIGGERED') return { icon: '🛎️', label: t('evTriggered') };
  if (e === 'CALL_CLEARED') return { icon: '✅', label: t('evCleared') };
  if (e === 'INFO_UPDATE') return { icon: 'ℹ️', label: t('evInfo') };
  return { icon: '🔔', label: evType || '—' };
}
function shortRoom(id) {
  const m = String(id || '').match(/\d+/);
  return m ? m[0] : String(id || '—');
}
function formatClockISO(iso) { if (!iso) return '—'; const d = new Date(iso); return isNaN(d) ? '—' : fmtTime.format(d); }
function eventCardMeta(evType) {
  const e = String(evType || '').toUpperCase();
  if (e === 'CALL_BATHROOM_EMERGENCY') return { title: t('evTitleBathroom'), dev: t('devPull') };
  if (e === 'CALL_BEDSIDE') return { title: t('evTitleBedside'), dev: t('devCord') };
  if (e === 'NURSE_TALKING' || e === 'CALL_HANDSET' || e === 'OFFHOOK') return { title: t('evTitleHandset'), dev: t('devHandset') };
  if (e === 'ACKNOWLEDGED') return { title: t('evAck'), dev: '' };
  if (e === 'CALL_CLEARED') return { title: t('evCleared'), dev: '' };
  if (e === 'CALL_TRIGGERED') return { title: t('evTriggered'), dev: '' };
  if (e === 'INFO_UPDATE') return { title: t('evInfo'), dev: '' };
  return { title: evType || '—', dev: '' };
}
function slaBadgeFor(ev) {
  const s = String(ev.status || '').toLowerCase();
  const resolved = s === 'resolved' || s === 'cleared' || s === 'completed';
  const acked = s === 'acknowledged' || s === 'ack';
  if (resolved) {
    return ev.sla_breached
      ? '<span class="badge-sla breach">⛔ ' + t('slaBreach') + '</span>'
      : '<span class="badge-sla ok">✓ ' + t('slaPass') + ' ' + formatTimer(ev.resolution_time_seconds || 0) + '</span>';
  }
  const over = acked
    ? ((ev.ack_time_seconds != null && ev.ack_time_seconds > 30) || !!ev.sla_breached)
    : ((Date.now() - Date.parse(ev.timestamp)) / 1000 > 30);
  return over
    ? '<span class="badge-sla breach">⛔ ' + t('slaBreach') + '</span>'
    : '<span class="badge-sla ok">✓ ' + t('slaWithin') + '</span>';
}
function roomDisplayName(id) {
  const num = parseInt(id, 10);
  
  // Special handling for Floor 11 Rajavithi Hospital layout
  if (id === '1100') return LANG === 'th' ? 'สถานีพยาบาลหลัก (KEY-1100)' : 'Main Nurse Station (KEY-1100)';
  if (id.startsWith('11')) {
    if (LANG === 'th') return 'ห้องพักผู้ป่วย ' + id;
    return 'Patient Room ' + id;
  }

  // Fallback for other rooms or legacy IDs
  const label = LANG === 'th' ? 'ห้อง' : 'Room';
  return isNaN(num) ? id : label + ' ' + String(num).padStart(4, '0');
}

/* ═══════════════════════════ Data loading ═══════════════════════════ */
async function loadEvents() {
  try {
    const data = await apiGet('/api/events?source=' + cfg.sourceMode);
    allEvents = (data.events || []);
    
    // Force-create Floor 11 rooms if no events are found (Fallback for empty DB)
    if (allEvents.length === 0) {
      console.log("No events found, pre-populating Floor 11 rooms...");
      for (let i = 1101; i <= 1127; i++) {
        roomStates[String(i)] = { status: 'normal', eventType: null, startedAt: null, source: 'init' };
      }
      roomStates['KEY-1100'] = { status: 'normal', eventType: null, startedAt: null, source: 'init' };
      roomStates['DISPLAY-1100'] = { status: 'normal', eventType: null, startedAt: null, source: 'init' };
    } else {
      syncRoomStates();
    }
    
    renderRooms();
    renderHistory();
    renderKpi();
    renderLastUpdated();
  } catch (err) {
    console.warn('loadEvents failed:', err);
    if (allEvents.length === 0) renderHistoryError();
  }
}
async function loadKpi() {
  try {
    kpiData = await apiGet('/api/analytics/kpi?source=' + cfg.sourceMode);
    renderKpi();
  } catch (err) { console.warn('loadKpi failed:', err); }
}

/* ═══════════════════════════ KPI View (รวม / รายห้อง / รายประเภท) ═══════════════════════════ */
let kpiViewSel = localStorage.getItem('snc_kpi_view') || 'overall';
function kpiGroupsBy(keyFn) {
  const g = {};
  for (const ev of allEvents) {
    const k = String(keyFn(ev) || '—');
    if (!g[k]) g[k] = { total: 0, acks: [], ress: [], breach: 0 };
    const o = g[k];
    o.total++;
    if (ev.ack_time_seconds != null) o.acks.push(ev.ack_time_seconds);
    if (ev.resolution_time_seconds != null) o.ress.push(ev.resolution_time_seconds);
    if (ev.sla_breached) o.breach++;
  }
  return Object.entries(g).map(([key, v]) => ({
    key, total: v.total,
    avg_ack: v.acks.length ? v.acks.reduce((a, b) => a + b, 0) / v.acks.length : null,
    avg_res: v.ress.length ? v.ress.reduce((a, b) => a + b, 0) / v.ress.length : null,
    breach: v.breach,
    compliance: v.total ? ((v.total - v.breach) / v.total) * 100 : 100
  }));
}
function renderKpiAlt(view) {
  const wrap = document.getElementById('kpiAlt');
  if (!wrap) return;
  const rows = view === 'room'
    ? kpiGroupsBy(ev => ev.room_id).sort((a, b) => b.total - a.total || a.key.localeCompare(b.key))
    : kpiGroupsBy(ev => ev.event_type).sort((a, b) => b.total - a.total);
  const nameFn = view === 'room' ? (k => roomDisplayName(k)) : (k => eventTypeMeta(k, '').label);
  let html = '<div class="table-wrap"><table><thead><tr>' +
    '<th>' + (view === 'room' ? t('colRoom') : t('colType')) + '</th>' +
    '<th>' + t('total') + '</th><th>' + t('avgAck') + '</th><th>' + t('avgRes') + '</th>' +
    '<th>' + t('breachCount') + '</th><th>' + t('compliance') + '</th></tr></thead><tbody>';
  if (!rows.length) {
    html += '<tr><td colspan="6" style="text-align:center;color:var(--text-faint);padding:2rem">' + t('noEvents') + '</td></tr>';
  }
  for (const r of rows) {
    html += '<tr><td class="room-cell">' + escapeHtml(nameFn(r.key)) + '</td>' +
      '<td class="mono">' + r.total + '</td>' +
      '<td class="mono">' + (r.avg_ack != null ? r.avg_ack.toFixed(1) + 's' : '—') + '</td>' +
      '<td class="mono">' + (r.avg_res != null ? r.avg_res.toFixed(1) + 's' : '—') + '</td>' +
      '<td class="mono" style="color:' + (r.breach ? 'var(--red)' : 'var(--green)') + '">' + r.breach + '</td>' +
      '<td class="mono" style="color:' + (r.compliance >= 98 ? 'var(--green)' : 'var(--amber)') + '">' + r.compliance.toFixed(1) + '%</td></tr>';
  }
  html += '</tbody></table></div>';
  wrap.innerHTML = html;
}
async function loadHealth() {
  const pill = document.getElementById('healthPill');
  const dot = document.getElementById('healthDot');
  const txt = document.getElementById('healthText');
  try {
    const t0 = performance.now();
    await apiGet('/health');
    const ms = Math.round(performance.now() - t0);
    pill.className = 'pill ' + (ms > 800 ? 'warn' : 'ok');
    dot.className = 'dot pulse';
    txt.textContent = t(ms > 800 ? 'backendSlow' : 'backendOk') + ' · ' + ms + 'ms';
  } catch (e) {
    pill.className = 'pill danger';
    dot.className = 'dot';
    txt.textContent = t('backendDown');
  }
}
function renderLastUpdated() {
  document.getElementById('lastUpdatedText').textContent = formatClock(new Date());
}

/* ═══════════════════════════ Room states from server (SoT) ═══════════════════════════ */
function syncRoomStates() {
  const latest = {};
  for (const ev of allEvents) {
    if (!latest[ev.room_id] || String(ev.timestamp) > String(latest[ev.room_id].timestamp)) latest[ev.room_id] = ev;
  }
  for (const roomId of Object.keys(roomStates)) {
    if (!latest[roomId]) { roomStates[roomId].status = 'normal'; roomStates[roomId].startedAt = null; }
  }
  for (const [roomId, ev] of Object.entries(latest)) {
    const st = (ev.status || '').toLowerCase();
    const prev = roomStates[roomId];
    if (st === 'active' || st === 'triggered') {
      if (!prev) { roomStates[roomId] = { status: 'emergency', eventType: ev.event_type, startedAt: ev.timestamp, source: 'server' }; }
      else {
        // การเรียกซ้ำภายในห้องเดิม: อัปเดตชนิดเหตุการณ์ (เช่น escalate เป็นห้องน้ำ) แต่คงเวลาเริ่มต้น SLA ไว้
        prev.status = 'emergency';
        prev.eventType = ev.event_type;
        if (!prev.startedAt) prev.startedAt = ev.timestamp;
      }
    } else if (st === 'acknowledged' || st === 'ack') {
      if (!prev) { roomStates[roomId] = { status: 'ack', eventType: ev.event_type, startedAt: ev.timestamp, source: 'server' }; }
      else { prev.status = 'ack'; prev.eventType = ev.event_type; if (!prev.startedAt) prev.startedAt = ev.timestamp; }
    } else {
      if (!prev) { roomStates[roomId] = { status: 'normal', eventType: ev.event_type, startedAt: null, source: 'server' }; }
      else { prev.status = 'normal'; prev.startedAt = null; }
    }
  }
}

/* ═══════════════════════════ Status Strip (สถานะห้องปัจจุบัน) ═══════════════════════════ */
function renderStatusStrip() {
  const el = document.getElementById('statusStrip');
  if (!el) return;
  const vals = Object.entries(roomStates).filter(([id]) => !HIDDEN_ROOMS.includes(id)).map(([, s]) => s);
  const em = vals.filter(s => s.status === 'emergency').length;
  const ack = vals.filter(s => s.status === 'ack').length;
  const norm = vals.filter(s => s.status === 'normal').length;
  el.innerHTML =
    '<span class="stat-chip st-ok">✅ ' + t('statusNormal') + ' <b>' + norm + '</b></span>' +
    '<span class="stat-chip st-em">🚨 ' + t('statusEmergency') + ' <b>' + em + '</b></span>' +
    '<span class="stat-chip st-ack">⏳ ' + t('statusAck') + ' <b>' + ack + '</b></span>';
}

/* ═══════════════════════════ Render: rooms ═══════════════════════════ */
// ห้องที่ไม่มีตัวตนบนตู้จริง (as-built: PBX_PORT_ROOM_MAPPING) — ซ่อนออกจาก grid
const HIDDEN_ROOMS = ['1116', '0400'];
function renderRooms() {
  const grid = document.getElementById('roomGrid');
  renderStatusStrip();
  
  // Pre-populate Floor 11 rooms if roomStates is empty (Initial Load)
  if (Object.keys(roomStates).length === 0) {
    // Patient Rooms 1101-1127
    for (let i = 1101; i <= 1127; i++) {
      if (HIDDEN_ROOMS.includes(String(i))) continue;
      roomStates[String(i)] = { status: 'normal', eventType: null, startedAt: null, source: 'init' };
    }
    // Nurse Station & Display
    roomStates['KEY-1100'] = { status: 'normal', eventType: null, startedAt: null, source: 'init' };
    roomStates['DISPLAY-1100'] = { status: 'normal', eventType: null, startedAt: null, source: 'init' };
  }

  const rooms = Object.entries(roomStates).filter(([id]) => !HIDDEN_ROOMS.includes(id));
  if (rooms.length === 0) {
    grid.innerHTML = '<div class="empty-state"><span class="big">📡</span><span>' + t('noEvents') + '</span></div>';
    updateBanner(); updateAlarm(); return;
  }
  // เรียงลำดับ: emergency (เวลานานสุดก่อน) → ack → normal (ตามเลขห้อง)
  const now = Date.now();
  const rank = { emergency: 0, ack: 1, normal: 2 };
  rooms.sort((a, b) => {
    const st = roomStates[a[0]], stb = roomStates[b[0]];
    if (rank[st.status] !== rank[stb.status]) return rank[st.status] - rank[stb.status];
    if (st.status !== 'normal') {
      const ea = st.startedAt ? now - Date.parse(st.startedAt) : 0;
      const eb = stb.startedAt ? now - Date.parse(stb.startedAt) : 0;
      return eb - ea;
    }
    return a[0].localeCompare(b[0]);
  });
  grid.innerHTML = rooms.map(([roomId, st]) => roomCard(roomId, st, now)).join('');
  updateBanner();
  updateAlarm();
}
function elapsedOf(st, now) { return st.startedAt ? (now - Date.parse(st.startedAt)) / 1000 : 0; }
function roomCard(roomId, st, now) {
  const elapsed = elapsedOf(st, now);
  const breach = st.status === 'emergency' && elapsed > 180 ? 'over180' : (st.status === 'emergency' && elapsed > 30 ? 'over30' : '');
  const meta = eventTypeMeta(st.eventType, st.status === 'ack' ? 'acknowledged' : st.status);
  let badge = '<span class="room-badge b-normal">' + t('statusNormal') + '</span>';
  let btn = '<button class="btn btn-idle" disabled>' + t('btnIdle') + '</button>';
  if (st.status === 'emergency') {
    badge = '<span class="room-badge b-emergency">🚨 ' + t('statusEmergency') + '</span>';
    btn = '<button class="btn btn-ack" onclick="ackRoom(\'' + roomId + '\')">📞 ' + t('btnAck') + '</button>';
  } else if (st.status === 'ack') {
    badge = '<span class="room-badge b-ack">⏳ ' + t('statusAck') + '</span>';
    btn = '<button class="btn btn-clear" onclick="clearRoom(\'' + roomId + '\')">✅ ' + t('btnClear') + '</button>';
  }
  const chips = [];
  if (st.status !== 'normal' && st.eventType) chips.push('<span class="room-type">' + meta.icon + ' ' + meta.label + '</span>');
  if (st.status === 'emergency' && elapsed > 30) chips.push('<span class="breach-chip">⏰ ' + t('ackBreach') + '</span>');
  if (st.status !== 'normal' && elapsed > 180) chips.push('<span class="breach-chip">🚨 ' + t('resBreach') + '</span>');
  const timerHtml = st.status !== 'normal'
    ? '<div class="room-timer"><span class="t ' + breach + '" data-timer="' + roomId + '">' + formatTimer(elapsed) + '</span><span class="timer-caption">' + t('statusEmergency') + ' SLA</span></div>'
    : '<div class="room-timer"><span class="t" style="color:var(--text-faint)">--:--</span><span class="timer-caption">' + t('statusNormal') + '</span></div>';
  const since = st.status !== 'normal' && st.startedAt
    ? '<div class="room-since">' + t('sinceLabel') + ': ' + formatDT(st.startedAt) + '</div>' : '';
  return '<div class="room-card st-' + st.status + '" id="rc-' + roomId + '" role="status" aria-live="polite">' +
    '<div class="room-top"><div class="room-no">' + roomDisplayName(roomId) + '</div>' + badge + '</div>' +
    (chips.length ? '<div class="room-meta">' + chips.join('') + '</div>' : '') +
    timerHtml + since +
    '<div class="room-actions">' + btn + '</div></div>';
}
function tickTimers() {
  const now = Date.now();
  document.querySelectorAll('[data-timer]').forEach(el => {
    const st = roomStates[el.dataset.timer];
    if (!st || st.status === 'normal' || !st.startedAt) return;
    const elapsed = (now - Date.parse(st.startedAt)) / 1000;
    const breach = st.status === 'emergency' && elapsed > 180 ? 'over180' : (st.status === 'emergency' && elapsed > 30 ? 'over30' : '');
    el.className = 't ' + breach;
    el.textContent = formatTimer(elapsed);
  });
}
function updateBanner() {
  const banner = document.getElementById('emergencyBanner');  const ems = Object.entries(roomStates).filter(([id, s]) => s.status === 'emergency' && !HIDDEN_ROOMS.includes(id))
    .sort((a, b) => elapsedOf(b[1], Date.now()) - elapsedOf(a[1], Date.now()));
  if (ems.length === 0) {
    banner.classList.remove('show');
    document.body.classList.remove('has-emergency');
    document.getElementById('activeCallsPill').style.display = 'none';
    return;
  }
  banner.classList.add('show');
  document.body.classList.add('has-emergency');
  document.getElementById('bannerText').textContent = '🚨 ' + t('activeCalls') + ': ' + ems.length + ' — ' + ems.map(([r]) => roomDisplayName(r)).join(', ');
  const activePill = document.getElementById('activeCallsPill');
  activePill.style.display = 'inline-flex';
  activePill.className = 'pill danger';
  activePill.innerHTML = '<span class="dot"></span>' + ems.length + ' ' + t('activeCalls');
}

/* ═══════════════════════════ Render: KPI ═══════════════════════════ */
function renderKpi() {
  if (!kpiData) return;
  const grid = document.getElementById('kpiGrid');
  const alt = document.getElementById('kpiAlt');
  if (kpiViewSel !== 'overall') {
    grid.style.display = 'none';
    alt.style.display = '';
    renderKpiAlt(kpiViewSel);
    return;
  }
  alt.style.display = 'none';
  grid.style.display = '';
  const now = Date.now();
  const todayCount = allEvents.filter(ev => { const d = new Date(ev.timestamp); return !isNaN(d) && (now - d.getTime()) < 86400000; }).length;
  const compRate = kpiData.sla_compliance_rate != null ? kpiData.sla_compliance_rate : 100;
  const breachCount = kpiData.total_events ? Math.round(kpiData.total_events * (1 - (compRate || 0) / 100)) : 0;
  const ack = kpiData.avg_ack_time_seconds;
  const res = kpiData.avg_resolution_time_seconds;
  const ackCls = ack <= 30 ? 'good' : (ack <= 60 ? 'warn' : 'bad');
  const resCls = res <= 180 ? 'good' : (res <= 300 ? 'warn' : 'bad');
  const compCls = compRate >= 98 ? 'good' : (compRate >= 90 ? 'warn' : 'bad');
  const ackW = Math.min(100, (ack / 30) * 100);
  const resW = Math.min(100, (res / 180) * 100);
  const compW = Math.min(100, compRate);
  const cards = [
    { label: t('avgAck'), value: (ack == null ? '—' : ack), unit: 's', cls: ackCls, w: ackW, barCls: ackCls === 'good' ? 'ok' : (ackCls === 'warn' ? 'warn' : 'bad'), foot: t('targetAck') },
    { label: t('avgRes'), value: (res == null ? '—' : res), unit: 's', cls: resCls, w: resW, barCls: resCls === 'good' ? 'ok' : (resCls === 'warn' ? 'warn' : 'bad'), foot: t('targetRes') },
    { label: t('compliance'), value: (compRate == null ? '—' : compRate.toFixed(1)), unit: '%', cls: compCls, w: compW, barCls: compCls === 'good' ? 'ok' : (compCls === 'warn' ? 'warn' : 'bad'), foot: t('targetComp') },
    { label: t('total'), value: kpiData.total_events || 0, unit: '', cls: '', w: 0, barCls: '', foot: t('today') + ': ' + todayCount },
    { label: t('breachCount'), value: breachCount, unit: '', cls: breachCount > 0 ? 'bad' : 'good', w: 0, barCls: '', foot: kpiData.events_by_type ? '' : '' }
  ];
  grid.innerHTML = cards.map(c => {
    const bar = c.barCls ? '<div class="progress"><i class="' + c.barCls + '" style="width:' + c.w + '%"></i></div>' : '<div class="progress"><i style="width:0%"></i></div>';
    return '<div class="kpi-card"><div class="kpi-label"><span>' + c.label + '</span></div>' +
      '<div class="kpi-value ' + c.cls + '">' + c.value + (c.unit ? '<small>' + c.unit + '</small>' : '') + '</div>' + bar +
      '<div class="kpi-foot">' + c.foot + '</div></div>';
  }).join('');
  // chips: events by type
  const byType = kpiData.events_by_type || {};
  const chips = Object.entries(byType).map(([k, v]) => {
    const m = eventTypeMeta(k, ''); return '<span class="type-chip">' + m.icon + ' ' + m.label + ' <b>' + v + '</b></span>';
  }).join('');
  document.getElementById('typeChips').innerHTML = chips ? '<span class="type-chip" style="border-style:dashed">' + t('eventsByType') + '</span>' + chips : '';
}

/* ═══════════════════════════ Render: History ═══════════════════════════ */
const statusFilterMap = {
  active: ['active', 'triggered'],
  ack: ['acknowledged', 'ack'],
  resolved: ['resolved', 'cleared', 'completed']
};
function filteredEvents() {
  const qry = document.getElementById('searchInput').value.trim().toLowerCase();
  const filter = document.getElementById('statusFilter').value;
  return allEvents.filter(ev => {
    if (qry && !String(ev.room_id).toLowerCase().includes(qry)) return false;
    if (filter !== 'all') {
      const list = statusFilterMap[filter] || [];
      if (!list.includes(String(ev.status || '').toLowerCase())) return false;
    }
    return true;
  });
}
function renderHistory() {
  const body = document.getElementById('historyBody');
  const events = filteredEvents();
  document.getElementById('historyCount').textContent = t('total') + ': ' + allEvents.length + (events.length !== allEvents.length ? ' · ' + t('filterAll') + ': ' + events.length : '');
  if (events.length === 0) {
    body.innerHTML = '<tr><td colspan="6" style="text-align:center;color:var(--text-faint);padding:2rem">' + t(allEvents.length ? 'noMatch' : 'noEvents') + '</td></tr>';
    return;
  }
  // แสดง 3 เหตุการณ์ล่าสุด (ดีไซน์ Nurse Station: badge สีตามสถานะ + เวลาแบบนาฬิกา + SLA)
  const displayLimit = 3;
  body.innerHTML = events.slice(0, displayLimit).map(ev => {
    const s = String(ev.status || '').toLowerCase();
    const resolved = s === 'resolved' || s === 'cleared' || s === 'completed';
    const acked = s === 'acknowledged' || s === 'ack';
    const stCls = resolved ? 'st-resolved' : (acked ? 'st-ack' : 'st-active');
    const badgeCls = resolved ? 'resolved' : (acked ? 'acknowledged' : 'active');
    const statusLabel = resolved ? t('statusResolved') : (acked ? t('statusAck') : t('statusPending'));
    const em = eventCardMeta(ev.event_type);
    const roomNo = shortRoom(ev.room_id);
    const subLine = (em.dev ? em.dev + ' · ' : '') + t('roomWord') + ' ' + roomNo;
    const ackT = formatClockISO(ev.acknowledged_at);
    const resT = formatClockISO(ev.resolved_at);
    return '<tr class="' + (ev.sla_breached ? 'row-breach' : '') + '">' +
      '<td><span class="badge-room ' + stCls + '">' + escapeHtml(roomNo) + '</span></td>' +
      '<td><div class="ev-title">' + escapeHtml(em.title) + '</div><div class="ev-sub">' + escapeHtml(subLine) + '</div></td>' +
      '<td><span class="badge-status ' + badgeCls + '">' + statusLabel + '</span></td>' +
      '<td class="mono" style="color:var(--text-dim)">' + ackT + '</td>' +
      '<td class="mono" style="color:var(--text-dim)">' + resT + '</td>' +
      '<td>' + slaBadgeFor(ev) + '</td></tr>';
  }).join('');
}
function renderHistoryError() {
  document.getElementById('historyBody').innerHTML =
    '<tr><td colspan="6" style="text-align:center;color:var(--text-faint);padding:2rem">⚠️ ' + t('opFailed') + '</td></tr>';
}

/* ═══════════════════════════ Actions ═══════════════════════════ */
async function ackRoom(roomId) {
  try {
    const r = await apiWrite('/api/events/acknowledge/' + roomId);
    setLocalAck(roomId);
    toast(t('ackDone', { room: roomDisplayName(roomId) }), 'ok');
    refreshAfterAction();
  } catch (e) { if (e.message !== '401') toast(t('opFailed'), 'err'); }
}
async function clearRoom(roomId) {
  try {
    const r = await apiWrite('/api/events/clear/' + roomId);
    setLocalNormal(roomId);
    toast(t('clearDone', { room: roomDisplayName(roomId) }), 'ok');
    refreshAfterAction();
  } catch (e) { if (e.message !== '401') toast(t('opFailed'), 'err'); }
}
function setLocalAck(roomId) { if (roomStates[roomId]) { roomStates[roomId].status = 'ack'; renderRooms(); } }
function setLocalNormal(roomId) { if (roomStates[roomId]) { roomStates[roomId].status = 'normal'; roomStates[roomId].startedAt = null; renderRooms(); } }
function setLocalEmergency(roomId, sourceType) {
  const prev = roomStates[roomId];
  if (!prev) { roomStates[roomId] = { status: 'emergency', eventType: sourceType, startedAt: new Date().toISOString(), source: 'ws' }; }
  else { prev.status = 'emergency'; if (sourceType) prev.eventType = sourceType; if (!prev.startedAt) prev.startedAt = new Date().toISOString(); }
  renderRooms();
}
function refreshAfterAction() { loadKpi(); loadEvents(); }

/* ═══════════════════════════ Alarm (Web Audio loop) ═══════════════════════════ */
let audioCtx = null;
function ensureAudio() {
  if (!audioCtx) {
    try { audioCtx = new (window.AudioContext || window.webkitAudioContext)(); } catch (e) {}
  }
  if (audioCtx && audioCtx.state === 'suspended') audioCtx.resume().catch(() => {});
}
function beep(freq, dur) {
  if (!audioCtx) return;
  const osc = audioCtx.createOscillator(), gain = audioCtx.createGain();
  osc.type = 'square'; osc.frequency.value = freq;
  gain.gain.setValueAtTime(0.08, audioCtx.currentTime);
  gain.gain.exponentialRampToValueAtTime(0.001, audioCtx.currentTime + dur);
  osc.connect(gain); gain.connect(audioCtx.destination);
  osc.start(); osc.stop(audioCtx.currentTime + dur);
}
function startAlarm() {
  if (alarmTimer) return;
  ensureAudio();
  alarmTimer = setInterval(() => { beep(880, 0.18); setTimeout(() => beep(660, 0.18), 200); }, 1200);
}
function stopAlarm() {
  if (alarmTimer) { clearInterval(alarmTimer); alarmTimer = null; }
}
function updateAlarm() {
  const anyEm = Object.values(roomStates).some(s => s.status === 'emergency');
  if (anyEm && cfg.sound) startAlarm(); else stopAlarm();
}

/* ═══════════════════════════ WebSocket ═══════════════════════════ */
const WS_MAX_RETRY_MS = 30000;  // ขีดจำกัดสูงสุดของ delay ระหว่าง reconnect
const WS_HEARTBEAT_MS = 15000;   // ความถี่ส่ง ping กัน Cloudflare drop สาย idle (และตรวจความมีชีวิต)
const WS_STALE_MS = 60000;       // ไม่มีข้อความตอบกลับเกินนี้ → ถือว่าสายค้าง บังคับ reconnect
function wsBackoffDelay() {
  // exponential backoff + jitter: 1s → 2s → 4s → 8s → 16s → 30s (cap)
  const base = Math.min(1000 * Math.pow(2, wsRetry), WS_MAX_RETRY_MS);
  return base + Math.floor(Math.random() * 300);
}
function setConnState(state) {
  // state: 'connecting' | 'live' | 'retry' | 'offline'
  const pill = document.getElementById('connPill');
  const dot = document.getElementById('connDot');
  const txt = document.getElementById('connText');
  if (state === 'live') {
    pill.className = 'pill ok';
    dot.className = 'dot pulse';
    txt.textContent = t('connLive');
    pill.title = wsUrl();
  } else if (state === 'connecting') {
    pill.className = 'pill warn';
    dot.className = 'dot';
    txt.textContent = t('connConnecting');
    pill.title = wsUrl();
  } else if (state === 'retry') {
    pill.className = 'pill warn';
    dot.className = 'dot';
    txt.textContent = t('connReconnect', { n: wsRetry });  // wsRetry เพิ่มก่อนเรียกแล้ว
    pill.title = t('connOffline') + ' · ' + wsUrl();
  } else { // offline
    pill.className = 'pill danger';
    dot.className = 'dot';
    txt.textContent = t('connOffline');
    pill.title = wsUrl();
  }
}
function scheduleWsReconnect() {
  const delay = wsBackoffDelay();
  wsReconnectTimer = setTimeout(() => { wsReconnectTimer = null; initWebSocket(); }, delay);
  setConnState('retry');
}
function initWebSocket() {
  // ปิด WS เก่า (ถ้ามี) โดย mark manual close เพื่อกัน onclose ของตัวเก่าไป trigger reconnect ซ้อน
  if (wsReconnectTimer) { clearTimeout(wsReconnectTimer); wsReconnectTimer = null; }
  if (ws && (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING)) {
    wsManualClose = true;
    try { ws.close(); } catch (e) {}
  } else if (ws) {
    // socket เก่าปิดไปแล้ว — อย่า set flag เพราะ close() จะไม่ fire onclose มาล้าง (flag จะติดค้าง)
    wsManualClose = false;
  }
  setConnState('connecting');
  ws = new WebSocket(wsUrl());
  ws.onopen = () => {
    wsRetry = 0;
    wsManualClose = false;  // เปิดสำเร็จแล้ว — สายหลุดครั้งต่อไปคือของจริงเสมอ
    wsLastMsgAt = Date.now();
    setConnState('live');
  };
  ws.onmessage = (ev) => {
    try {
      const data = JSON.parse(ev.data);
      wsLastMsgAt = Date.now();  // ทุกข้อความ (รวม pong/ที่ถูก filter) = หลักฐานว่าสายยังมีชีวิต
      if (data.type === 'pong') { wsPongSeen = true; }  // server รองรับ heartbeat → เปิดการบังคับ reconnect
      const ext = data.extension || {};
      
      // Filter out events that do not match the current mode (demo vs real)
      const msgSource = ext.source || 'real';
      if (msgSource !== cfg.sourceMode) {
        return;
      }

      const room = ext.roomId;
      if (!room) return;
      const content = (data.payload && data.payload[0] && data.payload[0].contentString) || '';
      const sourceType = ext.sourceEventType || content;
      const status = String(data.status || '').toLowerCase();
      if (status === 'active' || content === 'CALL_TRIGGERED' || content === 'CALL_BEDSIDE' || content === 'CALL_BATHROOM_EMERGENCY') {
        setLocalEmergency(room, sourceType);
      } else if (status === 'acknowledged' || content === 'ACKNOWLEDGED' || content === 'NURSE_TALKING') {
        setLocalAck(room);
      } else if (status === 'resolved' || content === 'CALL_CLEARED') {
        setLocalNormal(room);
      }
      loadEvents();
      loadKpi();
    } catch (err) { console.warn('WS message parse failed:', err); }
  };
  ws.onclose = () => {
    // ปิดจากฝั่งเราเอง (เปลี่ยน host/รีโหลด) → ไม่ reconnect ซ้อน
    if (wsManualClose) { wsManualClose = false; return; }
    wsRetry++;
    setConnState('offline');
    scheduleWsReconnect();
  };
  ws.onerror = () => { try { ws.close(); } catch (e) {} };
}
// กลับมาที่แท็บแล้ว WS ยังไม่เปิด → ลองเชื่อมใหม่ทันที (กัน backoff ค้างนานเกินจำเป็น)
document.addEventListener('visibilitychange', () => {
  if (!document.hidden && (!ws || ws.readyState === WebSocket.CLOSED) && !wsReconnectTimer) {
    wsRetry = 0;
    initWebSocket();
  }
});

/* ═══════════════════════════ AI Summary ═══════════════════════════ */
let aiLoaded = false;
async function loadAiSummary() {
  if (aiLoaded) return;
  const body = document.getElementById('aiBody');
  body.innerHTML = t('loading') + '…';
  try {
    const data = await apiGet('/api/ai/daily-summary');
    aiLoaded = true;
    body.innerHTML = '<span class="ai-meta">' + formatDT(data.timestamp) + '</span>' + escapeHtml(String(data.ai_summary || data.summary_text || ''));
  } catch (e) {
    body.textContent = t('aiUnavailable');
  }
}
function escapeHtml(s) { return s.replace(/[&<>"']/g, c => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c])); }

/* ═══════════════════════════ CSV Export ═══════════════════════════ */
function exportCsv() {
  const rows = [['timestamp', 'room_id', 'event_type', 'status', 'ack_time_seconds', 'resolution_time_seconds', 'sla_breached']];
  filteredEvents().forEach(ev => {
    rows.push([ev.timestamp, ev.room_id, ev.event_type, ev.status,
      ev.ack_time_seconds != null ? ev.ack_time_seconds : '', ev.resolution_time_seconds != null ? ev.resolution_time_seconds : '', ev.sla_breached ? 1 : 0]);
  });
  const csv = '\uFEFF' + rows.map(r => r.map(v => '"' + String(v).replace(/"/g, '""') + '"').join(',')).join('\r\n');
  const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'snc_events_' + new Date().toISOString().slice(0, 19).replace(/[:T]/g, '-') + '.csv';
  a.click();
  setTimeout(() => URL.revokeObjectURL(a.href), 2000);
}

/* ═══════════════════════════ Settings ═══════════════════════════ */
function openSettings() {
  document.getElementById('apiKeyInput').value = cfg.apiKey;
  document.getElementById('hostInput').value = cfg.host;
  document.getElementById('soundInput').checked = cfg.sound;
  document.getElementById('settingsModal').classList.add('show');
}
function closeSettings() { document.getElementById('settingsModal').classList.remove('show'); }
function saveSettings() {
  cfg.apiKey = document.getElementById('apiKeyInput').value.trim();
  cfg.host = document.getElementById('hostInput').value.trim().replace(/^https?:\/\//, '');
  cfg.sound = document.getElementById('soundInput').checked;
  localStorage.setItem('snc_api_key', cfg.apiKey);
  localStorage.setItem('snc_backend_host', cfg.host);
  localStorage.setItem('snc_sound', cfg.sound ? '1' : '0');
  closeSettings();
  toast(t('settingsSaved'), 'ok');
  updateAlarm();
  initWebSocket(); // เปลี่ยน host แล้วให้ WS เชื่อมไปยัง endpoint ใหม่ทันที
  loadEvents(); loadKpi(); loadHealth();
}

/* ═══════════════════════════ i18n UI ═══════════════════════════ */
function applyI18n() {
  document.documentElement.lang = LANG;
  document.querySelectorAll('[data-i18n-key]').forEach(el => { el.textContent = t(el.dataset.i18nKey); });
  document.querySelectorAll('[data-i18n-ph]').forEach(el => { el.placeholder = t(el.dataset.i18nPh); });
  document.getElementById('statusFilter').innerHTML =
    '<option value="all">' + t('filterAll') + '</option>' +
    '<option value="active">' + t('filterActive') + '</option>' +
    '<option value="ack">' + t('filterAck') + '</option>' +
    '<option value="resolved">' + t('filterResolved') + '</option>';
  document.getElementById('langBtn').textContent = LANG === 'th' ? 'EN' : 'ไทย';
  renderRooms(); renderKpi(); renderHistory();
}
function setLang(l) {
  LANG = l;
  localStorage.setItem('snc_lang', l);
  applyI18n();
  window.location.reload();
}

/* ═══════════════════════════ Fit-to-Screen (พอดี 1 หน้าจอ) ═══════════════════════════ */
// Scale เนื้อหาทั้งหมด (header + main + footer) ให้พอดี viewport 1 หน้าโดยไม่ต้อง scroll — ใช้ได้ทุกแพลตฟอร์ม
// (transform-origin: top center — ยึดบน-กลาง จอ; modal/toast อยู่นอก #appScale จึงไม่ถูก scale)
function fitToScreen() {
  const el = document.getElementById('appScale');
  if (!el) return;
  el.style.transform = 'none';
  const natW = el.scrollWidth;
  const natH = el.scrollHeight;
  if (!natW || !natH) return;
  const vw = window.innerWidth;
  const vh = window.innerHeight;
  // scale ลงเพื่อให้พอดีจอเสมอ (scale > 1 อนุญาตเฉพาะจอใหญ่ เช่น TV 4K แต่จำกัดไม่ให้เบลอเกินไป)
  const scale = Math.min(2, vw / natW, vh / natH);
  el.style.transform = 'scale(' + scale + ')';
}
// เนื้อหาเปลี่ยนขนาด (โหลดห้อง/Banner/AI panel) หรือ viewport เปลี่ยน → ปรับ scale ใหม่
if (typeof ResizeObserver !== 'undefined') {
  new ResizeObserver(fitToScreen).observe(document.getElementById('appScale'));
}
window.addEventListener('resize', fitToScreen);
window.addEventListener('orientationchange', fitToScreen);
if (document.fonts && document.fonts.ready) document.fonts.ready.then(fitToScreen);

/* ═══════════════════════════ Clock ═══════════════════════════ */
setInterval(() => { document.getElementById('clock').textContent = formatClock(new Date()); }, 1000);

/* ═══════════════════════════ Wire up events ═══════════════════════════ */
document.getElementById('settingsBtn').addEventListener('click', openSettings);
document.getElementById('saveSettingsBtn').addEventListener('click', saveSettings);
document.getElementById('cancelSettingsBtn').addEventListener('click', closeSettings);
document.getElementById('settingsModal').addEventListener('click', (e) => { if (e.target === e.currentTarget) closeSettings(); });
document.getElementById('soundBtn').addEventListener('click', () => {
  cfg.sound = !cfg.sound;
  localStorage.setItem('snc_sound', cfg.sound ? '1' : '0');
  document.getElementById('soundBtn').textContent = cfg.sound ? '🔊' : '🔇';
  if (cfg.sound) { ensureAudio(); } updateAlarm();
  toast(t('soundLabel') + ': ' + (cfg.sound ? 'ON' : 'OFF'));
});
document.getElementById('langBtn').addEventListener('click', () => setLang(LANG === 'th' ? 'en' : 'th'));
document.getElementById('exportBtn').addEventListener('click', exportCsv);
document.getElementById('searchInput').addEventListener('input', renderHistory);
document.getElementById('statusFilter').addEventListener('change', renderHistory);
document.getElementById('kpiView').addEventListener('change', () => {
  kpiViewSel = document.getElementById('kpiView').value;
  localStorage.setItem('snc_kpi_view', kpiViewSel);
  renderKpi();
});
document.getElementById('aiPanel').addEventListener('toggle', () => { if (document.getElementById('aiPanel').open) loadAiSummary(); });
document.addEventListener('keydown', (e) => { if (e.key === 'Escape') closeSettings(); });
document.addEventListener('pointerdown', ensureAudio, { once: true });

/* ═══════════════════════════ Boot ═══════════════════════════ */
applyI18n();
fitToScreen();
updateModeIndicator();
document.getElementById('soundBtn').textContent = cfg.sound ? '🔊' : '🔇';
document.getElementById('kpiView').value = kpiViewSel;
initWebSocket();
loadEvents();
loadKpi();
loadHealth();
setInterval(loadEvents, 10000);
setInterval(loadKpi, 30000);
setInterval(loadHealth, 30000);
// Heartbeat WS: ส่ง ping ทุก 15 วิ + บังคับ reconnect ถ้าเงียบเกิน 60 วิ (สายค้างที่ onclose ไม่ fire)
setInterval(() => {
  if (!ws || ws.readyState !== WebSocket.OPEN) return;
  try { ws.send(JSON.stringify({ type: 'ping' })); } catch (e) {}
  if (wsPongSeen && Date.now() - wsLastMsgAt > WS_STALE_MS) {
    console.warn('WS ไม่มีสัญญาณตอบกลับเกิน ' + (WS_STALE_MS / 1000) + 's — บังคับ reconnect');
    wsRetry++;
    setConnState('retry');
    initWebSocket();
  }
}, WS_HEARTBEAT_MS);
setInterval(tickTimers, 1000);
