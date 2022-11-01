const $ = require('jquery'); // Jquery UI
//require('jquery-migrate');
global.$ = $;
global.jQuery = $;
const ui = require('jquery-ui'); // Jquery UI
require('jquery-ui/ui/widgets/progressbar');
require('datatables.net')(window, $); // Jquery datatables (npm install datatables.net-dtand)
//flotcharts
require('./lib/flotcharts/jquery.canvaswrapper.js');
require('./lib/flotcharts/jquery.colorhelpers.js');
require('./lib/flotcharts/jquery.event.drag.js');
require('./lib/flotcharts/jquery.flot.js');
require('./lib/flotcharts/jquery.flot.saturated.js');
require('./lib/flotcharts/jquery.flot.browser.js');
require('./lib/flotcharts/jquery.flot.drawSeries.js');
require('./lib/flotcharts/jquery.flot.uiConstants.js');
require('./lib/flotcharts/jquery.flot.selection.js');
require('./lib/flotcharts/jquery.flot.axislabels.js');
require('./lib/flotcharts/jquery.flot.navigate.js');
require('./lib/flotcharts/jquery.flot.touchNavigate.js');
require('./lib/flotcharts/jquery.flot.hover.js');
require('./lib/flotcharts/jquery.flot.touch.js');
require('./lib/flotcharts/jquery.flot.symbol.js');
require('./lib/flotcharts/jquery.flot.legend.js');
require('./lib/flotcharts/jquery.flot.logaxis.js');
require('./lib/flotcharts/jquery.flot.fillbetween.js');


const marked = require("./lib/marked.min.js"); // Markdown render
const SimpleMDE = require('./lib/simplemde.js');  // Simple markdown editor
const notifications = require('./lib/notifications.js');

var graphRendered = false;

// set progressbar timeout, progressbars to update and get base url
var progressBarTimeout = 3000;
var base_url = $(location).attr('href');
var i = base_url.lastIndexOf('/simulations/');
if (i != -1){
    base_url = base_url.substr(0, i);
}else{
    base_url = false;
}


var updateProgressBarTimeout = null;
var graphData = {};
var adp90Options = {};
var qnetOptions = {};
var pkpd_resultsOptions = {};
var tracesOptions = {};
var adp90OptionsNoZoom = {};
var qnetOptionsNoZoom = {};
var pkpd_resultsOptionsNoZoom = {};
var tracesOptionsNoZoom = {};
var confidencePercentages = {};


function zoom(ranges, options, plotFunc){
    // clone options so we can reset later;
    options['xaxis']['autoScale'] = 'none';
    options['xaxis']['min'] = ranges.xaxis.from
    options['xaxis']['max'] = ranges.xaxis.to;
    options['yaxis']['autoScale'] = 'none';
    options['yaxis']['min'] = ranges.yaxis.from;
    options['yaxis']['max'] = ranges.yaxis.to;
    plotFunc(options);
}

function hover(event, pos, item, x_label, x_units, y_label, y_units, hoverDataId){
    if (pos.x && pos.y) {
        x = pos.x.toFixed(3);
        y = pos.y.toFixed(3);
        var hoverData = '<p><label>' + x_label +'</label>' + x + x_units + '</p><p>' + '<label>' + y_label +'</label>' + y + y_units + '</p>';
        $(hoverDataId).html(hoverData);
        if (item) {
            x = item.datapoint[0].toFixed(3);
            y = item.datapoint[1].toFixed(3);
            content = '[' + item.series.label + '] : ' + x_label + x + x_units + ' - ' + y_label + y + y_units;
            $("#tooltip").html(content)
                         .css({top: item.pageY+5, left: item.pageX+5})
                         .fadeIn(200);
        }else{
            $("#tooltip").fadeOut(200);
        }
    }
}

function hoverOut (x_label, x_units, y_label, y_units, hoverDataId) {
    $("#tooltip").hide();
    var hoverData = '<p><label>' + x_label +'</label>' + x_units + '</p><p>' + '<label>' + y_label +'</label>' + y_units + '</p>';
    $(hoverDataId).html(hoverData);
}

