# Generated by Django 4.0.7 on 2022-11-02 15:46

from django.db import migrations


PREDEF_MODELS = [
    {'name': r'Shannon et al.',
     'model_name_tag': 'shannon_wang_puglisi_weber_bers_2004_model_updated',
     'version': '',
     'ap_predict_model_call': r'1'},

    {'name': 'TenTusscher et al.',
     'model_name_tag': 'tentusscher_model_2006_epi',
     'version': '(epi)',
     'ap_predict_model_call': '2'},

    {'name': 'Mahajan et al.',
     'model_name_tag': 'MahajanShiferaw2008_units',
     'version': '',
     'ap_predict_model_call': '3'},

    {'name': 'Hund, Rudy',
     'model_name_tag': 'HundRudy2004_units',
     'version': '',
     'ap_predict_model_call': '4'},

    {'name': 'Grandi et al.',
     'model_name_tag': 'grandi_pasqualini_bers_2010_epi',
     'version': '(epi)',
     'ap_predict_model_call': '5'},

    {'name': r"O'Hara-Rudy",
     'model_name_tag': 'ohara_rudy_2011_endo',
     'version': '(endo)',
     'ap_predict_model_call': '6'},

    {'name': 'Paci et al.',
     'model_name_tag': 'paci_hyttinen_aaltosetala_severi_ventricularVersion',
     'version': '(ventricular)',
     'ap_predict_model_call': '7'},

    {'name': r"O'Hara-Rudy CiPA",
     'model_name_tag': 'ohara_rudy_cipa_v1_2017',
     'version': '(endo)',
     'ap_predict_model_call': '8'},
]


def correct_predefined_models(apps, schema_editor):
    CellmlModel = apps.get_model('files', 'CellmlModel')
    for predef_model in PREDEF_MODELS:
        model = CellmlModel.objects.get(ap_predict_model_call=predef_model['ap_predict_model_call'])
        model.name = predef_model['name']
        model.model_name_tag = predef_model['model_name_tag']
        model.version = predef_model['version']


class Migration(migrations.Migration):

    dependencies = [
        ('files', '0004_cellmlmodel_model_name_tag'),
    ]

    operations = [
        migrations.RunPython(correct_predefined_models),
    ]
