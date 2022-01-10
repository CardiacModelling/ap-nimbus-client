var $ = require('./jquery-3.6.0.min.js');

//Create simulation page
$( document ).ready(function(){
    // Update ion current units when selected unit changes
    $('#id_ion_units').change(function(){
        $('.ion-units').each(function(){
            $(this).html($('#id_ion_units').val());
        });
    });

    $('#id_ion_current_type').change(function(){
        //remove all options
        $("#id_ion_units option").remove();
        $('.current-concentration').removeAttr('min');

        //add appropriate options back in
        if($('#id_ion_current_type').val() == 'pIC50'){
            $("#id_ion_units").append($('<option>', {value: '-log(M)', text: '-log(M)'}));
            $('#id_ion_units').val('-log(M)');
            $('#id_ion_units').change();
        }else { //$('#id_ion_current_type').val() == 'IC50'
            $("#id_ion_units").append([$('<option>', {value: 'M', text: 'M'}),
                                       $('<option>', {value: 'µM', text: 'µM'}),
                                       $('<option>', {value: 'nM', text: 'nM'})]);
            $('#id_ion_units').val('µM');
            $('#id_ion_units').change();
            // store ion current type restriction in form
            $('.current-concentration').attr('min', 0);
        }
        // store ion current type in formset fo individual currents
        $('.ion_current_type').val($('#id_ion_current_type').val())
    });


    // trigger initial processing of current type
    $('#id_ion_current_type').change();
});
