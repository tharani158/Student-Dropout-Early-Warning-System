const state = { summary: null, comparison: null, clusters: null, pca: null, predictions: null, importance: null };
const $ = (id) => document.getElementById(id);
const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const fmt = (value, digits = 3) => Number.isFinite(Number(value)) ? Number(value).toFixed(digits) : '—';
const num = (value) => new Intl.NumberFormat().format(Number(value || 0));

async function getJson(path) {
  const response = await fetch(path);
  if (!response.ok) {
    let detail = `Request failed (${response.status})`;
    try { const body = await response.json(); detail = body.detail || detail; } catch {}
    throw new Error(detail);
  }
  return response.json();
}

function setError(message = '') {
  const box = $('global-error');
  box.hidden = !message;
  box.textContent = message;
}

function showPage(name) {
  document.querySelectorAll('.page').forEach(page => page.classList.toggle('active', page.id === `page-${name}`));
  document.querySelectorAll('.nav-item').forEach(button => button.classList.toggle('active', button.dataset.page === name));
  const button = document.querySelector(`.nav-item[data-page="${name}"]`);
  $('crumb-page').textContent = button?.textContent.trim() || 'Overview';
  if (name === 'clusters' && !state.clusters) loadClusters();
  if (name === 'pca' && !state.pca) loadPca();
  if (name === 'models' && !state.importance) loadImportance();
}

document.querySelectorAll('.nav-item').forEach(button => button.addEventListener('click', () => showPage(button.dataset.page)));
document.querySelectorAll('[data-jump]').forEach(button => button.addEventListener('click', () => showPage(button.dataset.jump)));
$('refresh-button').addEventListener('click', () => refreshAll(true));
$('metric-select').addEventListener('change', renderModelChart);
$('pca-color').addEventListener('change', renderPca);
$('reload-clusters').addEventListener('click', () => loadClusters(true));
$('explain-button').addEventListener('click', loadExplanation);

async function refreshAll(force = false) {
  if (force) { state.clusters = null; state.pca = null; state.importance = null; }
  setError('');
  $('api-status').textContent = 'Connecting';
  try {
    const [summary, comparison, quality, predictions] = await Promise.all([
      getJson('/api/analytics/summary'), getJson('/api/analytics/model-comparison'),
      getJson('/api/analytics/quality'), getJson('/api/analytics/predictions?limit=12')
    ]);
    state.summary = summary; state.comparison = comparison; state.quality = quality; state.predictions = predictions;
    $('api-status').textContent = 'Connected';
    document.querySelector('.sidebar-foot .status-dot').style.background = '#35b79b';
    renderSummary(); renderModelChart(); renderTables(); renderPredictions();
    if (force) { showPage(document.querySelector('.page.active')?.id.replace('page-', '') || 'overview'); }
  } catch (error) {
    $('api-status').textContent = 'Unavailable';
    document.querySelector('.sidebar-foot .status-dot').style.background = '#e16b61';
    setError(`${error.message}. Check that the API is running and the expected CSV outputs are in student_dropout_project_outputs.`);
  }
}

function renderSummary() {
  const data = state.summary;
  if (!data) return;
  $('record-count').textContent = num(data.record_count);
  $('dataset-count-chip').textContent = `${num(data.record_count)} records`;
  $('dropout-rate').textContent = `${fmt(data.dropout_rate, 1)}%`;
  $('dropout-count').textContent = num(data.dropout_count);
  $('best-auc').textContent = fmt(data.best_roc_auc, 3);
  $('best-model').textContent = data.best_model_by_roc_auc || 'No model metric available';
  $('duplicate-count').textContent = num(data.duplicate_rows);
  $('missing-caption').textContent = `${num(data.missing_cells)} missing cells across dataset`;
  drawRiskChart(data.risk_distribution);
  drawStackedDistribution('class-chart', data.class_distribution, {Retained:'#4e83ec', Dropout:'#eb6c62'});
  drawStackedDistribution('source-chart', data.source_distribution, {kaggle:'#1d9986', uci:'#8e6ae6'});
}

function drawRiskChart(distribution = {}) {
  const order = ['Low Risk', 'Medium Risk', 'High Risk'];
  const colors = {'Low Risk':'#4e83ec','Medium Risk':'#e2a443','High Risk':'#e66f65'};
  const total = Object.values(distribution).reduce((sum, value) => sum + Number(value), 0) || 1;
  $('risk-chart').innerHTML = order.map(name => {
    const value = Number(distribution[name] || 0);
    const width = value / total * 100;
    return `<div class="chart-row"><span>${esc(name)}</span><div class="bar-track"><div class="bar-fill" style="width:${width}%;background:${colors[name]}"></div></div><span class="bar-value">${num(value)}</span></div>`;
  }).join('');
}