function resetQnet(resetZoom){
    if($('#pkpd_results-graph').hasClass('show-graph')){
        if(resetZoom){
            pkpd_resultsOptions = JSON.parse(JSON.stringify(pkpd_resultsOptionsNoZoom));
        }
        plotQnet('#pkpd_results-graph', 'pkpd_results', pkpd_resultsOptions);
    }else if($('#adp90-graph').hasClass('show-graph')){
        if(resetZoom){
            adp90Options = JSON.parse(JSON.stringify(adp90OptionsNoZoom));
        }
        plotQnet('#adp90-graph', 'adp90', adp90Options);
    }else if($('#qnet-graph').hasClass('show-graph')){
        if(resetZoom){
            qnetOptions = JSON.parse(JSON.stringify(qnetOptionsNoZoom))
        }
        plotQnet('#qnet-graph', 'qnet', qnetOptions);
    }
}

function plotQnet(divId, type, options){
    var data = [];
    for(let i=0; i< graphData[type].length; i++){
        if(graphData[type][i]['enabled']){
            data.push(graphData[type][i]);
        }
    }
    $.plot(divId, data, options);
}

function plotTraces(tracesOptions){
    var data = [];
    graphData['traces'].forEach(function (item) {
      if(item.enabled){
          data.push(item);
      }
    });
    $.plot("#traces-graph", data, tracesOptions);
}

function toggleSeries(i){
    graphData['traces'][i].enabled = !graphData['traces'][i].enabled;
    plotTraces(tracesOptions);
}

