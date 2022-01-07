var $ = require('./jquery-3.6.0.min.js');

//Create simulation page

// Update ion current units when selected unit changes
$( document ).ready(function(){
    $('#id_ion_units').change(function(){
        $('.ion-units').each(function(){
            $(this).html($('#id_ion_units').val());
        });
    });
});