function drawStackedDistribution(id, distribution = {}, palette = {}) {
  const entries = Object.entries(distribution);
  const total = entries.reduce((sum, [, value]) => sum + Number(value), 0) || 1;
  const stack = entries.map(([name, value], index) => {
    const color = palette[name] || ['#1d9986','#4e83ec','#8e6ae6','#e2a443'][index % 4];
    return `<span title="${esc(name)}: ${num(value)}" style="width:${Number(value)/total*100}%;background:${color}"></span>`;
  }).join('');
  const labels = entries.map(([name, value], index) => {
    const color = palette[name] || ['#1d9986','#4e83ec','#8e6ae6','#e2a443'][index % 4];
    return `<span><i class="legend-dot" style="background:${color}"></i>${esc(name)} <b>${num(value)}</b></span>`;
  }).join('');
  $(id).innerHTML = `<div class="chart-stack">${stack}</div><div class="stat-pair"><span>Total</span><b>${num(total)}</b></div><div class="legend">${labels}</div>`;
}

function renderModelChart() {
  if (!state.comparison) return;
  const metric = $('metric-select')?.value || 'ROC AUC';
  const rows = [...state.comparison.metrics].sort((a,b) => Number(b[metric] || 0) - Number(a[metric] || 0));
  const max = Math.max(1, ...rows.map(row => Number(row[metric] || 0)));
  const html = rows.map((row, index) => {
    const score = Number(row[metric] || 0);
    const width = score / max * 100;
    return `<div class="chart-row ${index > 3 ? 'small' : ''}"><span>${esc(row.Model)}</span><div class="bar-track"><div class="bar-fill" style="width:${width}%;background:${index===0?'#1d9986':'#7bbaae'}"></div></div><span class="bar-value">${fmt(score)}</span></div>`;
  }).join('');
  $('model-chart').innerHTML = html;
  $('overview-model-chart').innerHTML = rows.slice(0,5).map((row,index) => `<div class="chart-row small"><span>${esc(row.Model)}</span><div class="bar-track"><div class="bar-fill" style="width:${Number(row['ROC AUC'])*100}%;background:${index===0?'#1d9986':'#7bbaae'}"></div></div><span class="bar-value">${fmt(row['ROC AUC'])}</span></div>`).join('');
}

function tableHtml(table, columns, rows, formatters = {}) {
  table.querySelector('thead').innerHTML = `<tr>${columns.map(column => `<th>${esc(column.label)}</th>`).join('')}</tr>`;
  table.querySelector('tbody').innerHTML = rows.map(row => `<tr>${columns.map(column => {
    const value = row[column.key];
    const rendered = formatters[column.key] ? formatters[column.key](value) : (typeof value === 'number' ? fmt(value) : esc(value));
    return `<td>${rendered}</td>`;
  }).join('')}</tr>`).join('');
}

function renderTables() {
  if (!state.comparison) return;
  const metricColumns = ['Model','Accuracy','Precision','Recall','F1 Score','ROC AUC','PR AUC','MCC'].map(key => ({key,label:key}));
  tableHtml($('metrics-table'), metricColumns, state.comparison.metrics);
  const cvRows = state.comparison.cross_validation || [];
  if (cvRows.length) {
    const columns = Object.keys(cvRows[0]).map(key => ({key,label:key}));
    tableHtml($('cv-table'), columns, cvRows);
  } else $('cv-table').innerHTML = '<tbody><tr><td>Cross-validation file is not present.</td></tr></tbody>';
}

function renderPredictions() {
  if (!state.predictions?.records?.length) return;
  const columns = ['record_id','age','gender','scholarship','dropout_probability','risk_level','actual_dropout'].map(key => ({key,label:key.replaceAll('_',' ')}));
  const riskFormatter = value => `<span class="risk-badge ${String(value).toLowerCase().split(' ')[0]}">${esc(value)}</span>`;
  tableHtml($('prediction-table'), columns, state.predictions.records, {
    record_id: value => Number.isFinite(Number(value)) ? String(Math.trunc(Number(value))) : '—',
    age: value => Number.isFinite(Number(value)) ? String(Math.round(Number(value))) : '—',
    dropout_probability: value => `${fmt(Number(value)*100,1)}%`, risk_level:riskFormatter,
    actual_dropout:value => value == null ? '—' : (Number(value) ? 'Dropout' : 'Retained')
  });
}

