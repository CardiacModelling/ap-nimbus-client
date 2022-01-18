var $ = require('./jquery-3.6.0.js'); // Jquery UI
const SimpleMDE = require('./lib/simplemde.js');  // Simple markdown editor

//Create simulation page
$( document ).ready(function(){
    // update ion current enabledness when model changes
    $('#id_model').change(function(){
        $('.current-concentration').each(function(){
            id = $(this).attr("id").replace('id_ion-', '').replace('-current', '');
            models_str = $('#id_ion-' + id + '-models').val();
            models = [];
            if(models_str.length > 2){
                models = models_str.slice(1,-1).split(", ");
            }
            $(this).attr('disabled', $('#id_model').val()=='' || !models.includes($('#id_model').val()));
        });
        // trigger enabledness change
        $('.current-concentration').change();
    });

    // Update ion current units when selected unit changes
    $('#id_ion_units').change(function(){
        $('.ion-units').each(function(){
            $(this).html('&nbsp;' + $('#id_ion_units').val());
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

    // enable other options when a current is input
    $('.current-concentration').change(function(){
        id = $(this).attr("id").replace('id_ion-', '').replace('-current', '');
        disabled =  $(this).val()=='' || $(this).is(':disabled');
        $('#id_ion-' + id + '-hill_coefficient').attr('disabled',  disabled);
        $('#id_ion-' + id + '-hill_coefficient').attr('required',  !disabled);

        $('#id_ion-' + id + '-saturation_level').attr('disabled',  disabled);
        $('#id_ion--' + id + '-saturation_level').attr('required',  !disabled);

        $('#id_ion-' + id + '-spread_of_uncertainty').attr('disabled',  disabled || !$('#enable_spread_of_uncertainty').is(':checked'));
        $('#id_ion-' + id + '-spread_of_uncertainty').attr('required',  !disabled && $('#enable_spread_of_uncertainty').is(':checked'));

    });

    // update enabledness of spead when checkbox is ticked
    $('#enable_spread_of_uncertainty').change(function(){
        if ($('#enable_spread_of_uncertainty').is(':checked')){
            // initialise spread values
            $('.spread_of_uncertainty').each(function(){
                id = $(this).attr("id").replace('-spread_of_uncertainty', '-default_spread_of_uncertainty');
                $(this).val($('#' + id).val());
            });
        }else{
            // clear spread values
            $('.spread_of_uncertainty').each(function(){
                $(this).val('');
            });
        }
        // trigger enabledness change
        $('.current-concentration').change();

    });
    // initialise ion current enabledness
    $('#id_model').change();

    // display relevant compound parems based on seletcted type
    $('.pk_or_concs').change(function(){
        $('.pk_or_concs').each(function(){
            id = $(this).attr('id');
            if($(this).is(':checked')){
                $('#' + id.replace('id_', 'div_')).css('visibility', 'visible');
                $('#' + id.replace('id_', 'div_')).css('display', 'block');
            }else{
                $('#' + id.replace('id_', 'div_')).css('visibility', 'hidden');
                $('#' + id.replace('id_', 'div_')).css('display', 'none');
            }
        });

        // update required and min for Compound Concentration Range
        div_0_vis = $('#div_pk_or_concs_0').css('visibility') == 'visible'
        $('#id_minimum_concentration').attr('required', div_0_vis);
        $('#id_maximum_concentration').attr('required', div_0_vis);
        if(div_0_vis){
            $('#id_minimum_concentration').attr('min', 0);
            $('#id_minimum_concentration').change();
        }else{
            $('#id_minimum_concentration').removeAttr('min');
            $('#id_maximum_concentration').removeAttr('min');
        }
        // update required for Pharmacokinetics
        div_2_vis = $('#div_pk_or_concs_2').css('visibility') == 'visible'
        $('#id_PK_data').attr('required', div_2_vis);

    })
    //initialise compound parems isplay
    $('.pk_or_concs').change();

    //update min value for maximum_concentration
    $('#id_minimum_concentration').change(function(){
        min_min = parseFloat($(this).val());
        $('#id_maximum_concentration').attr('min', min_min >= 0 ? min_min + parseFloat(0.0000000000001): 0);
    });

    // attach action to backbuttons
    if(document.referrer.indexOf(window.location.host) == -1 || history.length <= 1){
        $('#backbutton').attr("href", $('#home_link').attr("href"));
    }else{
       $('#backbutton').attr("href", "javascript:history.back();");
    }

    //Render markdown editor
    id_notes = $('#id_notes');
    if(id_notes.length){
        var simplemde = new SimpleMDE({hideIcons:['guide', 'quote', 'heading'], showIcons: ['strikethrough', 'heading-1', 'heading-2', 'heading-3', 'code', 'table', 'horizontal-rule', 'undo', 'redo'], element: id_notes[0]});
        simplemde.render();
    }
});
