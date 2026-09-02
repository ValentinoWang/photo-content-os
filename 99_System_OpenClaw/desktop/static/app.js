const state = { csrf: '', projects: [], project: null, settings: null, screen: 'home', wizard: 1, deleteCandidates: [], inboxPlan: null, inboxPlanError: '', assets: [], assetStatistics: null, assetError: '', selectedAsset: null, libraryView: 'grid' };
const $ = selector => document.querySelector(selector);
const esc = value => String(value ?? '').replace(/[&<>'"]/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', "'": '&#39;', '"': '&quot;' })[char]);
const notice = (message, bad = false) => { const node = $('#toast'); node.textContent = message; node.className = `toast show${bad ? ' error' : ''}`; clearTimeout(notice.timer); notice.timer = setTimeout(() => node.className = 'toast', 2600); };

async function api(path, options = {}) {
  const init = { credentials: 'same-origin', ...options, headers: { Accept: 'application/json', ...(options.headers || {}) } };
  if (init.body && typeof init.body !== 'string') { init.body = JSON.stringify(init.body); init.headers['Content-Type'] = 'application/json'; }
  if (init.method && init.method !== 'GET') init.headers['X-Content-OS-CSRF'] = state.csrf;
  const response = await fetch(path, init);
  const payload = await response.json().catch(() => ({ ok: false, error: { message: '服务返回无法读取的内容' } }));
  if (!response.ok || !payload.ok) throw new Error(payload.error?.message || '请求失败');
  return payload;
}

function stage(project) {
  const docs = project.documents || {};
  const value = name => docs[name] && docs[name].version > 1 ? 'done' : '';
  return ['素材归档', '取证分析', '脚本分镜', '剪辑决策', '时间线', '人工精剪'].map((label, index) => `<div class="stage-step ${value(['brief', 'brief', 'script', 'storyboard', 'edl', 'delivery'][index])}"><i></i><span>${label}</span></div>`).join('');
}

function projectCard(project) {
  return `<button class="project-card" data-project-id="${esc(project.id)}"><header><span class="chip">${esc(project.platform || '未指定')}</span><span>r${Number(project.revision || 1)}</span></header><strong>${esc(project.title)}</strong><small>${esc(project.account || '未绑定账号')}</small><div class="progress">${stage(project)}</div></button>`;
}

function renderHome() {
  const target = $('[data-screen-panel="home"]');
  const projects = state.projects.length ? state.projects.map(projectCard).join('') : '<div class="empty"><h2>还没有内容项目</h2><p>从一个项目开始，再连接本地照片和视频。</p><button class="btn btn--pri" data-create>新建项目</button></div>';
  const providers = state.settings?.model_providers || [];
  const upstream = state.settings?.upstream || {};
  target.innerHTML = `<div class="screen-head"><div><p class="eyebrow">本地工作台</p><h2>最近项目</h2></div><button class="btn" data-refresh>刷新</button></div><div class="dashboard-grid"><section class="project-grid">${projects}</section><aside class="rail"><p class="eyebrow">能力状态</p><div class="engine"><span class="dot ${upstream.upstream_features_available ? 'dot--ok' : ''}"></span><div><strong>数据中台</strong><small>${upstream.upstream_features_available ? '已连接上游身份' : '未连接，不影响本地能力'}</small></div></div><div class="engine"><span class="dot dot--ok"></span><div><strong>本机创作能力</strong><small>${providers.length ? `${providers.length} 个模型配置` : '尚未配置模型'}</small></div></div><div class="engine"><span class="dot"></span><div><strong>ChatCut Desktop MCP</strong><small>${state.settings?.chatcut?.available ? '已连接' : '可选连接，未启用'}</small></div></div><button class="btn btn--full" data-screen="settings">管理设置</button></aside></div>`;
  target.querySelectorAll('[data-project-id]').forEach(button => button.onclick = () => selectProject(button.dataset.projectId));
  target.querySelectorAll('[data-create]').forEach(button => button.onclick = openProjectDialog);
  target.querySelector('[data-refresh]').onclick = bootstrap;
  target.querySelector('[data-screen="settings"]').onclick = () => showScreen('settings');
}