function renderGraph(pk){
    $.ajax({type: 'GET',
            url: `${base_url}/simulations/${pk}/data`,
            dataType: 'json',
            success: function(data) {
                graphData = data;
                // show messages if there are any
                if(data['messages']){
                    $('#messages').html(data['messages'].join('<br/>'));
                    $("#messages-container").removeClass("hide-messages");
                }
                // set qnet series label and gather confidence intervals
                for(let i=0; i< graphData['adp90'].length; i++){
                    label = graphData['adp90'][i]['label'];
                    const percentageMatch = label.match(/.+Hz (.+%).+/);
                    if(percentageMatch == null){  // this is the main series set the label
                        $('#qnet-series-name').html(label);
                    }else{
                        percentage = percentageMatch[1];
                        if(confidencePercentages[percentage] == undefined){
                            confidencePercentages[percentage] = [i];
                        }else{
                            confidencePercentages[percentage].push(i);
                        }
                    }
                }
                if (!$.isEmptyObject(confidencePercentages)){
                    $('#confidence-percentages').removeClass('hide-messages');
                    $('#confidence-percentages').empty();
                    for (const [pct, series] of Object.entries(confidencePercentages)) {
                        $('#confidence-percentages').append(`<input type="checkbox" id="${pct}" class="confidence-checkbox" checked> ${pct}<br/>`);
                    }
                }
                // assign click action for confidence checkboxes
                $('.confidence-checkbox').click(function(){
                    for (const i of confidencePercentages[$(this).attr('id')]) {
                        if(i < graphData['adp90'].length){
                            graphData['adp90'][i]['enabled'] = !graphData['adp90'][i]['enabled'];
                        }
                        if(i < graphData['qnet'].length){
                            graphData['qnet'][i]['enabled'] = !graphData['qnet'][i]['enabled'];
                        }
                    }
                    resetQnet(false);
                })
                adp90Options = {legend: {show: false},
                                grid: {hoverable: true, clickable: true},
                                xaxis: {axisLabelUseCanvas: true, axisLabelPadding: 10, position: 'bottom', axisLabel: 'Concentration (μM)', mode: "log", showTicks: false, showTickLabels: "all", autoscaleMargin: 0.05, },
                                yaxis: {axisLabelUseCanvas: true, axisLabelPadding: 10, position: 'left', axisLabel: 'Δ APD90 (%)', showTicks: false, showTickLabels: "all", autoscaleMargin: 0.05},
                                selection: {mode: "xy"}
                };
                if('adp90_y_scale' in graphData){  // if we are given a scale, apply it
                    $.extend(adp90Options['yaxis'], adp90Options['yaxis'], graphData['adp90_y_scale'] );
                }

                tracesOptions = {legend: {show: true, container: $('#legendContainerTraces').get(0)},
                                series: {lines: {show: true, lineWidth: 2}, points: {show: false}},
                                grid: {hoverable: true, clickable: true},
                                xaxis: {axisLabelUseCanvas: true, axisLabelPadding: 10, position: 'bottom', axisLabel: 'Time (ms)', showTicks: false, showTickLabels: "all", autoscaleMargin: 0.05},
                                yaxis: {axisLabelUseCanvas: true, axisLabelPadding: 10, position: 'left', axisLabel: 'Membrane Voltage (mV)', showTicks: false, showTickLabels: "all", autoscaleMargin: 0.05},
                                selection: {mode: "xy"}
                };
                plotQnet('#adp90-graph', 'adp90', adp90Options);
                // clone options for zoom reset
                adp90OptionsNoZoom = JSON.parse(JSON.stringify(adp90Options));
                $('#adp90-graph').bind('plotselected', (event, ranges) => zoom(ranges, adp90Options, (opts) => plotQnet('#adp90-graph', 'adp90', adp90Options)));
                $('#adp90-graph').bind('plothover', (event, pos, item) => hover(event, pos, item, 'Conc.: ', ' µM', 'Δ APD90: ', ' %', '#hoverdata'));
                $('#adp90-graph').mouseout((event)=>hoverOut('Conc.: ', ' µM', 'Δ APD90: ', ' %', '#hoverdata'));

                if(graphData['pkpd_results'].length > 0){
                    // show graph, so we can draw
                    $('#pkpd_results').click();

                    pkpd_resultsOptions = {legend: {show: true, container: $('#legendContainerpkpd_results').get(0)},
                                   series: {lines: {show: true, lineWidth: 2}, points: {show: true}},
                                   grid: {hoverable: true, clickable: true},
                                   xaxis: {axisLabelUseCanvas: true, axisLabelPadding: 10, position: 'bottom', axisLabel: 'Timepoint (h)', mode: "log", showTicks: false, showTickLabels: "all", autoscaleMargin: 0.05},
                                   yaxis: {axisLabelUseCanvas: true, axisLabelPadding: 10, position: 'left', axisLabel: 'ADP90 (ms)', showTicks: false, showTickLabels: "all", autoscaleMargin: 0.05},
                                   selection: {mode: "xy"}
                    };
                    if('pkpd_results_y_scale' in graphData){  // if we are given a scale, apply it
                        $.extend(pkpd_resultsOptions['yaxis'], pkpd_resultsOptions['yaxis'], graphData['pkpd_results_y_scale'] );
                    }
                    plotQnet('#pkpd_results-graph', 'pkpd_results', pkpd_resultsOptions);
                    // make sure the legend does not get replotted
                    pkpd_resultsOptions['legend'] = {'show': false};
                    pkpd_resultsOptionsNoZoom = JSON.parse(JSON.stringify(pkpd_resultsOptions)); // clone options for zoom reset

                    $('#pkpd_results-graph').bind('plotselected', (event, ranges) => zoom(ranges, pkpd_resultsOptions, (opts) => plotQnet('#pkpd_results-graph', 'pkpd_results', pkpd_resultsOptions)));
                    $('#pkpd_results-graph').bind('plothover', (event, pos, item) => hover(event, pos, item, 'Timepoint: ', ' h', 'ADP90: ', ' ms', '#hoverdata'));
                    $('#pkpd_results-graph').mouseout((event)=>hoverOut('Timepoint: ', ' h', 'ADP90: ', ' ms', '#hoverdata'));
                }else{
                    // hide qnet button
                    $('#pkpd_results').hide();
                }

                if(graphData['qnet'].length > 0){
                    // show graph, so we can draw
                    $('#qnet').click();

                    qnetOptions = {legend: {show: false},
                                   series: {lines: {show: true, lineWidth: 2}, points: {show: true}},
                                   grid: {hoverable: true, clickable: true},
                                   xaxis: {axisLabelUseCanvas: true, axisLabelPadding: 10, position: 'bottom', axisLabel: 'Concentration (μM)', mode: "log", showTicks: false, showTickLabels: "all", autoscaleMargin: 0.05},
                                   yaxis: {axisLabelUseCanvas: true, axisLabelPadding: 10, position: 'left', axisLabel: 'qNet (C/F)', showTicks: false, showTickLabels: "all", autoscaleMargin: 0.05},
                                   selection: {mode: "xy"}
                    };
                    if('qnet_y_scale' in graphData){  // if we are given a scale, apply it
                        $.extend(qnetOptions['yaxis'], qnetOptions['yaxis'], graphData['qnet_y_scale'] );
                    }
                    qnetOptionsNoZoom = JSON.parse(JSON.stringify(qnetOptions)); // clone options for zoom reset
                    plotQnet('#qnet-graph', 'qnet', qnetOptions);
                    $('#qnet-graph').bind('plotselected', (event, ranges) => zoom(ranges, qnetOptions, (opts) => plotQnet('#qnet-graph', 'qnet', qnetOptions)));
                    $('#qnet-graph').bind('plothover', (event, pos, item) => hover(event, pos, item, 'Conc.: ', ' µM', 'qNet: ', ' C/F', '#hoverdata'));
                    $('#qnet-graph').mouseout((event)=>hoverOut('Conc.: ', ' µM', 'qNet: ', ' C/F', '#hoverdata'));
                }else{
                    // hide qnet button
                    $('#qnet').hide();
                }
                plotTraces(tracesOptions);
                // make sure the legend does not get replotted
                tracesOptions['legend'] = {'show': false};
                tracesOptionsNoZoom = JSON.parse(JSON.stringify(tracesOptions)); // clone options for zoom reset
                $('#traces-graph').bind('plotselected', (event, ranges) => zoom(ranges, tracesOptions, plotTraces));
                $('#traces-graph').bind('plothover', (event, pos, item) => hover(event, pos, item, 'Time: ', ' ms', 'Membrane Voltage: ', ' mV', '#hoverdataTraces'));
                $('#traces-graph').mouseout((event)=>hoverOut('Time: ', ' ms', 'Membrane Voltage: ', ' mV', '#hoverdataTraces'));

                // allow toggling voltage traces in legend
                var labelIndex = 0;
                var checboxesMapObj = {'\u2610': '\u2611', '\u2611': '\u2610'};
                checboxes_regex_str = /\u2610|\u2611/gi;
                $('#legendContainerTraces > .legendLayer > g').each(function(){
                    textElem = $(this).find('text > tspan');
                    textElem.html(`<a href="" onclick="event.preventDefault();" id='${labelIndex}' class='toggleTrace'>\u2611 ${textElem.html()}</a>`);
                    link = $(textElem).find('a');
                    link.click(function(){
                        text = $(this).html().replace(checboxes_regex_str, (matched) => checboxesMapObj[matched]);
                        $(this).html(text);
                        toggleSeries($(this).attr('id'));
                    });
                    labelIndex++;
                });


                // add reset actions
                $('#resetqnet').click(() => resetQnet(true));
                $('#resetTraces').click(function(){ // reset traces graph
                    tracesOptions = JSON.parse(JSON.stringify(tracesOptionsNoZoom));
                    plotTraces(tracesOptions);
                });

                // now select adp90 graph
                $('#adp90').click();
            }
    });
}

