var $ = require('./jquery-3.6.0.min.js');

//Create simulation page

// Update ion current units when selected unit changes
$( document ).ready(function(){
    $('#id_ion_units').change(function(){
        $('.ion-units').each(function(){
            $(this).html($('#id_ion_units').val());
        });
    });

    $('#id_ion_current_type').change(function(){
        $("#id_ion_units option").remove();

        if($('#id_ion_current_type').val() == 'pIC50'){
            $("#id_ion_units").append($('<option>', {value: '-log(M)', text: '-log(M)'}));
            $('#id_ion_units').val('-log(M)');
            $('#id_ion_units').change();
        }
        if($('#id_ion_current_type').val() == 'IC50'){
            $("#id_ion_units").append([$('<option>', {value: 'M', text: 'M'}),
                                       $('<option>', {value: 'µM', text: 'µM'}),
                                       $('<option>', {value: 'nM', text: 'nM'})]);
            $('#id_ion_units').val('µM');
            $('#id_ion_units').change();
        }
    });
    $('#id_ion_current_type').change();
});
