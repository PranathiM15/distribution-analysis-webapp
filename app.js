(() => {
  const $ = (id) => document.getElementById(id);
  const fileInput = $('csvFile');
  const dropzone = $('dropzone');
  const columnSelect = $('columnSelect');
  const binsRange = $('binsRange');
  const binsValue = $('binsValue');
  const analyzeButton = $('analyzeButton');
  const formStatus = $('formStatus');
  const sampleButton = $('sampleButton');
  let csvText = '';
  let currentFileName = 'student_performance.csv';
  let toastTimer;

  function status(message, kind = '') {
    formStatus.textContent = message;
    formStatus.className = `form-status ${kind}`.trim();
  }
  function toast(message) {
    const element = $('toast');
    element.textContent = message;
    element.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => element.classList.remove('show'), 2600);
  }
  async function postJson(url, body) {
    const response = await fetch(url, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    let result;
    try { result = await response.json(); }
    catch { throw new Error('The local server returned an unreadable response. Restart it and try again.'); }
    if (!response.ok || result.error) throw new Error(result.error || 'Something went wrong.');
    return result;
  }
  function setFileDetails(name, rows, columns) {
    $('fileName').textContent = name;
    $('fileMeta').textContent = `${Number(rows).toLocaleString()} rows · ${columns} columns`;
    $('fileCheck').textContent = '✓';
    $('resultCount').textContent = `${Number(rows).toLocaleString()} SOURCE ROWS`;
    $('previewCount').textContent = `FIRST 5 OF ${Number(rows).toLocaleString()} ROWS`;
  }
  function renderPreview(preview, allColumns) {
    const table = $('previewTable');
    table.replaceChildren();
    const head = document.createElement('thead');
    const headerRow = document.createElement('tr');
    allColumns.forEach((column) => {
      const th = document.createElement('th');
      th.textContent = column;
      headerRow.appendChild(th);
    });
    head.appendChild(headerRow);
    const body = document.createElement('tbody');
    preview.forEach((item) => {
      const tr = document.createElement('tr');
      allColumns.forEach((column) => {
        const td = document.createElement('td');
        const value = item[column];
        td.textContent = value === null || value === undefined ? '—' : String(value);
        tr.appendChild(td);
      });
      body.appendChild(tr);
    });
    table.append(head, body);
  }
  async function loadCsv(text, name) {
    if (!text || !text.trim()) throw new Error('This file is empty. Please choose a CSV with data.');
    if (new Blob([text]).size > 10 * 1024 * 1024) throw new Error('The CSV is over 10 MB. Please choose a smaller file.');
    csvText = text;
    currentFileName = name || 'uploaded.csv';
    status('Reading columns and checking numeric values…');
    analyzeButton.disabled = true;
    columnSelect.disabled = true;
    binsRange.disabled = true;
    const data = await postJson('/api/inspect', { csv: csvText });
    columnSelect.replaceChildren();
    data.columns.forEach((column) => {
      const option = document.createElement('option');
      option.value = column;
      option.textContent = column;
      columnSelect.appendChild(option);
    });
    columnSelect.disabled = false;
    binsRange.disabled = false;
    analyzeButton.disabled = false;
    setFileDetails(currentFileName, data.rows, data.column_count);
    renderPreview(data.preview, data.all_columns);
    status(`Ready · ${data.columns.length} numeric column(s) detected. Generate your histogram.`, 'success');
    await runAnalysis(false);
  }
  function renderStats(stats) {
    const grid = $('statsGrid');
    grid.replaceChildren();
    stats.forEach((stat, index) => {
      const card = document.createElement('div');
      card.className = 'stat-card';
      const label = document.createElement('span');
      label.className = 'stat-label';
      label.textContent = `${String(index + 1).padStart(2, '0')} / ${stat.label.toUpperCase()}`;
      const value = document.createElement('strong');
      value.className = 'stat-value';
      value.textContent = stat.value;
      const detail = document.createElement('small');
      detail.textContent = stat.detail;
      card.append(label, value, detail);
      grid.appendChild(card);
    });
  }
  function renderInsights(items) {
    const list = $('insightsList');
    list.replaceChildren();
    items.forEach((item, index) => {
      const card = document.createElement('article');
      card.className = 'insight-card';
      const number = document.createElement('span');
      number.className = 'insight-number';
      number.textContent = `0${index + 1}`;
      const heading = document.createElement('h3');
      heading.textContent = item.title;
      const paragraph = document.createElement('p');
      paragraph.textContent = item.text;
      card.append(number, heading, paragraph);
      list.appendChild(card);
    });
  }
  async function runAnalysis(showToast = true) {
    if (!csvText || !columnSelect.value) return;
    analyzeButton.disabled = true;
    analyzeButton.querySelector('span:first-child').textContent = 'Analyzing…';
    status('Calculating statistics and drawing the histogram…');
    try {
      const result = await postJson('/api/analyze', {
        csv: csvText,
        filename: currentFileName,
        column: columnSelect.value,
        bins: Number(binsRange.value),
      });
      renderStats(result.stats);
      renderInsights(result.observations);
      const image = $('histogramImage');
      image.src = result.histogram;
      image.hidden = false;
      document.querySelector('.chart-empty').hidden = true;
      $('chartSubtitle').textContent = `${result.column} · ${result.count.toLocaleString()} valid observations`;
      $('chartBinLabel').textContent = `${result.bins} BINS`;
      $('resultCount').textContent = `${result.rows.toLocaleString()} SOURCE ROWS`;
      renderPreview(result.preview, result.all_columns);
      status(`Analysis complete · ${result.count} valid numeric values analyzed.`, 'success');
      if (showToast) toast(`Histogram generated for ${result.column}.`);
    } catch (error) {
      status(error.message || 'Analysis failed. Check the CSV and try again.', 'error');
      toast(error.message || 'Analysis failed.');
    } finally {
      analyzeButton.disabled = !csvText || columnSelect.options.length === 0;
      analyzeButton.querySelector('span:first-child').textContent = 'Generate analysis';
    }
  }
  async function chooseFile(file) {
    if (!file) return;
    if (!file.name.toLowerCase().endsWith('.csv') && file.type !== 'text/csv') {
      status('Please select a .csv file. Excel workbooks are not supported directly.', 'error');
      toast('Please choose a CSV file.');
      return;
    }
    if (file.size > 10 * 1024 * 1024) {
      status('This file is over 10 MB. Please choose a smaller CSV.', 'error');
      return;
    }
    try {
      await loadCsv(await file.text(), file.name);
      toast(`Loaded ${file.name}`);
    } catch (error) {
      status(error.message || 'Could not load the file.', 'error');
    }
  }

  fileInput.addEventListener('change', (event) => chooseFile(event.target.files[0]));
  ['dragenter', 'dragover'].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
    event.preventDefault(); dropzone.classList.add('dragging');
  }));
  ['dragleave', 'drop'].forEach((eventName) => dropzone.addEventListener(eventName, (event) => {
    event.preventDefault(); dropzone.classList.remove('dragging');
  }));
  dropzone.addEventListener('drop', (event) => chooseFile(event.dataTransfer.files[0]));
  sampleButton.addEventListener('click', async () => {
    sampleButton.disabled = true;
    try {
      const response = await fetch('/sample_dataset.csv', { cache: 'no-store' });
      if (!response.ok) throw new Error('Sample dataset was not found. Check that sample_dataset.csv is in the app folder.');
      await loadCsv(await response.text(), 'sample_dataset.csv');
      toast('Sample dataset loaded.');
    } catch (error) {
      status(error.message || 'Could not load the sample dataset.', 'error');
    } finally { sampleButton.disabled = false; }
  });
  binsRange.addEventListener('input', () => { binsValue.textContent = `${binsRange.value} bins`; });
  columnSelect.addEventListener('change', () => runAnalysis(false));
  binsRange.addEventListener('change', () => runAnalysis(false));
  analyzeButton.addEventListener('click', () => runAnalysis(true));

  // Load the included sample so the dashboard is useful immediately on launch.
  fetch('/sample_dataset.csv', { cache: 'no-store' })
    .then((response) => { if (!response.ok) throw new Error('Start the app from run_app.bat so the local server can load the sample dataset.'); return response.text(); })
    .then((text) => loadCsv(text, 'sample_dataset.csv'))
    .catch((error) => status(error.message || 'Could not load sample data.', 'error'));
})();