function updateProgressbars(skipUpdate=false){
    progressbars = [];
    $('.progressbar').each(function(){
        pk = $(this).attr('id').replace('progressbar-', '');
        progressbars.push(pk);
    });

    if(progressbars.length > 0){
        $.ajax({type: 'GET',
                url: `${base_url}/simulations/status/${skipUpdate}/${progressbars.join('/')}`,
                dataType: 'json',
                success: function(data) {
                    data.forEach(function (simulation) {
                        bar = $(`#progressbar-${simulation['pk']}`);
                        // set label
                        bar.find('.progress-label').text(simulation['progress']); // set label
                        // update progress bar
                        if(simulation['status'] == 'SUCCESS'){
                            bar.progressbar('value', 100);
                            //show export
                            $(`#spreadsheetexport${simulation['pk']}`).css('visibility', 'visible');
                            $(`#spreadsheetexport${simulation['pk']}`).css('display', 'inline');
                            if($('#traces-graph').length > 0 && !graphRendered){
                                renderGraph(simulation['pk']);
                                graphRendered = true;
                            }
                        }else{ // convert into number
                            //hide export
                            $(`#spreadsheetexport${simulation['pk']}`).css('visibility', 'hidden');
                            $(`#spreadsheetexport${simulation['pk']}`).css('display', 'none');
                            graphRendered = false;
                            progress_number = simulation['progress'].replace('% completed', '');
                            if(progress_number == 'Initialising..'){
                                progress_number = 0;
                            }
                            if(!isNaN(progress_number)){ // if the progress is actually a number we can use, use it to set progress on the progressbar
                                bar.progressbar('value', parseInt(progress_number));
                            }
                        }
                        setTimeout(updateProgressbars, progressBarTimeout);
                    })
                }
        });
    }
}