function batchCard(id, title, details, selected = false) {
  return `<button class="batch ${selected ? 'selected' : ''}" data-batch="${id}" aria-selected="${selected}"><span class="thumb">${id.toUpperCase()}</span><span><strong>${title}</strong><small>${details}</small></span><i>›</i></button>`;
}

function renderInbox() {
  const target = $('[data-screen-panel="inbox"]');
  const batches = state.inboxPlan?.batches || [];
  const selectedBatch = batches[0] || null;
  const list = batches.length ? batches.map((batch, index) => batchCard(batch.batch_id, `事件 ${batch.batch_id}`, `${batch.media_ids.length} 个文件 · 待确认`, index === 0)).join('') : '<div class="asset-empty"><h3>尚无可确认的批次</h3><p>' + esc(state.inboxPlanError || '为项目连接本地素材目录并生成媒体清单后，系统会在这里生成仅供确认的事件计划。') + '</p></div>';
  const batchDetail = selectedBatch ? `<div class="panel-heading"><div><span class="chip chip--ai">自动分批建议</span><h3>事件 ${esc(selectedBatch.batch_id)}</h3><p>根据拍摄时间、位置和不可拆分的实况照片组生成。</p></div><span class="chip">待确认</span></div>${selectedBatch.media_ids.map(mediaId => `<div class="media-row"><span class="media">媒体</span><span><strong>${esc(mediaId)}</strong><small>来源清单中的媒体编号</small></span></div>`).join('')}<div class="decision-row"><label><input type="radio" name="destination" checked> 进入项目</label><label><input type="radio" name="destination">仅归档</label><button class="btn btn--pri" id="confirm-batch">确认落点</button></div>` : '<div class="panel-heading"><div><h3>等待媒体清单</h3><p>分批计划只读取已连接项目的当前媒体清单；未生成计划时不会创建目录或移动媒体。</p></div></div>';
  target.innerHTML = `<div class="screen-head"><div><p class="eyebrow">整理台</p><h2>按事件整理本地素材</h2><p class="muted">素材留在本机。自动建议只会生成批次计划；迁移、归档与回收站操作都需要你的确认。</p></div><button class="btn" id="reanalyze">重新分析</button></div><div class="split"><aside class="list-panel">${list}</aside><section class="detail-panel">${batchDetail}<section class="delete-box"><header><div><span class="chip chip--warn">推荐删除</span><p>仅显示可机器验证的原因；每项均需勾选和二次确认。</p></div><span id="delete-number">0</span></header>${['d1', 'd2', 'd3'].map((id, index) => `<label class="delete-row" data-del="${id}"><input type="checkbox" data-delete="${id}"><span><strong>${['时长过短的误触片段', '哈希完全重复', '相机低清代理'][index]}</strong><small>${['0.3 秒，低于策略阈值', '与 IMG_0241 完全相同', '原片已存在'][index]}</small></span></label>`).join('')}<button class="btn danger" id="confirm-delete" disabled>移入系统回收站</button></section></section></div>`;
  target.querySelectorAll('[data-batch]').forEach(button => button.onclick = () => { target.querySelectorAll('[data-batch]').forEach(node => node.classList.remove('selected')); button.classList.add('selected'); });
  target.querySelectorAll('[data-delete]').forEach(box => box.onchange = () => { const selected = target.querySelectorAll('[data-delete]:checked').length; $('#delete-number').textContent = String(selected); target.querySelector('#confirm-delete').disabled = !selected; });
  target.querySelector('#confirm-batch')?.addEventListener('click', () => notice('确认批次需要在项目迁移流程中选择落点后执行。'));
  target.querySelector('#reanalyze').onclick = async () => { await loadInboxPlan(); renderInbox(); notice(state.inboxPlan ? '已根据当前媒体清单重新生成批次计划。' : state.inboxPlanError, !state.inboxPlan); };
  target.querySelector('#confirm-delete').onclick = () => notice('请先在真实候选清单中完成二次确认。', true);
}

