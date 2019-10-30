$(function () {
  console.log("ready!");

  var startDatePicker = $('#start-date-picker').pikaday({
    format: 'DD.MM.YYYY',
    firstDay: 1,
    minDate: new Date(2005, 0, 1),
    maxDate: new Date(),
    yearRange: [2005, 2019]
  });

  var endDatePicker = $('#end-date-picker').pikaday({
    format: 'DD.MM.YYYY',
    firstDay: 1,
    minDate: new Date(2005, 0, 1),
    maxDate: new Date(),
    yearRange: [2005, 2019]
  });

  var getCheckedData = function () {
    return $('input:checked[name=series]')
      .map(function () {
        var patient_id = $(this).attr('data-patient-id');
        var patient_birth_date = $(this).attr('data-patient-birthdate');
        var study_uid = $(this).attr('data-study-id');
        var study_description = $(this).attr('data-study-description')
        var study_date = $(this).attr('data-study-date');
        var series_uid = $(this).attr('data-series-id');
        var accession_number = $(this).attr('data-accession-number');
        var series_number = $(this).attr('data-series-number');
        var series_description = $(this).attr('data-series-description');
        result = {
          "patient_id": patient_id,
          "patient_birth_date": patient_birth_date,
          "study_uid": study_uid,
          "study_description": study_description,
          "study_date": study_date,
          "series_uid": series_uid,
          "accession_number": accession_number,
          "series_number": series_number,
          "series_description": series_description
        };
        return result;
      })
      .get();
  };

  var getUniqueAccessionNumbers = function (data) {
    var set = new Set();
    for (i = 0; i < data.length; ++i) {
      set.add(data[i].accession_number);
    };
    return set;
  };

  $('#expand-all').on('click', function (e) {
    $('.collapse').slice(1).collapse('show');
  });

  $('#collapse-all').on('click', function (e) {
    $('.collapse').slice(1).collapse('hide');
  });


  $('.page-link').on('click', function (e) {
    page = $(this).data('page');
    offset = $(this).data('offset');
    $('input[name="offset"]').val(offset);
    $('input[name="page"]').val(page);
    $('#search-form').submit();
  });


  $("#export").on('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    if (parseInt($('#studies_result').html()) > 10000) {
      noty({
        text: 'Too many results to export (Studies > 10000)',
        layout: 'centerRight',
        timeout: '3000',
        closeWith: ['click', 'hover'],
        type: 'error'
      });
      return
    }
    $('#loading').removeClass('d-none');
    q = $('#search-form').serialize();
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/export', true);
    xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    xhr.responseType = 'blob';
    xhr.onload = function (e) {
      if (this.status == 200) {
        $('#loading').addClass('d-none');
        var blob = this.response;
        saveAs(blob, 'download.xlsx');
      } else if (this.status >= 400 || this.status == 500) {
        $('#loading').addClass('d-none');
      }
    };
    xhr.send(q);

    return false;
  });
  
  
  $("#export_anon").on('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    if (parseInt($('#studies_result').html()) > 10000) {
      noty({
        text: 'Too many results to export (Studies > 10000)',
        layout: 'centerRight',
        timeout: '3000',
        closeWith: ['click', 'hover'],
        type: 'error'
      });
      return
    }
    $('#loading').removeClass('d-none');
    q = $('#search-form').serialize();
    var xhr = new XMLHttpRequest();
    xhr.open('POST', '/export_anon', true);
    xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
    xhr.responseType = 'blob';
    xhr.onload = function (e) {
      if (this.status == 200) {
        $('#loading').addClass('d-none');
        var blob = this.response;
        saveAs(blob, 'download.xlsx');
      } else if (this.status >= 400 || this.status == 500) {
        $('#loading').addClass('d-none');
      }
    };
    xhr.send(q);

    return false;
  });
  

  $("#download-ris-reports").on('click', function (e) {
    e.preventDefault();
    var data = getCheckedData();
    var aNum_set = getUniqueAccessionNumbers(data);
    var zip = new JSZip();
    for (var it = aNum_set.values(), item = null; item = it.next().value;) {
      name = item + '-report';
      text = document.getElementById(name).innerText;
      zip.file(name + '.txt', text);
    }
    zip.generateAsync({ type: "blob" })
      .then(function (content) {
        saveAs(content, "reports.zip");
      });
  });

  $('#transfer-button').on('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    var target = $("input[type='radio'][name='target']:checked").val();
    var selection = $("input[name='transfer-selection']:checked", "#transfer-form").val();
    console.log(selection);
    if ("all" === selection) {
      $('#loading').removeClass('d-none');
      q = $('#search-form').serialize() + "&target=" + target + "&selection=" + selection;
      var xhr = new XMLHttpRequest();
      xhr.open('POST', '/transfer-all', true);
      xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
      xhr.responseType = 'json';
      xhr.onload = function (e) {
        if (this.status == 200) {
          $('#loading').addClass('d-none');
          var data = this.response;
          console.log(data)
          noty({
            text: 'Successfully added ' + data.series_length + ' series',
            layout: 'centerRight',
            timeout: '3000',
            closeWith: ['click', 'hover'],
            type: 'success'
          });
        } else if (this.status >= 400 || this.status == 500) {
          $('#loading').addClass('d-none');
          noty({
            text: 'Can\'t get connection to MOVA. Download failed!',
            layout: 'centerRight',
            timeout: '3000',
            closeWith: ['click', 'hover'],
            type: 'error'
          });
        }
      };
      xhr.send(q);
    } else {
      var checkedData = getCheckedData();
      var data = {
        'data': checkedData,
        'target': target
      }
      $.ajax({
        type: 'POST',
        url: 'transfer',
        data: JSON.stringify(data),
        dataType: 'json'
      }).done(function (data) {
        noty({
          text: 'Successfully added ' + data.series_length + ' studies to transfer',
          layout: 'centerRight',
          timeout: '3000',
          closeWith: ['click', 'hover'],
          type: 'success'
        });
      }).fail(function (error) {
        console.log(error);
        console.error("Post failed");
        noty({
          text: 'Can\'t get connection to MOVA',
          layout: 'centerRight',
          timeout: '3000',
          closeWith: ['click', 'hover'],
          type: 'error'
        });
      });
    }
  });

  $('#download-button').on('click', function (e) {
    e.preventDefault();
    e.stopPropagation();
    var dirName = $('#download-dir').val();
    var regex = /^[a-zA-Z0-9_-]+$/
    var selection = $("input[name='download-selection']:checked", "#download-form").val();
    if (!dirName) {
      setError('Please put in folder name, allowed characters are: a-Z, 0-9,_,-');
      return
    } else if (dirName.indexOf(' ') >= 0) {
      setError('No spaces are allowed');
      return
    } else if (!regex.test(dirName)) {
      setError('Allowed characters are: a-Z,0-9,_,-');
      return
    } else {
      clearError();
    }

    if ("all" === selection) {
      $('#loading').removeClass('d-none');
      q = $('#search-form').serialize() + "&download-dir=" + dirName + "&selection=" + selection;
      var xhr = new XMLHttpRequest();
      xhr.open('POST', '/download-all', true);
      xhr.setRequestHeader("Content-type", "application/x-www-form-urlencoded");
      xhr.responseType = 'json';
      xhr.onload = function (e) {
        if (this.status == 200) {
          $('#loading').addClass('d-none');
          var data = this.response;
          noty({
            text: 'Successfully added ' + data.series_length + ' series',
            layout: 'centerRight',
            timeout: '3000',
            closeWith: ['click', 'hover'],
            type: 'success'
          });
        } else if (this.status >= 400 || this.status == 500) {
          $('#loading').addClass('d-none');
          noty({
            text: 'Can\'t get connection to MOVA. Download failed!',
            layout: 'centerRight',
            timeout: '3000',
            closeWith: ['click', 'hover'],
            type: 'error'
          });
        }
      };
      xhr.send(q);
    } else {
      var checkedData = getCheckedData();
      var data = {
        'data': checkedData,
        'dir': dirName
      }
      $.ajax({
        type: 'POST',
        url: 'download',
        data: JSON.stringify(data),
        dataType: 'json'
      }).done(function (data) {
        noty({
          text: 'Successfully added ' + data.series_length + ' series',
          layout: 'centerRight',
          timeout: '3000',
          closeWith: ['click', 'hover'],
          type: 'success'
        });
      }).fail(function (error) {
        console.log(error);
        console.error("Post failed");
        noty({
          text: 'Can\'t get connection to MOVA. Download failed!',
          layout: 'centerRight',
          timeout: '3000',
          closeWith: ['click', 'hover'],
          type: 'error'
        });
      });
    }
  });


  if ('download-status' == $('body').data('page')) {
    $.get('/tasks/data',
      function (data) {
        $('#container').html(data);
        $(document).on('click', 'input[name=select-all-resend]', function (e) {
          var value = $(this).prop("checked")
          $("input:checkbox").prop('checked', value);
        });
        $(document).on('click', '#resend', function (e) {
          var checkedData = getCheckedData();
          var dir_name_element = $('input:checked[name=series]')
          var dir_name = $(dir_name_element[0]).data('dir');
          var data = {
            'data': checkedData,
            'dir': dir_name
          }
          $.ajax({
            type: 'POST',
            url: 'download',
            data: JSON.stringify(data),
            dataType: 'json'
          }).done(function (data) {
            noty({
              text: 'Successfully added ' + data.series_length + ' series',
              layout: 'centerRight',
              timeout: '3000',
              closeWith: ['click', 'hover'],
              type: 'success'
            });
          }).fail(function (error) {
            console.log(error);
            console.error("Post failed");
          });
        });
      });
  }

  setError = function (text) {
    $('#download-dir').addClass('is-invalid');
    $('#download-error-text').text(text);
    $('input[name=download-dir]').addClass("invalid");
  }

  clearError = function () {
    $('#download-dir').removeClass('is-invalid');
    $('#download-error-text').text('');
    $('input[name=download-dir]').removeClass("form-control-danger");
  }

  $('input[name=select-all-accession-number').on('click', function (e) {
    var accession_number = $(e.target).data('accession-number');
    var table = $('table[data-accession-number="' + accession_number + '"]')[0];
    var value = $(this).prop("checked")
    $("td input:checkbox", table).prop('checked', value);
  });

  $('input[name=select-all-patient').on('click', function (e) {
    var value = $(this).prop("checked")
    var patientId = $(e.target).attr('data-patient-id');
    var selector = 'table[data-patient-id="' + patientId + '"]'
    $(selector).find('input:checkbox').prop('checked', value)
    var selector2 = 'input[data-patient-id="' + patientId + '"]'[0]
    $(selector2).prop('checked', value)
  });

  $('input[name=select-all-page').on('click', function (e) {
    var value = $(this).prop("checked")
    $("input:checkbox").not('.modality').prop('checked', value);
  });

  $('li.list-group-item.patients a').on('click', function (e) {
    // parent is in because user can click also on icon
    $(e.target).parent().find('span').first().toggleClass('oi-collapse-down oi-collapse-up');
  });

  $('a.exam-details').on('click', function (e) {
    // parent is in because user can click also on icon
    $(e.target).parent().find('span').first().toggleClass('oi-collapse-down oi-collapse-up');
  });

  /**
   * Pasting the names will escape them automatically. This means that a
   * name like Jon Doe will be become "John\^Doe". In the PACS the whitespace
   * is replace by a '^'. The usecase is that people are coming with lists of
   * names and they don't need to remember how to escape it properly.
   */
  $('#patientname-input').on('paste', function (e) {
    // cancel paste
    e.preventDefault();
    var data = e.originalEvent.clipboardData.getData('Text');
    var names = data.split(/(?:\r\n|\r|\n)/g);
    names = names.map(function (x) { return x.trim(); });
    names = names.filter(function (x) { return x !== '' });
    names = names.map(function (x) { return x.replace(/\s/g, "\^"); });
    names = names.map(function (x) { return '"' + x.toUpperCase() + '"' });
    value = names.join(',');
    $('#patientname-input').val(value);
  });

  if ('statistics' == $('body').data('page')) {
    function draw_statistics() {
      // Assign the specification to a local variable vlSpec.
      var vlSpec = {
        "$schema": "https://vega.github.io/schema/vega-lite/v2.json",
        "data": { "url": "statistics/data.csv" },
        "mark": {
          "type": "line",
          "point": "true"
        },
        "title": "PACS Study Distribution",
        "width": 420,
        "height": 380,
        "transform": [{
          "filter": { "field": "year", "timeUnit": "year", "range": [2007, 2019] }
        }],
        "encoding": {
          "x": {
            "field": "year",
            "type": "temporal",
            "axis": {
              "format": "%Y",
              "title": "Years"
            }
          },
          "y": {
            "field": "InstitutionName",
            "type": "quantitative",
            "axis": {
              "title": "Number of Studies"
            }
          },
          "color": {
            "field": "institution_type",
            "type": "nominal",
            "legend": { "title": "Type" }
          }
        }
      }
      // Embed the visualization in the container with id `vis`
      vegaEmbed("#vis", vlSpec, { "actions": false });
    };
    draw_statistics()
  }
});