function updateProgressIcons(skipUpdate=false){
    progressIcons = [];
    $('.progressIcon').each(function(){
        pk = $(this).attr('id').replace('progressIcon-', '');
        progressIcons.push(pk);
    });
    if(progressIcons.length > 0){
        $.ajax({type: 'GET',
            url: `${base_url}/simulations/status/${skipUpdate}/${progressIcons.join('/')}`,
            dataType: 'json',
            success: function(data) {
                data.forEach(function (simulation) {
                    icon = $(`#progressIcon-${simulation['pk']}`);
                    if(simulation['status'] == 'SUCCESS'){
                        $(`#progressIcon-${simulation['pk']}`).attr('src', `${base_url}/static/images/finished.gif`);
                        //show export
                        $(`#spreadsheetexport${simulation['pk']}`).css('visibility', 'visible');
                        $(`#spreadsheetexport${simulation['pk']}`).css('display', 'inline');
                    }else{
                        //hide export
                        $(`#spreadsheetexport${simulation['pk']}`).css('visibility', 'hidden');
                        $(`#spreadsheetexport${simulation['pk']}`).css('display', 'none');
                        if(simulation['status'] == 'FAILED'){
                            $(`#progressIcon-${simulation['pk']}`).attr('src', `${base_url}/static/images/failed.gif`);
                        }else{
                            $(`#progressIcon-${simulation['pk']}`).attr('src', `${base_url}/static/images/inprogress.gif`);
                        }
                    }
                });
                updateProgressIconTimeout = setTimeout(updateProgressIcons, progressBarTimeout);
            }
        })
    }
}