function renderLibrary() {
  const target = $('[data-screen-panel="library"]');
  const statistics = state.assetStatistics || { categories: [], tags: [], asset_count: 0 };
  const assets = state.assets || [];
  const assetCards = assets.length ? assets.map(asset => `<button class="document-card" data-asset-id="${esc(asset.asset_id)}"><header><div><span class="chip">${esc(asset.category)}</span><h3>${esc(asset.title)}</h3></div><span class="chip">${esc(asset.public_status)}</span></header><p>${esc((asset.tags || []).join(' · ') || '未标记')}</p></button>`).join('') : `<div class="asset-empty"><h3>尚未建立结构化索引</h3><p>${esc(state.assetError || '注册本地素材后，这里会显示可筛选的分类、标签、用途、计数和详情。')}</p></div>`;
  const detail = state.selectedAsset ? `<p class="eyebrow">详情</p><h3>${esc(state.selectedAsset.title)}</h3><p>${esc((state.selectedAsset.uses || []).join(' · ') || '尚未标记用途')}</p><button class="btn" data-asset-add-project>加入项目</button>` : '<p class="eyebrow">详情</p><h3>选择一项素材</h3><p>详情栏只显示可公开的结构化信息，不暴露本机绝对路径。</p><button class="btn" disabled>加入项目</button>';
  target.innerHTML = `<div class="screen-head"><div><p class="eyebrow">素材库</p><h2>可复用素材</h2><p class="muted">分类、标签和用途来自结构化素材索引。</p></div><div class="segmented"><button data-library-view="grid" class="${state.libraryView === 'grid' ? 'active' : ''}">网格</button><button data-library-view="list" class="${state.libraryView === 'list' ? 'active' : ''}">列表</button><button data-library-view="cards" class="${state.libraryView === 'cards' ? 'active' : ''}">卡片</button></div></div><div class="library-layout"><aside class="tree"><button aria-current="true">全部素材 <i>${statistics.asset_count || 0}</i></button>${statistics.categories.map(category => `<button data-category="${esc(category.name)}">${esc(category.name)} <i>${category.asset_count}</i></button>`).join('')}</aside><section><div class="filters"><button aria-pressed="true" data-tags="">全部标签</button>${statistics.tags.map(tag => `<button data-tags="${esc(tag.name)}">${esc(tag.name)}</button>`).join('')}</div><div class="document-grid" data-library-results>${assetCards}</div></section><aside class="asset-detail">${detail}</aside></div>`;
  target.querySelectorAll('[data-library-view]').forEach(button => button.onclick = () => { state.libraryView = button.dataset.libraryView; renderLibrary(); });
  target.querySelectorAll('[data-category], [data-tags]').forEach(button => button.onclick = async () => { await loadLibrary(button.dataset.category || '', button.dataset.tags || ''); renderLibrary(); });
  target.querySelectorAll('[data-asset-id]').forEach(button => button.onclick = async () => { try { state.selectedAsset = (await api(`/api/assets/${encodeURIComponent(button.dataset.assetId)}`)).asset; renderLibrary(); } catch (error) { notice(error.message, true); } });
  target.querySelector('[data-asset-add-project]')?.addEventListener('click', () => notice('素材已准备好；请选择项目后再写入项目引用。'));
}

