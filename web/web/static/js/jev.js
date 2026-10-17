$(function () {
  var panel = $('#jev-panel');
  if (!panel.length) return;
  var open = false, queries = [], selected = 0, completed = null, run = null;
  var pending = false, history = [], generation = 0, pageRequest = null;
  var initialSearch = searchValues();

  function searchValues() {
    return $('#search-form').serializeArray().filter(function (p) {
      return p.name !== 'page' && p.name !== 'offset';
    }).map(function (p) { return [p.name, p.value]; });
  }
  function clone(value) { return JSON.parse(JSON.stringify(value)); }
  function log(message) { history.push(new Date().toISOString() + ' ' + message); }
  function error(message) { $('#jev-error').text(message || ''); }
  function post(url, data) {
    return $.ajax({url: '/jev/' + url, method: 'POST', contentType: 'application/json', data: JSON.stringify(data)});
  }
  function failure(xhr) { return xhr.responseJSON && xhr.responseJSON.error || 'Request failed. Try again.'; }
  function blankQuery() { return {name: '', type: 'noul', instructions: '', options: [['', ''], ['', '']]}; }
  function dirty(q) { return !q.saved || JSON.stringify(q.draft) !== JSON.stringify(q.saved); }
  function apiQuery(q) {
    var result = {name: q.name, type: q.type, instructions: q.instructions};
    if (q.type === 'choice') {
      result.criteria = Object.create(null);
      q.options.forEach(function (o) { result.criteria[o[0]] = o[1] || o[0]; });
    }
    return result;
  }
  function controls() {
    var busy = !!run || pending;
    $('#jev-fields').prop('disabled', busy || !queries.length);
    $('#jev-add, #jev-name').prop('disabled', busy);
    $('#jev-apply').prop('disabled', busy || !queries.length || queries.some(dirty));
    $('#jev-interrupt').toggleClass('d-none', !run).prop('disabled', !!run && run.stopped);
    $('#jev-export-state').text(completed ? 'Excel uses the last completed run.' : 'No Kev annotations in Excel yet.');
    $('#jev-draft').text(queries.length ? (dirty(queries[selected]) ? 'Unconfirmed changes' : 'Confirmed') : 'Add a query to begin.');
  }
  function tabs() {
    $('#jev-queries').empty();
    queries.forEach(function (q, i) {
      $('<button type="button" class="list-group-item list-group-item-action py-2 small">')
        .text((i + 1) + '. ' + (q.draft.name || 'New query') + (dirty(q) ? ' *' : ''))
        .toggleClass('active', i === selected).attr('aria-current', i === selected ? 'true' : 'false')
        .on('click', function () { selected = i; editor(); }).appendTo('#jev-queries');
    });
    controls();
  }
  function optionRow(option) {
    var row = $('<div class="jev-option">');
    $('<input class="form-control form-control-sm" aria-label="Option name" placeholder="Option name">').val(option[0]).appendTo(row);
    $('<input class="form-control form-control-sm" aria-label="Option description" placeholder="Description (optional)">').val(option[1]).appendTo(row);
    $('<button type="button" class="btn btn-outline-secondary btn-sm" aria-label="Remove option">').text('×').on('click', function () { row.remove(); readDraft(); }).appendTo(row);
    row.appendTo('#jev-options');
  }
  function editor() {
    var q = queries.length ? queries[selected].draft : blankQuery();
    $('#jev-query-name').val(q.name);
    $('#jev-type').val(q.type);
    $('#jev-question').val(q.instructions);
    $('#jev-choice').toggleClass('d-none', q.type !== 'choice');
    $('#jev-options').empty();
    q.options.forEach(optionRow);
    tabs();
  }
  function readDraft() {
    if (!queries.length) return;
    queries[selected].draft = {
      name: $('#jev-query-name').val(), type: $('#jev-type').val(), instructions: $('#jev-question').val(),
      options: $('#jev-options .jev-option').map(function () {
        var inputs = $(this).find('input'); return [[$(inputs[0]).val(), $(inputs[1]).val()]];
      }).get()
    };
    $('#jev-choice').toggleClass('d-none', $('#jev-type').val() !== 'choice');
    tabs();
  }
  $('#jev-editor').on('input change', 'input, textarea, select', readDraft);
  $('#jev-option-add').on('click', function () { optionRow(['', '']); readDraft(); });
  $('#jev-add').on('click', function () {
    queries.push({draft: blankQuery(), saved: null}); selected = queries.length - 1; editor();
  });
  $('#jev-remove').on('click', function () {
    log('Removed query: ' + (queries[selected].draft.name || 'unnamed'));
    queries.splice(selected, 1); selected = Math.max(0, selected - 1); editor();
  });
  $('#jev-editor').on('submit', function (e) {
    e.preventDefault();
    var q = clone(queries[selected].draft);
    q.name = q.name.trim(); q.instructions = q.instructions.trim();
    q.options = q.options.map(function (o) { return o.map(function (v) { return v.trim(); }); });
    if (!q.name || !q.instructions) return error('Enter a name and question.');
    if (queries.some(function (other, i) { return i !== selected && other.saved && other.saved.name === q.name; })) return error('Query names must be unique.');
    if (q.type === 'choice') {
      var names = q.options.map(function (o) { return o[0]; });
      if (names.length < 2 || names.some(function (n) { return !n; }) || new Set(names).size !== names.length) return error('Add at least two options with unique, nonempty names.');
    }
    queries[selected] = {draft: clone(q), saved: clone(q)};
    log('Confirmed query: ' + q.name); error(''); editor();
  });

  $('#jev-open').on('click', function () {
    if (!$('#studies_result').length || JSON.stringify(searchValues()) !== JSON.stringify(initialSearch)) {
      noty({text: 'Run the search first, then open Kev.', type: 'information', timeout: 3000}); return;
    }
    open = true; $('#search-form').addClass('d-none'); panel.removeClass('d-none');
    if (!queries.length) $('#jev-add').trigger('click');
    $('#jev-status').text('Ready. The whole search cohort will be annotated, across all pages.');
  });
  $('#jev-close').on('click', function () {
    if (run) run.stopped = true;
    generation++; open = false; run = null; queries = []; completed = null; history = [];
    if (pageRequest) pageRequest.abort();
    panel.addClass('d-none'); $('#search-form').removeClass('d-none');
    $('#jev-name').val('Cohort annotation'); $('#jev-summary, #jev-progress').addClass('d-none');
    $('#jev-summary-text, #jev-status').text(''); error(''); controls();
  });
  $('#jev-interrupt').on('click', function () {
    if (!run) return;
    run.stopped = true; log('Interrupted run.');
    $('#jev-status').text('Stopping after the current batch. No further batches will be sent.');
    controls();
  });
  function duration(seconds) {
    seconds = Math.max(0, Math.ceil(seconds));
    return seconds < 60 ? seconds + 's' : Math.floor(seconds / 60) + 'm ' + (seconds % 60) + 's';
  }
  function progress(r) {
    if (run !== r || r.stopped) return;
    var elapsed = (Date.now() - r.clock) / 1000;
    var done = r.outcomes.length;
    var rate = done ? r.measured / done : .0224 + .0047 * r.queries.length;
    var remaining = Math.max(0, (r.total - done) * rate - (elapsed - r.measured));
    $('#jev-progress').removeClass('d-none').attr('max', r.total || 1).val(done);
    $('#jev-status').text(done + ' / ' + r.total + ' studies · ' + duration(elapsed) + ' elapsed · ' +
      (remaining ? '~' + duration(remaining) + ' remaining' : 'finishing current batch…'));
  }
  $('#jev-apply').on('click', async function () {
    if (run || pending || queries.some(dirty)) return;
    if (!$('#jev-name').val().trim()) return error('Enter a pipeline name.');
    error(''); log('Started pipeline.');
    var token = generation;
    var r = {name: $('#jev-name').val().trim(), queries: queries.map(function (q) { return apiQuery(q.saved); }),
      search: clone(initialSearch), started: new Date().toISOString(), clock: Date.now(), measured: 0,
      outcomes: [], total: 0, stopped: false};
    run = r; pending = true; controls(); $('#jev-status').text('Checking the search cohort…');
    var timer;
    try {
      var cohort = await post('cohort', {search: r.search});
      if (token !== generation || r.stopped) return;
      r.model = cohort.model; r.total = cohort.studies.length;
      if (!r.total) { error('No studies in this search.'); return; }
      var remaining = cohort.studies.slice();
      timer = setInterval(function () { progress(r); }, 1000); progress(r);
      while (remaining.length && !r.stopped && token === generation) {
        var batch = remaining.splice(0, 100);
        var result = await post('batch', {search: r.search, queries: r.queries, studies: batch});
        if (r.stopped || token !== generation) return;
        if (!result.outcomes.length) throw new Error('No progress in the batch. Try again.');
        r.outcomes = r.outcomes.concat(result.outcomes);
        remaining = result.remaining.concat(remaining);
        r.measured = (Date.now() - r.clock) / 1000; progress(r);
      }
      if (r.stopped || token !== generation) return;
      r.elapsed = (Date.now() - r.clock) / 1000;
      var missing = r.outcomes.filter(function (o) { return o.status === 'missing'; }).length;
      var failed = r.outcomes.filter(function (o) { return o.status === 'failed'; }).length;
      log('Completed: ' + r.total + ' studies, ' + missing + ' missing reports, ' + failed + ' failures.');
      r.history = history.slice(); completed = r;
      $('#jev-status').text('Complete · ' + r.total + ' studies in ' + duration(r.elapsed) + ' · ' + missing + ' missing · ' + failed + ' failed. Details in Summary.');
      if (!$('#jev-summary').hasClass('d-none')) showSummary();
    } catch (xhr) {
      if (token === generation && !r.stopped) { log('Run failed. Previous completed annotations retained.'); error(xhr.message || failure(xhr)); $('#jev-status').text('Run stopped. Previous completed annotations retained.'); }
    } finally {
      clearInterval(timer); pending = false;
      if (run === r) {
        if (r.stopped) $('#jev-status').text('Interrupted. Previous completed annotations retained.');
        run = null;
      }
      controls();
    }
  });

  function summaryRun() {
    return completed || {name: $('#jev-name').val().trim(), model: 'Not run yet', started: 'Not run yet', elapsed: 0,
      search: initialSearch, queries: queries.filter(function (q) { return q.saved; }).map(function (q) { return apiQuery(q.saved); }), outcomes: [], history: history};
  }
  async function showSummary(download) {
    var token = generation;
    try {
      var text = await post('summary', summaryRun());
      if (token !== generation) return;
      $('#jev-summary-text').text((completed ? 'Last completed run\n\n' : 'Confirmed configuration (not run)\n\n') + text);
      if (download) saveAs(new Blob([text], {type: 'text/plain;charset=utf-8'}), 'kev-summary.txt');
    } catch (xhr) { if (token === generation) error(failure(xhr)); }
  }
  $('#jev-summary-toggle').on('click', function () {
    $('#jev-summary').toggleClass('d-none');
    if (!$('#jev-summary').hasClass('d-none')) showSummary();
  });
  $('#jev-summary-download').on('click', function () { showSummary(true); });

  window.kev = {
    isOpen: function () { return open; },
    exportData: function () { return completed ? {search: initialSearch, jev: completed} : null; },
    page: function (link) {
      if (pageRequest) return;
      var page = $(link).data('page'), offset = $(link).data('offset'), token = generation;
      var params = initialSearch.map(function (p) { return {name: p[0], value: p[1]}; });
      params.push({name: 'page', value: page}, {name: 'offset', value: offset});
      pageRequest = $.ajax({url: '/search', method: 'POST', data: $.param(params), headers: {'X-Kev-Page': '1'}})
        .done(function (html) {
          if (token !== generation) return;
          var content = $('<div>').append($.parseHTML(html));
          if (!content.find('.results-panel').length) return error('Could not load the results page.');
          $('#table-view').html(content.contents());
          $('#search-form input[name="page"]').val(page); $('#search-form input[name="offset"]').val(offset);
        }).fail(function (xhr, status) { if (status !== 'abort' && token === generation) error('Could not load the results page.'); })
        .always(function () { pageRequest = null; });
    }
  };
});