async function loadImportance() {
  $('importance-chart').innerHTML = '<p class="empty-state">Loading feature analysis…</p>';
  try {
    state.importance = await getJson('/api/analytics/feature-importance');
    $('importance-method').textContent = state.importance.method;
    $('importance-note').textContent = state.importance.note || state.importance.interpretation || '';
    const items = state.importance.items || [];
    const max = Math.max(1e-9, ...items.map(item => Number(item.importance)));
    $('importance-chart').innerHTML = items.slice(0,10).map((item,index) => `<div class="chart-row small"><span>${esc(item.feature)}</span><div class="bar-track"><div class="bar-fill" style="width:${Number(item.importance)/max*100}%;background:${index===0?'#1d9986':'#78b9ad'}"></div></div><span class="bar-value">${fmt(item.importance,3)}</span></div>`).join('');
  } catch (error) { $('importance-chart').innerHTML = `<p class="empty-state">${esc(error.message)}</p>`; }
}

async function loadClusters(force = false) {
  $('cluster-panels').innerHTML = '<article class="panel span-2"><p class="empty-state">Fitting clustering models on the reproducible sample…</p></article>';
  try {
    if (force) state.clusters = null;
    state.clusters = await getJson('/api/analytics/clusters');
    $('cluster-sample').textContent = num(state.clusters.sample_size);
    $('cluster-sample-caption').textContent = `Sample of ${num(state.clusters.dataset_size)} dataset rows`;
    $('selected-k').textContent = num(state.clusters.selected_cluster_count);
    const counts = state.clusters.cluster_count_diagnostics || [];
    const maxSilhouette = Math.max(1e-9, ...counts.map(item => Number(item.silhouette)));
    $('cluster-count-chart').innerHTML = counts.map(item => `<div class="chart-row small"><span>k = ${item.clusters}</span><div class="bar-track"><div class="bar-fill" style="width:${Number(item.silhouette)/maxSilhouette*100}%;background:${item.clusters===state.clusters.selected_cluster_count?'#1d9986':'#7bbaae'}"></div></div><span class="bar-value">${fmt(item.silhouette,3)}</span></div><div class="cluster-count-note">Inertia ${num(item.inertia)} · Davies-Bouldin ${fmt(item.davies_bouldin,3)}</div>`).join('');
    $('cluster-panels').innerHTML = Object.entries(state.clusters.algorithms).map(([name, result]) => {
      const clusters = result.clusters;
      const max = Math.max(1, ...clusters.map(cluster => cluster.records));
      const d = result.diagnostics;
      return `<article class="panel"><div class="panel-heading"><div><h2>${esc(name)}</h2><p>Cluster sizes and recorded dropout rate</p></div></div><div class="cluster-diagnostics"><span>Silhouette <b>${fmt(d.silhouette,3)}</b></span><span>Davies-Bouldin <b>${fmt(d.davies_bouldin,3)}</b></span><span>ARI vs target <b>${fmt(d.adjusted_rand_vs_target,3)}</b></span></div>${clusters.map(cluster => `<div class="cluster-row"><div class="cluster-title"><b>Cluster ${cluster.cluster+1}</b><span>${num(cluster.records)} records · ${fmt(cluster.dropout_rate,1)}% dropout</span></div><div class="chart-row small"><span>Group size</span><div class="bar-track"><div class="bar-fill" style="width:${cluster.records/max*100}%"></div></div><span class="bar-value">${fmt(cluster.records/max*100,0)}%</span></div><div class="cluster-details"><span>Academic avg <b>${fmt(cluster.mean_academic_overall,2)}</b></span><span>Engagement <b>${fmt(cluster.mean_engagement,2)}</b></span></div><div class="source-mini">${Object.entries(cluster.sources).map(([source,count])=>`${esc(source)} ${num(count)}`).join(' · ')}</div></div>`).join('')}</article>`;
    }).join('');
  } catch (error) { $('cluster-panels').innerHTML = `<article class="panel span-2"><p class="empty-state">${esc(error.message)}</p></article>`; }
}

async function loadPca() {
  $('pca-chart').innerHTML = '<p class="empty-state" style="padding:20px">Computing PCA projection…</p>';
  try { state.pca = await getJson('/api/analytics/pca'); renderPca(); }
  catch (error) { $('pca-chart').innerHTML = `<p class="empty-state" style="padding:20px">${esc(error.message)}</p>`; }
}