function renderProject() {
  const target = $('[data-screen-panel="project"]');
  if (!state.project) { target.innerHTML = '<div class="empty"><h2>先选择一个项目</h2><p>项目屏保留 Brief、脚本、锁定范围、版本、失效提示、参考资料和复盘。</p><button class="btn btn--pri" data-screen="home">返回工作台</button></div>'; target.querySelector('button').onclick = () => showScreen('home'); return; }
  const project = state.project;
  const documents = Object.entries(project.documents || {}).map(([name, document]) => `<article class="document-card"><header><div><span class="chip">${esc(document.label || name)}</span><h3>${esc(document.label || name)}</h3></div><span class="chip ${document.stale ? 'chip--warn' : 'chip--ok'}">${document.stale ? '需要更新' : `v${document.version}`}</span></header><p>${document.blocks?.filter(block => block.locked).length || 0} 个区块已锁定，AI 只可修改你选中的未锁定内容。</p><button class="btn" data-open-document="${esc(name)}">查看与编辑</button></article>`).join('');
  target.innerHTML = `<div class="screen-head"><div><p class="eyebrow">项目</p><h2>${esc(project.title)}</h2><p class="muted">${esc(project.platform || '未指定')} · r${project.revision}</p></div><button class="btn" id="project-refresh">刷新项目</button></div><div class="project-progress">${stage(project)}</div><div class="project-layout"><section><h3>创作链路</h3><div class="document-grid">${documents}</div><section class="timeline"><header><div><p class="eyebrow">剪辑方案</p><h3>双轨时间线</h3></div><div class="segmented"><button class="active">时间线</button><button>文本视图</button></div></header><div class="tracks"><div><span>视频</span><i style="width:64%"></i><i style="width:28%"></i></div><div><span>声音</span><i style="width:82%"></i></div></div><p class="muted">结构化剪辑方案是唯一机器执行依据；文本视图保留为可控编辑入口。</p></section></section><aside class="rail"><p class="eyebrow">项目状态</p><div class="kv"><span>交付</span><strong>${esc(project.delivery?.state || 'not_started')}</strong></div><div class="kv"><span>研究与参考</span><strong>${project.references?.length || 0}</strong></div><div class="kv"><span>发布与复盘</span><strong>${project.publishing_history?.length || 0}</strong></div><button class="btn btn--full" id="add-reference">添加参考资料</button></aside></div>`;
  target.querySelector('#project-refresh').onclick = () => selectProject(project.id);
  target.querySelectorAll('[data-open-document]').forEach(button => button.onclick = () => notice(`“${button.dataset.openDocument}” 的区块编辑入口仍保留在项目数据合同中。`));
  target.querySelector('#add-reference').onclick = () => notice('参考资料与素材库分开保存，避免把外部参考误作可剪素材。');
}

function settingsPane(name, title, text, body) { return `<section class="set-sec" data-set-pane="${name}" ${name === 'paths' ? '' : 'hidden'}><h3>${title}</h3><p>${text}</p>${body}</section>`; }
function renderSettings() {
  const target = $('[data-screen-panel="settings"]'); const settings = state.settings || {}; const upstream = settings.upstream || {}; const providers = settings.model_providers || []; const archive = settings.archive || {};
  target.innerHTML = `<div class="screen-head"><div><p class="eyebrow">设置与诊断</p><h2>本机配置</h2><p class="muted">账号连接是可选项，未连接上游不限制本地创作。</p></div></div><div class="settings-layout"><aside class="set-nav"><button data-set-nav="paths" aria-current="true">存放位置</button><button data-set-nav="agent">创意模型</button><button data-set-nav="asr">音频转写</button><button data-set-nav="budget">分析预算</button><button data-set-nav="account">上游账号</button><hr><button data-set-nav="doctor">诊断</button></aside><main>${settingsPane('paths', '归档生命周期与物理位置', '每个物理位置独立保留清单与回读状态。', `<div class="setrow"><div><strong>生命周期</strong><small>${esc(archive.lifecycle || 'active')}</small></div><span class="chip">${archive.locations?.length || 0} 个位置</span></div><button class="btn" id="save-location">登记位置</button>`)}${settingsPane('agent', '创意模型', '可配置 Codex、Claude、DeepSeek 或兼容 API；密钥仅用本机引用保存。', `<div class="history">${providers.length ? providers.map(provider => `<div><strong>${esc(provider.provider)} · ${esc(provider.model)}</strong><small>${esc(provider.capability?.reason_code || '未探测')}</small></div>`).join('') : '<p>尚未配置模型。</p>'}</div><button class="btn" id="add-provider">添加模型</button>`)}${settingsPane('asr', '音频转写', '默认使用阿里云在线转写。音频会发送给阿里云；请求失败后才尝试已安装的本机 FunASR。', '<span class="chip chip--ai">DashScope 默认</span>')} ${settingsPane('budget', '分析预算', '分析档位和预算由本机配置读取，耗尽后应显示明确状态而非静默降级。', '<div class="tier"><i></i><i></i><i></i> 标准</div>')} ${settingsPane('account', '上游中台账号', upstream.upstream_features_available ? '已连接上游身份。本地功能始终可用。' : '尚未连接上游。本地功能保持完整。', `<button class="btn" data-surface="login">${upstream.upstream_features_available ? '管理连接' : '连接上游'}</button>`)} ${settingsPane('doctor', '诊断', '诊断将区分“本机不支持”和“配置错误”，不会把不支持的上游能力误报为本地流水线故障。', '<div class="diagnostic"><span class="dot dot--ok"></span><div><strong>本地工作台</strong><small>可用</small></div></div><button class="btn" id="copy-report">复制报告</button>')}</main></div>`;
  target.querySelectorAll('[data-set-nav]').forEach(button => button.onclick = () => { const name = button.dataset.setNav; target.querySelectorAll('[data-set-pane]').forEach(pane => pane.hidden = pane.dataset.setPane !== name); target.querySelectorAll('[data-set-nav]').forEach(item => item.setAttribute('aria-current', String(item === button))); });
  target.querySelectorAll('[data-surface="login"]').forEach(button => button.onclick = () => openSurface('login'));
  target.querySelector('#copy-report').onclick = async () => { await navigator.clipboard?.writeText(`Photo Content OS\n本机功能: 可用\n上游: ${upstream.pairing_status || 'unavailable'}`); notice('诊断报告已复制。'); };
  target.querySelector('#save-location').onclick = () => notice('请填写受控的位置引用和媒体清单后登记。'); target.querySelector('#add-provider').onclick = () => notice('模型配置需要提供方、模型、端点和本机密钥引用。');
}

