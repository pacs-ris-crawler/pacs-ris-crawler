$(function () {
  console.log('ready');

  $('#reload-button').on('click', function(e) {
    document.getElementById('luigi').contentWindow.location.reload();
  });


  $('#batch-upload').submit(function (e) {
    var form = $(this);
    var url = form.attr('action');

    var acc_numbers = $("#accession_numbers").val().split(" ").filter(Boolean)

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