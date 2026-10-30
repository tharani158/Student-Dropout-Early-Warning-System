const $ = (s) => document.querySelector(s);
const statusBox = (node, text, error=false) => { node.textContent=text; node.className=`status${error?' error':''}`; };
async function api(path, options={}) { const r=await fetch(path,options); const d=await r.json(); if(!r.ok) throw new Error(d.detail||'Request failed'); return d; }
async function refresh() {
  try {
    const {datasets=[]}=await api('/api/datasets');
    $('#dataset-count').textContent=datasets.length;
    $('#record-count').textContent=datasets.reduce((n,d)=>n+d.rows,0).toLocaleString();
    $('#dataset-list').innerHTML=datasets.length?datasets.map(d=>`<article class="dataset-card"><div><b>${escapeHtml(d.filename)}</b><small>${escapeHtml(d.source)} · ${Math.ceil(d.size_bytes/1024).toLocaleString()} KB</small></div><span class="numbers">${d.rows.toLocaleString()} rows · ${d.columns} columns</span><span class="badge">Validated</span></article>`).join(''):'<div class="empty">No datasets uploaded yet.</div>';
    for(const id of ['dataset-a','dataset-b','preview-select','validation-select']) { const el=$(`#${id}`); const placeholder=id.includes('select')?'Choose dataset':'Select dataset'; const selected=el.value; el.innerHTML=`<option value="">${placeholder}</option>`+datasets.map(d=>`<option value="${d.id}">${escapeHtml(d.filename)} (${escapeHtml(d.source)})</option>`).join(''); if(datasets.some(d=>d.id===selected)) el.value=selected; }
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
document.querySelectorAll('.nav[data-page]').forEach(link=>link.addEventListener('click',e=>{e.preventDefault();document.querySelectorAll('.nav').forEach(n=>n.classList.remove('active'));link.classList.add('active');document.querySelectorAll('.page').forEach(p=>p.classList.remove('active'));$(`#page-${link.dataset.page}`).classList.add('active');}));
async function showValidation(id){if(!id)return;const box=$('#validation-results');try{const d=(await api('/api/datasets')).datasets.find(x=>x.id===id);const v=await api(`/api/datasets/${id}/validation`);box.innerHTML=`<div class="validation-item"><b>Dataset</b><small>${escapeHtml(d.filename)} · ${escapeHtml(d.source)}</small></div><div class="validation-item"><b>${v.row_count.toLocaleString()} rows × ${v.column_count} columns</b><small>File size ${(d.size_bytes/1024).toFixed(1)} KB</small></div><div class="validation-item"><b>${v.missing_cells.toLocaleString()} missing cells</b><small>${v.duplicate_rows.toLocaleString()} exact duplicate rows</small></div>${v.columns.map(c=>`<div class="validation-item"><b>${escapeHtml(c.name)}</b><small>${escapeHtml(c.dtype)} · ${c.missing} missing (${c.missing_percent}%) · ${c.unique} unique</small></div>`).join('')}${v.warnings.map(w=>`<div class="validation-item"><b>Warning</b><small>${escapeHtml(w)}</small></div>`).join('')}`;}catch(e){box.innerHTML=`<div class="empty">${escapeHtml(e.message)}</div>`;}}
$('#validation-select').addEventListener('change',e=>showValidation(e.target.value));
api('/api/health').then(()=>{$('.api-pill').innerHTML='<i></i> API connected'}).catch(()=>{$('.api-pill').innerHTML='<i style="background:#d45b51"></i> API offline'});
$('#preview-select').addEventListener('change',async e=>{if(!e.target.value)return;try{const p=await api(`/api/datasets/${e.target.value}/preview`);$('#preview-title').textContent=`Dataset preview · ${p.rows?.length||0} rows`;$('#preview-table').innerHTML=`<thead><tr>${p.columns.map(c=>`<th>${escapeHtml(c)}</th>`).join('')}</tr></thead><tbody>${p.rows.map(row=>`<tr>${p.columns.map(c=>`<td>${escapeHtml(row[c]??'')}</td>`).join('')}</tr>`).join('')}</tbody>`;}catch(err){$('#preview-title').textContent=err.message;}});
$('#integrate').addEventListener('click',async()=>{const box=$('#integration-result');box.classList.remove('hidden');$('#integration-state').textContent='Running…';statusBox($('#integration-log'),'Integration started…');$('#integration-details').innerHTML='';try{const ids=[$('#dataset-a').value,$('#dataset-b').value].filter(Boolean);const r=await api('/api/integrate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({dataset_ids:ids,target_mode:$('#target-mode').value})});$('#integration-state').textContent='Complete';statusBox(box,`Processing complete: ${r.rows.toLocaleString()} rows, ${r.columns.length} columns. `);const a=document.createElement('a');a.href=r.download_url;a.textContent='Download processed CSV';a.style.marginLeft='8px';box.append(a);statusBox($('#integration-log'),`Complete · ${r.rows.toLocaleString()} rows · ${r.columns.length} columns · ${ids.length===1?'standalone source':'two-source integration'} · target mode: ${r.target_mode}.`);$('#integration-details').innerHTML=r.statistics.sources.map(s=>`<div class="validation-item"><b>${escapeHtml(s.source)} · original</b><small>${s.rows.toLocaleString()} rows · ${s.columns} columns · ${s.missing_values.toLocaleString()} missing · ${s.duplicate_rows.toLocaleString()} duplicate rows</small></div>`).join('')+`<div class="validation-item"><b>Processed dataset</b><small>${r.statistics.combined_rows.toLocaleString()} rows · ${r.statistics.combined_columns} columns · target: ${escapeHtml(r.statistics.target_column)}</small></div><div class="validation-item"><b>Target distribution</b><small>${Object.entries(r.statistics.target_counts).map(([k,v])=>`${escapeHtml(k)}: ${v}`).join(' · ')}</small></div>`;}catch(e){$('#integration-state').textContent='Needs attention';statusBox(box,e.message,true);statusBox($('#integration-log'),`Failed · ${e.message}`,true);}});
refresh();