function render() { renderHome(); renderInbox(); renderLibrary(); renderProject(); renderSettings(); }
function showScreen(name) { state.screen = name; document.querySelectorAll('[data-screen-panel]').forEach(panel => panel.hidden = panel.dataset.screenPanel !== name); document.querySelectorAll('[data-screen]').forEach(button => button.setAttribute('aria-current', String(button.dataset.screen === name))); const labels = { home: ['工作台', '最近项目与本机能力状态'], inbox: ['整理台', '按事件建议整理本地素材'], library: ['素材库', '筛选可复用素材'], project: ['项目', '创作链路与剪辑方案'], settings: ['设置与诊断', '本机配置与可选连接'] }; $('#screen-title').textContent = labels[name][0]; $('#screen-sub').textContent = labels[name][1]; }
function openSurface(name) { document.querySelectorAll('[data-surface-panel]').forEach(panel => panel.hidden = panel.dataset.surfacePanel !== name); if (name === 'cloud') renderCloud(); if (name === 'setup') renderWizard(); }
function closeSurface() { document.querySelectorAll('[data-surface-panel]').forEach(panel => panel.hidden = true); }
function renderWizard() { const copy = [['存放位置', '状态目录可重新进入；不要求上传原始媒体。'], ['运行环境', '检查本机工具链并给出可执行修复建议。'], ['剪辑器', '选择标准剪辑交接，或在本机条件满足时选择可编辑时间线。'], ['账号与设备', '连接上游是可选项；跳过不会关闭本地工作台。']][state.wizard - 1]; $('#wizard-panel').innerHTML = `<p class="eyebrow">第 ${state.wizard} 步</p><h2>${copy[0]}</h2><p>${copy[1]}</p>`; document.querySelectorAll('[data-wizard-step]').forEach(node => node.classList.toggle('active', Number(node.dataset.wizardStep) === state.wizard)); $('#wizard-prev').disabled = state.wizard === 1; $('#wizard-next').textContent = state.wizard === 4 ? '完成' : '下一步'; }
function renderCloud() { const upstream = state.settings?.upstream || {}; const stateMap = { queued: '排队中', running: '处理中', completed: '已完成', failed: '失败', expired: '已过期', cancelled: '已取消' }; const projected = upstream.upstream_features_available ? 'completed' : 'expired'; $('#cloud-content').innerHTML = `<div class="cloud-task"><span class="chip ${projected === 'completed' ? 'chip--ok' : 'chip--warn'}">${stateMap[projected]}</span><h2>${upstream.upstream_features_available ? '上游已连接' : '未连接或配对已过期'}</h2><p>上游任务仅在连接可用时显示；本地创作不依赖此状态。</p></div>`; }
async function loadLibrary(category = '', tags = '') { try { const query = new URLSearchParams(); if (category) query.set('category', category); if (tags) query.append('tags', tags); const suffix = query.toString() ? `?${query}` : ''; const [assets, statistics] = await Promise.all([api(`/api/assets${suffix}`), api('/api/assets/statistics')]); state.assets = assets.assets || []; state.assetStatistics = statistics.statistics; state.assetError = ''; } catch (error) { state.assets = []; state.assetStatistics = null; state.assetError = error.message; } }
async function loadInboxPlan() { if (!state.project?.id) { state.inboxPlan = null; state.inboxPlanError = '先选择并连接一个项目，才能读取它的媒体清单。'; return; } try { const response = await api(`/api/projects/${encodeURIComponent(state.project.id)}/inbox-plan`, { method: 'POST', body: {} }); state.inboxPlan = response.plan; state.inboxPlanError = ''; } catch (error) { state.inboxPlan = null; state.inboxPlanError = error.message; } }
async function selectProject(id) { try { const response = await api(`/api/projects/${encodeURIComponent(id)}`); state.project = response.project; await loadInboxPlan(); showScreen('project'); renderProject(); } catch (error) { notice(error.message, true); } }
function openProjectDialog() { $('#project-dialog').showModal(); }
async function bootstrap() { try { const response = await api('/api/bootstrap'); state.csrf = response.csrfToken; state.projects = response.projects || []; const [settings] = await Promise.all([api('/api/settings'), loadLibrary()]); state.settings = settings.settings; if (state.projects[0] && !state.project) { const project = await api(`/api/projects/${encodeURIComponent(state.projects[0].id)}`); state.project = project.project; } await loadInboxPlan(); $('#inbox-count').textContent = String(state.inboxPlan?.batches?.length || 0); render(); showScreen(state.screen); } catch (error) { notice(error.message, true); } }

