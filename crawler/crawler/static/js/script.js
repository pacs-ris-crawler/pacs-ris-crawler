$(function () {
  console.log('ready');

  function updateStudyToggle($study, expanded) {
    $study.find('.study-row')
      .toggleClass('is-expanded', expanded);
    $study.find('.exam-toggle')
      .attr('aria-label', expanded ? 'Collapse study' : 'Expand study')
      .attr('aria-expanded', expanded ? 'true' : 'false');
    $study.find('.exam-chevron')
      .toggleClass('bi-chevron-down', !expanded)
      .toggleClass('bi-chevron-up', expanded);
  }

  $('.study-block').on('click', '.study-row', function (e) {
    if ($(e.target).closest('input, a, button').length) return;
    $(this).closest('.study-block').find('.study-details').collapse('toggle');
  });

  $('.study-block').on('click', '.copy-accession-btn', function (e) {
    e.preventDefault();
    e.stopPropagation();

    var $button = $(this);
    var accessionNumber = $button.attr('data-accession-number');
    var showCopied = function () {
      var $icon = $button.find('.copy-accession-icon');
      $icon.removeClass('bi-clipboard-plus').addClass('bi-check2');
      $button.attr('aria-label', 'Accession number copied');
      window.setTimeout(function () {
        $icon.removeClass('bi-check2').addClass('bi-clipboard-plus');
        $button.attr('aria-label', 'Copy accession number ' + accessionNumber);
      }, 1400);
    };
    var copyFallback = function () {
      var $temporaryInput = $('<textarea>').val(accessionNumber).appendTo('body');
      $temporaryInput[0].select();
      var copied = false;
      try {
        copied = document.execCommand('copy');
      } catch (error) {
        copied = false;
      }
      $temporaryInput.remove();
      return copied;
    };

    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(accessionNumber).then(showCopied).catch(function () {
        if (copyFallback()) showCopied();
      });
    } else if (copyFallback()) {
      showCopied();
    }
  });

  $('.study-block').on('show.bs.collapse', '.study-details', function () {
    updateStudyToggle($(this).closest('.study-block'), true);
  });

  $('.study-block').on('hide.bs.collapse', '.study-details', function () {
    updateStudyToggle($(this).closest('.study-block'), false);
  });

  $('.study-details.show').each(function () {
    updateStudyToggle($(this).closest('.study-block'), true);
  });

  var rqFrameResizeTimer = null;

  function resizeRqFrame() {
    var frame = document.getElementById('prefect');
    if (!frame || !frame.contentDocument) {
      return;
    }
    var doc = frame.contentDocument;
    var body = doc.body;
    var root = doc.documentElement;
    var height = Math.max(
      body ? body.scrollHeight : 0,
      body ? body.offsetHeight : 0,
      root ? root.scrollHeight : 0,
      root ? root.offsetHeight : 0
    );
    if (height > 0) {
      frame.style.height = (height + 8) + 'px';
    }
  }

  function scheduleRqFrameResize() {
    if (rqFrameResizeTimer) {
      clearTimeout(rqFrameResizeTimer);
    }
    rqFrameResizeTimer = setTimeout(resizeRqFrame, 50);
  }

  function watchRqFrame() {
    var frame = document.getElementById('prefect');
    if (!frame || !frame.contentDocument || !frame.contentDocument.body) {
      return;
    }
    if (frame._rqResizeObserver) {
      frame._rqResizeObserver.disconnect();
    }
    frame._rqResizeObserver = new MutationObserver(scheduleRqFrameResize);
    frame._rqResizeObserver.observe(frame.contentDocument.body, {
      childList: true,
      subtree: true,
      attributes: true,
      characterData: true
    });
  }

  function onRqFrameLoad() {
    resizeRqFrame();
    watchRqFrame();
    scheduleRqFrameResize();
    setTimeout(resizeRqFrame, 250);
    setTimeout(resizeRqFrame, 1000);
  }

  $('#prefect').on('load', onRqFrameLoad);

  $('#reload-button').on('click', function () {
    var frame = document.getElementById('prefect');
    if (frame._rqResizeObserver) {
      frame._rqResizeObserver.disconnect();
      frame._rqResizeObserver = null;
    }
    frame.src = frame.src;
  });


  $('.prefetch-batch-upload').submit(function (e) {
    var form = $(this);
    var url = form.attr('action');

    var acc_numbers = $("#accession_numbers").val().split(" ").filter(Boolean)
    console.log(acc_numbers)
    if (acc_numbers.length > 0) {
      for (let index = 0; index < acc_numbers.length; index++) {
        const element = acc_numbers[index];
        $.ajax({
          type: "GET",
          url: url,
          data: {"accession_number": element},
          success: function (data) {
            console.log(data);
            noty({
              type: 'info',
              text: 'Jobs submitted',
              layout: 'centerRight',
              timeout: '3000',
              closeWith: ['click', 'hover'],
              theme: 'metroui'
            }).show();
          }
        })
      }
    } else {
      $.ajax({
        type: "GET",
        url: url,
        data: form.serialize(),
        success: function (data) {
          console.log(data);
          noty({
            type: 'info',
            text: 'Jobs submitted',
            layout: 'centerRight',
            timeout: '3000',
            closeWith: ['click', 'hover'],
            theme: 'metroui'
          }).show();
        }
      })
    }
    e.preventDefault();
  });

  $('.batch-upload').submit(function (e) {
    var form = $(this);
    var url = form.attr('action');

    var acc_numbers = $("#accession_numbers").val().split(" ").filter(Boolean)
    var dicom_node = $("#dicom_node_upload").val()

    if (acc_numbers.length > 0) {
      for (let index = 0; index < acc_numbers.length; index++) {
        const element = acc_numbers[index];
        $.ajax({
          type: "GET",
          url: url,
          data: {"accession_number": element, "dicom_node": dicom_node},
          success: function (data) {
            console.log(data);
            noty({
              type: 'info',
              text: 'Jobs submitted',
              layout: 'centerRight',
              timeout: '3000',
              closeWith: ['click', 'hover'],
              theme: 'metroui'
            }).show();
          }
        })
      }
    } else {
      $.ajax({
        type: "GET",
        url: url,
        data: form.serialize(),
        success: function (data) {
          console.log(data);
          noty({
            type: 'info',
            text: 'Jobs submitted',
            layout: 'centerRight',
            timeout: '3000',
            closeWith: ['click', 'hover'],
            theme: 'metroui'
          }).show();
        }
      })
    }
    e.preventDefault();
  });


  $('#upload-button').on('click', function (e) {
    e.preventDefault();
    var acc = $('#search-input').val();
    var day = $('#day-input').val();
    var data = {
      'acc': acc,
      'day': day
    }
    $.ajax({
      type: 'POST',
      url: 'upload',
      data: JSON.stringify(data),
      dataType: 'json'
    }).done(function (data) {
      noty({
        text: 'Successfully uploaded to RIS/PACS Crawler',
        layout: 'centerRight',
        timeout: '3000',
        closeWith: ['click', 'hover'],
        type: 'success'
      });
    }).fail(function (error) {
      noty({
        text: 'Upload failed: ' + error.responseText,
        layout: 'topRight',
        timeout: '3000',
        closeWith: ['click', 'hover'],
        type: 'error'
      });
      console.log(error);
      console.error("Upload failed");
    });
  });
});