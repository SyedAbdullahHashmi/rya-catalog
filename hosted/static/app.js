'use strict';
const $ = (s) => document.querySelector(s);
const loginForm = $('#login-form');
if (loginForm) {
  loginForm.addEventListener('submit', async (e) => {
    e.preventDefault(); const button = loginForm.querySelector('button'); button.disabled = true;
    $('#login-error').textContent = '';
    try {
      const res = await fetch('/login', {method: 'POST', headers: {'Content-Type': 'application/json'},
        body: JSON.stringify(Object.fromEntries(new FormData(loginForm)))});
      const data = await res.json(); if (!res.ok) throw new Error(data.error || 'Sign-in failed.');
      location.assign('/');
    } catch (err) { $('#login-error').textContent = err.message; button.disabled = false; }
  });
} else {
  let csrf = '', products = [], version = '', selected = null, operation = crypto.randomUUID();
  let currentCommit = sessionStorage.getItem('catalog_commit') || '', poll = null, busy = false;
  let loadedCatalog = '', loading = false, loadSequence = 0;
  const form = $('#product-form'), catalog = $('#catalog');
  const notice = (message = '') => { $('#notice').textContent = message; $('#notice').hidden = !message; };
  async function api(path, payload) {
    const options = {headers: {}};
    if (payload) Object.assign(options, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-CSRF-Token': csrf}, body: JSON.stringify(payload)});
    const response = await fetch(path, options);
    let data; try { data = await response.json(); } catch { throw new Error('Could not read the server response. Reload before retrying.'); }
    if (response.status === 401) { location.assign('/login'); throw new Error('Please sign in again.'); }
    if (!response.ok) throw new Error(data.error || 'The request could not be completed.');
    return data;
  }
  function node(tag, text, cls) { const element = document.createElement(tag); if (text !== undefined) element.textContent = text; if (cls) element.className = cls; return element; }
  function resetForm() {
    const key = catalog.value; form.reset(); catalog.value = key; selected = null; operation = crypto.randomUUID();
    $('#editor-title').textContent = 'Add something new'; $('#image-preview').hidden = true;
  }
  function render() {
    const term = $('#search').value.trim().toLowerCase(); const list = $('#product-list'); list.replaceChildren();
    $('#product-count').textContent = products.length;
    const matched = products.filter(p => [p.name, p.sku, p.category].join(' ').toLowerCase().includes(term));
    if (!matched.length) list.append(node('p', term ? 'No matching products.' : 'Your collection is ready for its first product.', 'muted'));
    for (const p of matched) {
      const row = node('article', undefined, 'product');
      if (p.preview) { const img = node('img'); img.src = p.preview; img.alt = p.name; img.loading = 'lazy'; row.append(img); }
      else row.append(node('div', 'R', 'placeholder'));
      const copy = node('div', undefined, 'product-copy'); copy.append(node('h3', p.name), node('p', p.sku + ' · ' + (p.category || 'Other')), node('p', p.price, 'price'));
      const badges = node('div', undefined, 'badges'); if(p.best_seller) badges.append(node('span', 'Best seller', 'badge')); if(p.out_of_stock) badges.append(node('span', 'Out of stock', 'badge')); copy.append(badges); row.append(copy);
      const actions = node('div', undefined, 'product-actions');
      const edit = node('button', 'Edit', 'quiet'); edit.type = 'button'; edit.disabled = busy || loading; edit.addEventListener('click', () => {
        if (busy || loading) return;
        resetForm(); selected = p.idx; $('#editor-title').textContent = 'Edit product';
        for (const key of ['name', 'sku', 'description', 'category']) form.elements[key].value = p[key] || '';
        form.elements.price.value = String(p.price || '').replace(/^(?:Rs\.?|INR|₹)\s*/i, '').replace(/,/g, '');
        form.elements.best_seller.checked = !!p.best_seller; form.elements.out_of_stock.checked = !!p.out_of_stock;
        if (p.preview) { $('#image-preview').src = p.preview; $('#image-preview').hidden = false; }
        form.scrollIntoView({behavior: 'smooth', block: 'start'}); form.elements.name.focus();
      });
      const del = node('button', 'Remove', 'quiet delete'); del.type = 'button'; del.disabled = busy || loading;
      del.addEventListener('click', async () => {
        if (busy || loading || !confirm('Remove “' + p.name + '” from the public catalog?')) return;
        setBusy(true); notice();
        try { const result = await api('/api/product', {action: 'delete', catalog: loadedCatalog, idx: p.idx, version, operation: crypto.randomUUID()}); await saved(result); }
        catch(err) { notice(err.message); } finally { setBusy(false); }
      });
      actions.append(edit, del); row.append(actions); list.append(row);
    }
  }
  function setBusy(value) { busy = value; for (const el of form.elements) el.disabled = value || loading; $('#reload').disabled = value || loading; $('#new-product').disabled = value || loading; $('#save-product').disabled = value || loading || !version; render(); }
  async function loadCatalog(preserveForm = false) {
    const key = catalog.value, sequence = ++loadSequence; loading = true; version = ''; setBusy(busy);
    try {
      const data = await api('/api/catalog?catalog=' + encodeURIComponent(key));
      if (sequence !== loadSequence) return;
      products = data.products; version = data.version; loadedCatalog = key;
      if (!preserveForm) resetForm(); render();
    } catch (err) { notice(err.message); throw err; }
    finally { if (sequence === loadSequence) { loading = false; setBusy(busy); } }
  }
  async function checkStatus() {
    clearTimeout(poll);
    try {
      const status = await api('/api/status' + (currentCommit ? '?commit=' + currentCommit : ''));
      $('#publish-title').textContent = {live: 'Catalog published', failed: 'Publishing needs attention', waiting: 'Update saved', building: 'Publishing your collection'}[status.state] || 'Publishing';
      $('#publish-message').textContent = status.message; $('#publish-details').hidden = !status.url;
      if (status.url) $('#publish-details').href = status.url;
      if (status.state === 'waiting' || status.state === 'building') poll = setTimeout(checkStatus, 10000);
    } catch(err) { $('#publish-title').textContent = 'Status unavailable'; $('#publish-message').textContent = err.message; }
  }
  async function saved(result) {
    currentCommit = result.commit; sessionStorage.setItem('catalog_commit', currentCommit);
    $('#publish-title').textContent = 'Update saved'; $('#publish-message').textContent = result.message;
    resetForm(); await loadCatalog(); await checkStatus();
  }
  catalog.addEventListener('change', () => { notice(); loadCatalog().catch(() => {}); });
  $('#reload').addEventListener('click', () => {
    if (selected !== null && !confirm('Reloading clears the edit form so you cannot accidentally change the wrong product. Continue?')) return;
    notice(); loadCatalog(selected === null).catch(() => {});
  });
  $('#new-product').addEventListener('click', () => { if (!busy) resetForm(); });
  $('#search').addEventListener('input', render);
  $('#check-status').addEventListener('click', checkStatus);
  $('#logout').addEventListener('click', async () => { try { await api('/logout', {}); location.assign('/login'); } catch(err) { notice(err.message); } });
  form.elements.image_file.addEventListener('change', async () => {
    const file = form.elements.image_file.files[0]; if (!file) return;
    if (file.size > 8 * 1024 * 1024) { notice('Choose an image smaller than 8 MB.'); form.elements.image_file.value = ''; return; }
    try { $('#image-preview').src = await readFile(file); $('#image-preview').hidden = false; } catch(err) { notice(err.message); }
  });
  function readFile(file) { return new Promise((resolve, reject) => { const r = new FileReader(); r.onload = () => resolve(r.result); r.onerror = () => reject(new Error('The photo could not be read.')); r.readAsDataURL(file); }); }
  form.addEventListener('submit', async (e) => {
    e.preventDefault(); if (busy || loading || !version) return; notice();
    const values = Object.fromEntries(new FormData(form));
    const payload = {action: selected === null ? 'add' : 'edit', idx: selected, catalog: loadedCatalog, version, operation};
    for (const key of ['name', 'sku', 'price', 'category', 'description', 'image_url']) payload[key] = values[key] || '';
    payload.best_seller = form.elements.best_seller.checked; payload.out_of_stock = form.elements.out_of_stock.checked;
    const file = form.elements.image_file.files[0]; setBusy(true);
    try {
      if(file) { if(file.size > 8 * 1024 * 1024) throw new Error('Choose an image smaller than 8 MB.'); payload.image_data = await readFile(file); }
      const result = await api('/api/product', payload); await saved(result);
    } catch(err) { notice(err.message); } finally { setBusy(false); }
  });
  (async () => {
    try { const data = await api('/api/session'); csrf = data.csrf; $('#account').textContent = data.user; $('#public-link').href = data.public_url;
      for (const [key, title] of Object.entries(data.catalogs)) { const option = node('option', title); option.value = key; catalog.append(option); }
      await loadCatalog(); await checkStatus();
    } catch(err) { notice(err.message); }
  })();
}
