const $ = (s) => document.querySelector(s);
const statusBox = (node, text, error=false) => { node.textContent=text; node.className=`status${error?' error':''}`; };
async function api(path, options={}) { const r=await fetch(path,options); const d=await r.json(); if(!r.ok) throw new Error(d.detail||'Request failed'); return d; }
async function refresh() {
  try {
    const {datasets=[]}=await api('/api/datasets');
    $('#dataset-count').textContent=datasets.length;
    $('#record-count').textContent=datasets.reduce((n,d)=>n+d.rows,0).toLocaleString();
<<<<<<< Updated upstream
    $('#dataset-list').innerHTML=datasets.length?datasets.map(d=>`<article class="dataset-card"><div><b>${escapeHtml(d.filename)}</b><small>${escapeHtml(d.source)} · ${Math.ceil(d.size_bytes/1024).toLocaleString()} KB</small></div><span class="numbers">${d.rows.toLocaleString()} rows · ${d.columns} columns</span><span class="badge">Validated</span></article>`).join(''):'<div class="empty">No datasets uploaded yet.</div>';
    for(const id of ['dataset-a','dataset-b','preview-select','validation-select','dashboard-select','profile-select']) { const el=$(`#${id}`); const placeholder=id.includes('select')?'Choose dataset':'Select dataset'; const selected=el.value; el.innerHTML=`<option value="">${placeholder}</option>`+datasets.map(d=>`<option value="${d.id}">${escapeHtml(d.filename)} (${escapeHtml(d.source)})</option>`).join(''); if(datasets.some(d=>d.id===selected)) el.value=selected; }
    await refreshDashboard();
=======
    $('#dataset-list').innerHTML=datasets.length?datasets.map(d=>`<article class="dataset-card"><div><b>${escapeHtml(d.filename)}</b><small>${escapeHtml(d.source)} · ${Math.ceil(d.size_bytes/1024).toLocaleString()} KB</small></div><span class="numbers">${d.rows.toLocaleString()} rows · ${d.columns} columns</span><span class="badge">Validated</span><button class="button delete-button" type="button" data-delete-id="${escapeHtml(d.id)}" data-delete-name="${escapeHtml(d.filename)}" aria-label="Delete ${escapeHtml(d.filename)}">Delete</button></article>`).join(''):'<div class="empty">No datasets uploaded yet.</div>';
    for(const id of ['dataset-a','dataset-b','preview-select','validation-select']) { const el=$(`#${id}`); const placeholder=id.includes('select')?'Choose dataset':'Select dataset'; const selected=el.value; el.innerHTML=`<option value="">${placeholder}</option>`+datasets.map(d=>`<option value="${d.id}">${escapeHtml(d.filename)} (${escapeHtml(d.source)})</option>`).join(''); if(datasets.some(d=>d.id===selected)) el.value=selected; }
>>>>>>> Stashed changes
  } catch(e) { console.error(e); }
}
function escapeHtml(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
async function upload(files) {
  const box=$('#upload-status'); box.classList.remove('hidden');
  for (const file of files) {
    try { statusBox(box,`Uploading ${file.name}…`); const form=new FormData(); form.append('file',file); const source=document.querySelector('input[name=source]:checked').value; await api(`/api/datasets/upload?source=${encodeURIComponent(source)}`,{method:'POST',body:form}); statusBox(box,`${file.name} uploaded and inspected successfully.`); }
    catch(e){ statusBox(box,`${file.name}: ${e.message}`,true); }
  }
  await refresh();
}
$('#file-input').addEventListener('change',e=>upload(e.target.files));
$('#dropzone').addEventListener('click',e=>{if(e.target.id!=='file-input') $('#file-input').click();});
$('#dropzone').addEventListener('dragover',e=>{e.preventDefault();e.currentTarget.style.background='#edf8f4';});
$('#dropzone').addEventListener('dragleave',e=>e.currentTarget.style.background='');
$('#dropzone').addEventListener('drop',e=>{e.preventDefault();e.currentTarget.style.background='';upload(e.dataTransfer.files);});
$('#refresh').addEventListener('click',refresh);
<<<<<<< Updated upstream
document.querySelectorAll('.nav[data-page]').forEach(link=>link.addEventListener('click',e=>{e.preventDefault();document.querySelectorAll('.nav').forEach(n=>n.classList.remove('active'));link.classList.add('active');document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));$(`#page-${link.dataset.page}`).classList.add('active');$('#page-title').textContent=link.textContent.trim();history.replaceState(null,'',`#${link.dataset.page}`);if(link.dataset.page==='dashboard')refreshDashboard();}));
function bar(label,value,max,detail,kind='primary') {return `<div class="bar-row"><div class="bar-label"><b>${escapeHtml(label)}</b><span>${escapeHtml(detail)}</span></div><div class="bar-track"><div class="bar-fill ${kind}" style="width:${Math.max(0,Math.min(100,100*value/Math.max(max,1)))}%"></div></div></div>`;}
async function refreshDashboard(){
  try {
    const d=await api('/api/dashboard/summary');
    for(const [id,value] of [['dash-datasets',d.dataset_count],['dash-records',d.total_records],['dash-features',d.total_features],['dash-missing',d.missing_values]]) $(`#${id}`).textContent=value.toLocaleString();
    const selected=$('#dashboard-select').value || d.datasets[0]?.id;
    if(selected) $('#dashboard-select').value=selected;
    const dataset=d.datasets.find(x=>x.id===selected);
    const classes=dataset?.class_distribution||[];
    $('#class-chart').classList.toggle('empty',!classes.length);
    $('#class-chart').innerHTML=classes.length?classes.map(c=>bar(c.label,c.count,dataset.rows,`${c.count.toLocaleString()} · ${c.percent}%`,c.label.toLowerCase().includes('dropout')?'danger':'primary')).join(''):'No outcome column detected for this dataset.';
    $('#comparison-chart').classList.toggle('empty',!d.datasets.length);
    $('#comparison-chart').innerHTML=d.datasets.length?d.datasets.map(x=>bar(x.filename,x.rows,Math.max(...d.datasets.map(y=>y.rows)),`${x.rows.toLocaleString()} rows · ${x.missing_values} missing · ${x.duplicate_rows} duplicates`)).join(''):'Upload datasets to compare them.';
    $('#recent-uploads').classList.toggle('empty',!d.datasets.length);
    $('#recent-uploads').innerHTML=d.datasets.length?[...d.datasets].reverse().slice(0,5).map(x=>`<div class="activity-row"><b>${escapeHtml(x.filename)}</b><small>${x.rows.toLocaleString()} rows · ${escapeHtml(x.source)} · ${new Date(x.uploaded_at).toLocaleString()}</small></div>`).join(''):'No uploads yet.';
    $('#recent-activities').classList.toggle('empty',!d.recent_activities.length);
    $('#recent-activities').innerHTML=d.recent_activities.length?d.recent_activities.map(x=>`<div class="activity-row"><b>${escapeHtml(x.description)}</b><small>${new Date(x.at).toLocaleString()}</small></div>`).join(''):'No activity yet.';
  } catch(e){$('#class-chart').textContent=e.message;}
}
$('#dashboard-select').addEventListener('change',refreshDashboard);
$('#profile-select').addEventListener('change',async e=>{
  const id=e.target.value;if(!id){$('#profile-table').innerHTML='';return;}
  try{const p=await api(`/api/datasets/${id}/profile`);$('#profile-summary').classList.remove('empty');$('#profile-summary').textContent=`${p.row_count.toLocaleString()} rows · ${p.feature_count} features · ${p.missing_cells} missing cells · ${p.duplicate_rows} duplicate rows. ${p.quality_issues.join(' ')}`;$('#profile-table').innerHTML=`<thead><tr><th>Feature</th><th>Type</th><th>Missing</th><th>Unique</th><th>IQR outliers</th><th>Top values</th></tr></thead><tbody>${p.columns.map(c=>`<tr><td>${escapeHtml(c.name)}</td><td>${escapeHtml(c.type)} · ${escapeHtml(c.dtype)}</td><td>${c.missing} (${c.missing_percent}%)</td><td>${c.unique}</td><td>${c.outlier_count??'—'}</td><td>${c.top_values.slice(0,3).map(v=>`${escapeHtml(v.value)}: ${v.count}`).join(' · ')}</td></tr>`).join('')}</tbody>`;}catch(err){$('#profile-summary').textContent=err.message;}
});
=======
$('#dataset-list').addEventListener('click',async e=>{
  const button=e.target.closest('[data-delete-id]');
  if(!button)return;
  const id=button.dataset.deleteId, filename=button.dataset.deleteName;
  if(!window.confirm(`Delete "${filename}" and its uploaded CSV? This cannot be undone.`))return;
  const clearPreview=$('#preview-select').value===id, clearValidation=$('#validation-select').value===id;
  const notice=$('#dataset-status');
  notice.classList.remove('hidden');
  button.disabled=true;
  try{
    await api(`/api/datasets/${encodeURIComponent(id)}`,{method:'DELETE'});
    await refresh();
    statusBox(notice,`${filename} and its uploaded file were deleted.`);
    if(clearPreview){$('#preview-title').textContent='Select a dataset to preview';$('#preview-table').innerHTML='';}
    if(clearValidation)$('#validation-results').innerHTML='<div class="empty">Choose an uploaded dataset to see validation details.</div>';
  }catch(err){
    statusBox(notice,`Could not delete ${filename}: ${err.message}`,true);
    button.disabled=false;
  }
});
document.querySelectorAll('.nav[data-page]').forEach(link=>link.addEventListener('click',e=>{e.preventDefault();document.querySelectorAll('.nav').forEach(n=>n.classList.remove('active'));link.classList.add('active');document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));$(`#page-${link.dataset.page}`).classList.add('active');}));
>>>>>>> Stashed changes
async function showValidation(id){if(!id)return;const box=$('#validation-results');try{const d=(await api('/api/datasets')).datasets.find(x=>x.id===id);const v=await api(`/api/datasets/${id}/validation`);box.innerHTML=`<div class="validation-item"><b>Dataset</b><small>${escapeHtml(d.filename)} · ${escapeHtml(d.source)}</small></div><div class="validation-item"><b>${v.row_count.toLocaleString()} rows × ${v.column_count} columns</b><small>File size ${(d.size_bytes/1024).toFixed(1)} KB</small></div><div class="validation-item"><b>${v.missing_cells.toLocaleString()} missing cells</b><small>${v.duplicate_rows.toLocaleString()} exact duplicate rows</small></div>${v.columns.map(c=>`<div class="validation-item"><b>${escapeHtml(c.name)}</b><small>${escapeHtml(c.dtype)} · ${c.missing} missing (${c.missing_percent}%) · ${c.unique} unique</small></div>`).join('')}${v.warnings.map(w=>`<div class="validation-item"><b>Warning</b><small>${escapeHtml(w)}</small></div>`).join('')}`;}catch(e){box.innerHTML=`<div class="empty">${escapeHtml(e.message)}</div>`;}}
$('#validation-select').addEventListener('change',e=>showValidation(e.target.value));
api('/api/health').then(()=>{$('.api-pill').innerHTML='<i></i> API connected'}).catch(()=>{$('.api-pill').innerHTML='<i style="background:#d45b51"></i> API offline'});
$('#preview-select').addEventListener('change',async e=>{if(!e.target.value)return;try{const p=await api(`/api/datasets/${e.target.value}/preview`);$('#preview-title').textContent=`Dataset preview · ${p.rows?.length||0} rows`;$('#preview-table').innerHTML=`<thead><tr>${p.columns.map(c=>`<th>${escapeHtml(c)}</th>`).join('')}</tr></thead><tbody>${p.rows.map(row=>`<tr>${p.columns.map(c=>`<td>${escapeHtml(row[c]??'')}</td>`).join('')}</tr>`).join('')}</tbody>`;}catch(err){$('#preview-title').textContent=err.message;}});
$('#integrate').addEventListener('click',async()=>{const box=$('#integration-result');box.classList.remove('hidden');$('#integration-state').textContent='Running…';statusBox($('#integration-log'),'Integration started…');$('#integration-details').innerHTML='';try{const ids=[$('#dataset-a').value,$('#dataset-b').value].filter(Boolean);const r=await api('/api/integrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dataset_ids:ids,target_mode:$('#target-mode').value})});$('#integration-state').textContent='Complete';statusBox(box,`Processing complete: ${r.rows.toLocaleString()} rows, ${r.columns.length} columns. `);const a=document.createElement('a');a.href=r.download_url;a.textContent='Download processed CSV';a.style.marginLeft='8px';box.append(a);statusBox($('#integration-log'),`Complete · ${r.rows.toLocaleString()} rows · ${r.columns.length} columns · ${ids.length===1?'standalone source':'two-source integration'} · target mode: ${r.target_mode}.`);$('#integration-details').innerHTML=r.statistics.sources.map(s=>`<div class="validation-item"><b>${escapeHtml(s.source)} · original</b><small>${s.rows.toLocaleString()} rows · ${s.columns} columns · ${s.missing_values.toLocaleString()} missing · ${s.duplicate_rows.toLocaleString()} duplicate rows</small></div>`).join('')+`<div class="validation-item"><b>Processed dataset</b><small>${r.statistics.combined_rows.toLocaleString()} rows · ${r.statistics.combined_columns} columns · target: ${escapeHtml(r.statistics.target_column)}</small></div><div class="validation-item"><b>Target distribution</b><small>${Object.entries(r.statistics.target_counts).map(([k,v])=>`${escapeHtml(k)}: ${v}`).join(' · ')}</small></div>`;}catch(e){$('#integration-state').textContent='Needs attention';statusBox(box,e.message,true);statusBox($('#integration-log'),`Failed · ${e.message}`,true);}});
refresh();