document.querySelectorAll('[data-screen]').forEach(button => button.onclick = () => showScreen(button.dataset.screen));
document.querySelectorAll('[data-surface]').forEach(button => button.onclick = () => openSurface(button.dataset.surface));
document.querySelectorAll('[data-close-surface]').forEach(button => button.onclick = closeSurface);
$('#open-create').onclick = openProjectDialog;
$('#project-form').onsubmit = async event => { event.preventDefault(); try { const value = Object.fromEntries(new FormData(event.currentTarget)); const response = await api('/api/projects', { method: 'POST', body: value }); state.projects.unshift(response.project); state.project = response.project; $('#project-dialog').close(); render(); showScreen('project'); notice('项目已创建。'); } catch (error) { notice(error.message, true); } };
$('#pair-form').onsubmit = async event => { event.preventDefault(); try { const value = Object.fromEntries(new FormData(event.currentTarget)); const response = await api('/api/settings/upstream/pair', { method: 'POST', body: value }); state.settings = { ...state.settings, upstream: response.upstream }; closeSurface(); render(); notice(response.upstream.upstream_features_available ? '已连接上游。' : '上游当前不可用，本地工作台仍可使用。'); } catch (error) { notice(error.message, true); } };
$('#wizard-prev').onclick = () => { state.wizard = Math.max(1, state.wizard - 1); renderWizard(); }; $('#wizard-next').onclick = () => { if (state.wizard === 4) { closeSurface(); notice('向导可随时重新打开。'); } else { state.wizard += 1; renderWizard(); } };
bootstrap();
