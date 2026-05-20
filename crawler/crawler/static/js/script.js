$(function () {
  console.log('ready');

  $('.study-block').on('click', '.exam-details, .results-icon-btn', function () {
    $(this).closest('.study-block').find('.exam-chevron').toggleClass('oi-collapse-down oi-collapse-up');
  });

  function resizeRqFrame() {
    var frame = document.getElementById('prefect');
    if (!frame || !frame.contentDocument) {
      return;
    }
    var doc = frame.contentDocument;
    var height = Math.max(
      doc.body ? doc.body.scrollHeight : 0,
      doc.documentElement ? doc.documentElement.scrollHeight : 0
    );
    if (height > 0) {
      frame.style.height = height + 'px';
      if (doc.body) {
        doc.body.style.overflow = 'hidden';
      }
      if (doc.documentElement) {
        doc.documentElement.style.overflow = 'hidden';
      }
    }
  }

  $('#prefect').on('load', resizeRqFrame);

  $('#reload-button').on('click', function () {
    var frame = document.getElementById('prefect');
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