function renderPca() {
  if (!state.pca) return;
  const data = state.pca;
  $('pc1-variance').textContent = `${fmt(data.explained_variance_ratio[0]*100,1)}%`;
  $('pc2-variance').textContent = `${fmt(data.explained_variance_ratio[1]*100,1)}%`;
  $('pca-point-count').textContent = num(data.plot_size);
  const points = data.points || [];
  if (!points.length) { $('pca-chart').innerHTML = '<p class="empty-state" style="padding:20px">No PCA coordinates available.</p>'; return; }
  const width=880,height=420,pad={l:54,r:20,t:18,b:42};
  const xs=points.map(p=>Number(p.pc1)),ys=points.map(p=>Number(p.pc2));
  const xmin=Math.min(...xs),xmax=Math.max(...xs),ymin=Math.min(...ys),ymax=Math.max(...ys);
  const xscale=x=>pad.l+(x-xmin)/(xmax-xmin||1)*(width-pad.l-pad.r);
  const yscale=y=>height-pad.b-(y-ymin)/(ymax-ymin||1)*(height-pad.t-pad.b);
  const colorKey=$('pca-color').value;
  const sourceColors={kaggle:'#4e83ec',uci:'#e2a443',Unknown:'#91a0a4'};
  const color=p=>colorKey==='target'?(Number(p.target)===1?'#e66f65':'#4e83ec'):(sourceColors[p.source]||'#8e6ae6');
  const circles=points.map(p=>`<circle class="pca-point" cx="${xscale(p.pc1).toFixed(1)}" cy="${yscale(p.pc2).toFixed(1)}" r="3.2" fill="${color(p)}"><title>PC1 ${fmt(p.pc1,2)}, PC2 ${fmt(p.pc2,2)}, ${colorKey==='target'?(Number(p.target)?'Dropout':'Retained'):esc(p.source)}</title></circle>`).join('');
  $('pca-chart').innerHTML=`<svg viewBox="0 0 ${width} ${height}" role="img" aria-label="PCA scatter plot"><line class="axis-line" x1="${pad.l}" y1="${height-pad.b}" x2="${width-pad.r}" y2="${height-pad.b}"/><line class="axis-line" x1="${pad.l}" y1="${pad.t}" x2="${pad.l}" y2="${height-pad.b}"/><text class="axis-label" x="${width/2}" y="${height-9}" text-anchor="middle">Principal component 1</text><text class="axis-label" transform="translate(14 ${height/2}) rotate(-90)" text-anchor="middle">Principal component 2</text>${circles}</svg>`;
  const legend=colorKey==='target'?[['#4e83ec','Retained'],['#e66f65','Dropout']]:Object.entries(sourceColors).filter(([key])=>points.some(p=>p.source===key)).map(([c,label])=>[c,label]);
  $('pca-legend').innerHTML=legend.map(([c,label])=>`<span><i class="legend-dot" style="background:${c}"></i>${esc(label)}</span>`).join('');
}

async function loadExplanation() {
  const recordId=Math.max(0,Number($('record-id').value||0));
  const model=$('explain-model').value;
  $('explain-result').className='explain-result empty-state';
  $('explain-result').textContent='Requesting model explanation…';
  try {
    const result=await getJson(`/api/analytics/explain/${recordId}?model=${encodeURIComponent(model)}`);
    renderExplanation(result);
  } catch(error) { $('explain-result').textContent=error.message; }
}

function renderExplanation(result) {
  const box=$('explain-result');
  box.className='explain-result';
  const features=Object.entries(result.student_features||{}).map(([key,value])=>{
    let displayValue=value;
    if(key==='age'&&Number.isFinite(Number(value))) displayValue=String(Math.round(Number(value)));
    if(['academic_trend','academic_overall'].includes(key)&&Number.isFinite(Number(value))) displayValue=Number(value).toFixed(4);
    return `<span class="prediction-pill">${esc(key.replaceAll('_',' '))}: <b>${esc(displayValue)}</b></span>`;
  }).join('');
  const riskClass=String(result.risk_level||'').toLowerCase().split(' ')[0];
  let body='';
  if (result.available && result.values?.length) {
    const max=Math.max(1e-9,...result.values.map(item=>Math.abs(Number(item.shap_value))));
    body=result.values.map(item=>`<div class="shap-item"><span>${esc(item.feature)}</span><div class="shap-track"><i class="shap-zero"></i><i class="shap-fill ${Number(item.shap_value)>=0?'positive':'negative'}" style="width:${Math.abs(Number(item.shap_value))/max*48}%"></i></div><span class="shap-value">${fmt(item.shap_value,4)}</span></div>`).join('');
  } else body=`<div class="notice subtle">${esc(result.message)}</div><p class="method-note">The predicted probability and risk label are taken from the saved prediction CSV. No SHAP values are fabricated when the model or its explanation runtime is unavailable.</p>`;
  box.innerHTML=`<div class="prediction-summary"><span class="prediction-pill">Record <b>#${num(result.record_id)}</b></span><span class="prediction-pill">Dropout probability <b>${fmt(Number(result.dropout_probability)*100,1)}%</b></span><span class="risk-badge ${riskClass}">${esc(result.risk_level)}</span><span class="prediction-pill">Model <b>${esc(result.model)}</b></span></div><div class="prediction-summary">${features}</div><h3>${esc(result.method||'Explanation status')}</h3><p class="method-note">${esc(result.message)}</p>${body}`;
}

refreshAll();