$(document).ready(function(){
    //init progress bars
    $('.progressbar').each(function(){
        bar = $(this).progressbar();
    });
    //update progress bar now
    updateProgressbars(true);
    //set update of progress icons
    updateProgressIconTimeout = setTimeout(updateProgressIcons, progressBarTimeout);


    // add dismiss action to notifications
    $("#dismisserrors").click(function() {
        notifications.clear("error");
    });

    $("#dismissnotes").click(function() {
        notifications.clear("info");
    });

    //Set cancel / close button action
    if(document.referrer.indexOf(window.location.host) == -1 || history.length <= 1){
        $('#backbutton').click(function(){window.location.href = $('#home_link').attr("href");});
    }else{
       $('#backbutton').click(function(){history.back();});
    }

    // update ion current enabledness when model changes
    $('#id_model').change(function(){
        $('.current-concentration').each(function(){
            id = $(this).attr("id").replace('id_ion-', '').replace('-current', '');
            models_str = $(`#id_ion-${id}-models`).val();
            models = [];
            if(models_str.length > 2){
                models = models_str.split(",");
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
        $(`#id_ion-${id}-hill_coefficient`).attr('disabled',  disabled);
        $(`#id_ion-${id}-hill_coefficient`).attr('required',  !disabled);

        $(`#id_ion-${id}-saturation_level`).attr('disabled',  disabled);
        $(`#id_ion-${id}-saturation_level`).attr('required',  !disabled);

        $(`#id_ion-${id}-spread_of_uncertainty`).attr('disabled',  disabled || !$('#enable_spread_of_uncertainty').is(':checked'));
        $(`#id_ion-${id}-spread_of_uncertainty`).attr('required',  !disabled && $('#enable_spread_of_uncertainty').is(':checked'));

    });

    // update enabledness of spead when checkbox is ticked
    $('#enable_spread_of_uncertainty').change(function(){
        if ($('#enable_spread_of_uncertainty').is(':checked')){
            // initialise spread values
            $('.spread_of_uncertainty').each(function(){
                id = $(this).attr("id").replace('-spread_of_uncertainty', '-default_spread_of_uncertainty');
                $(this).val($(`#${id}`).val());
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
    // the spread checkbox should be checked if there is any box with a value in it (hence the # of boxes without value != total number of spread input boxes
    $('#enable_spread_of_uncertainty').attr('checked', $('.spread_of_uncertainty:not([value])').length!= $('.spread_of_uncertainty').length );
    $('#id_model').change();

    // display relevant compound parems based on seletcted type
    $('.pk_or_concs').change(function(){
        $('.pk_or_concs').each(function(){
            id = $(this).attr('id');
            if($(this).is(':checked')){
                $(`#${id.replace('id_', 'div_')}`).css('visibility', 'visible');
                $(`#${id.replace('id_', 'div_')}`).css('display', 'block');
            }else{
                $(`#${id.replace('id_', 'div_')}`).css('visibility', 'hidden');
                $(`#${id.replace('id_', 'div_')}`).css('display', 'none');
            }
        });

        // update required and disabled for Compound Concentration Range
        div_0_vis = $('#div_pk_or_concs_0').css('visibility') == 'visible'
        $('#id_minimum_concentration').attr('required', div_0_vis);
        $('#id_maximum_concentration').attr('required', div_0_vis);
        $('#id_intermediate_point_count').attr('required', div_0_vis);
        $('#id_intermediate_point_log_scale').attr('required', div_0_vis);

        $('#id_minimum_concentration').attr('disabled', !div_0_vis);
        $('#id_maximum_concentration').attr('disabled', !div_0_vis);
        $('#id_intermediate_point_count').attr('disabled', !div_0_vis);
        $('#id_intermediate_point_log_scale').attr('disabled', !div_0_vis);

        // ensabled for input of concentration points, to disable checking duplicate when we're not using it and set required on 1st
        div_1_vis = $('#div_pk_or_concs_1').css('visibility') == 'visible'
        $('.compound-concentration').attr('disabled', !div_1_vis);
        $('#id_concentration-0-concentration').attr('required', div_1_vis);

        // update required for Pharmacokinetics
        div_2_vis = $('#div_pk_or_concs_2').css('visibility') == 'visible'
        $('#id_PK_data').attr('required', div_2_vis);
        $('#id_PK_data').attr('disabled', !div_2_vis);

    })
    //initialise compound parems isplay
    $('.pk_or_concs').change();

    //update min value for maximum_concentration
    $('#id_minimum_concentration').change(function(){
        min_min = parseFloat($(this).val());
        $('#id_maximum_concentration').attr('min', min_min >= 0 ? min_min + parseFloat(0.0000000000001): 0);
    });

    //add action for button allowing extra compound concentration pounts
    $('#add-row-concentration-points').click(function(){
        // only if we can still add forms
        total_forms = parseInt($('#id_concentration-TOTAL_FORMS').val());
        max_forms = parseInt($('#id_concentration-MAX_NUM_FORMS').val());
        if (total_forms < max_forms){
            forms_to_add = parseInt($('#id_concentration-MIN_NUM_FORMS').val());
            for (let i = 0; i < forms_to_add && total_forms < max_forms; i++) {// add as many extra points as there are initially
                // find last row
                last_row = $('.compound-concentration-point:last');
                last_index = parseInt(last_row.find('.compound-concentration-point-index').val());

                //clone
                last_row.clone().appendTo('#compound-concentration-points');

                //update index
                new_row = $('.compound-concentration-point:last');
                new_row.find('.compound-concentration-point-index').val(last_index + 1);
                new_row.find('.compound-concentration-point-index-text').text((last_index + 1).toString().padStart(2, '0') + '. ');
                inputBox = new_row.find('.compound-concentration');
                inputBox.val('');
                inputBox.attr('name', `concentration-${last_index.toString()}-concentration`);
                inputBox.attr('id', `id_concentration-${last_index.toString()}-concentration`);

                // update control form
                $('#id_concentration-TOTAL_FORMS').val(last_index + 1);
                total_forms++;
            }
        }
        // if no more forms can be added, disable adding of forms and style as greyed out
        if(total_forms >= max_forms){
            $("#add-row-concentration-points").removeClass("active");
            $("#add-row-concentration-points").addClass("greyed-out");
            $("#add-row-concentration-points").text($("#add-row-concentration-points a").text());
        }
    } );

    // init data table for simulation results
    var datatable = $('#simulations_table').removeAttr('width').DataTable( {
        autoWidth: false,
        scrollY: false,
        scrollX: "850px",
        paging: true,
        fixedColumns: true,
    } );

    // when we paginate to a different set of simulations, stop waiting & ask for status right away
    $('.paginate_button').click(function(){
        clearTimeout(updateProgressIcons);
        updateProgressIcons(true);
    });

    //Render markdown editor
    id_notes = $('#id_notes');
    if(id_notes.length){
        var simplemde = new SimpleMDE({hideIcons:['guide', 'quote', 'heading'], showIcons: ['strikethrough', 'heading-1', 'heading-2', 'heading-3', 'code', 'table', 'horizontal-rule', 'undo', 'redo'], element: id_notes[0]});
        simplemde.render();
    }

    //render markdown view
    $(".markdowrenderview").each(function(){
          source = $(this).find(".markdownsource").val();
          $(this).html(marked(source));
      });

    //buttons for switching between graphs
    $('#pkpd_results').click(function(){
        $('#pkpd_results-graph').removeClass('hide-graph');
        $('#adp90-graph').removeClass('show-graph');
        $('#qnet-graph').removeClass('show-graph');
        $('#pkpd_results-graph').addClass('show-graph');
        $('#adp90-graph').addClass('hide-graph');
        $('#qnet-graph').addClass('hide-graph');
        $('#pkpd_results').attr('disabled', true);
        $('#adp90').attr('disabled', false);
        $('#qnet').attr('disabled', false);
        $('#legendContainerpkpd_results').show();
        $('#legendContainerQnet').hide();
        resetQnet(false);  // reset the graph so that selected intervals are drawn
    });

    $('#adp90').click(function(){
        $('#pkpd_results-graph').removeClass('show-graph');
        $('#adp90-graph').removeClass('hide-graph');
        $('#qnet-graph').removeClass('show-graph');
        $('#pkpd_results-graph').addClass('hide-graph');
        $('#adp90-graph').addClass('show-graph');
        $('#qnet-graph').addClass('hide-graph');
        $('#pkpd_results').attr('disabled', false);
        $('#adp90').attr('disabled', true);
        $('#qnet').attr('disabled', false);
        $('#legendContainerpkpd_results').hide();
        $('#legendContainerQnet').show();
        resetQnet(false);  // reset the graph so that selected intervals are drawn
    });

    $('#qnet').click(function(){
        $('#pkpd_results-graph').removeClass('show-graph');
        $('#adp90-graph').removeClass('show-graph');
        $('#qnet-graph').removeClass('hide-graph');
        $('#pkpd_results-graph').addClass('hide-graph');
        $('#adp90-graph').addClass('hide-graph');
        $('#qnet-graph').addClass('show-graph');
        $('#pkpd_results').attr('disabled', false);
        $('#adp90').attr('disabled', false);
        $('#qnet').attr('disabled', true);
        $('#legendContainerpkpd_results').hide();
        $('#legendContainerQnet').show();
        resetQnet(false);  // reset the graph so that selected intervals are drawn
    });

});
