import os
import uuid
from shutil import copyfile

from accounts.models import User
from django.conf import settings
from django.core.files.uploadedfile import TemporaryUploadedFile
from django.core.management.base import BaseCommand
from files.models import CellmlModel, IonCurrent
from simulations.models import CompoundConcentrationPoint, Simulation, SimulationIonCurrentParam
from simulations.views import start_simulation


class Command(BaseCommand):
    def add_arguments(self, parser):
        parser.add_argument('title', type=str, help='Title to identify sumulations. Please note: '
                                                    'use quotes if the title contains spaces or quotes.')
        parser.add_argument('author_email', type=str,
                            help='Email address of the author for which the simulation is run')
        parser.add_argument('model_name', type=str,
                            help='The name of the model to use. If the name is not unique, please also specify year '
                                 'and/or version. Please note: use quotes if the model name contains spaces or quotes.')

        # Optional argument
        parser.add_argument('--model_year', type=str, help='The year for a specified model, '
                                                           'to tell models with the same name apart e.g. 2020')
        parser.add_argument('--model_version', type=str, help='The model version, '
                                                              'where a model has multiple versions e.g. CiPA-v1.0')
        parser.add_argument('--notes', type=str, help='Textual notes for the simulation. Please note: use quotes if '
                                                      'the notes contain spaces or quotes.', default='')
        parser.add_argument('--pacing_frequency', type=float, default=1.0,
                            help='(in Hz) Frequency of pacing (between 0.05 and 5).')
        parser.add_argument('--maximum_pacing_time', type=float, default=5.0,
                            help='(in mins) Maximum pacing time (between 0 and 120).')
        parser.add_argument('--ion_current_type', type=str, help='Ion current type: (pIC50 or IC50)', default='pIC50')
        parser.add_argument('--ion_units', type=str, help='Ion current units. (-log(M), M, µM, or nM)', default='')
        parser.add_argument('--concentration_type', '--pk_or_concs', type=str, default='compound_concentration_range',
                            help='Concentration specification type. (compound_concentration_range, '
                                 'compound_concentration_points, or pharmacokinetics)', dest='pk_or_concs')
        parser.add_argument('--minimum_concentration', type=float, help='(in µM) at least 0.', default=0.0)
        parser.add_argument('--maximum_concentration', type=float, help='(in µM) > minimum_concentration.',
                            default=100.0)
        parser.add_argument('--intermediate_point_count', type=int, default=4,
                            help='Count of plasma concentrations between the minimum and maximum (between 0 and 10).')
        parser.add_argument('--intermediate_point_log_scale', type=bool, help='Use log scale for intermediate points.',
                            default=True)
        parser.add_argument('--PK_data_file', '--PK_data', type=str, default='', dest='PK_data',
                            help='File format: tab-seperated values (TSV). Encoding: UTF-8\nColumn 1 : Time (hours) '
                                 'Columns 2-31 : Concentrations (µM).')
        parser.add_argument('--concentration_point', type=float, action='append', default=[],
                            help='Specify compound concentrations points one by one. For example for points 0.1 and 0.2'
                                 ' specify as follows: --concentration_point 0.1 --concentration_point 0.2')
        conc_meta = ('<current>', 'concentration', 'hill coefficient', 'saturation level', 'spread of uncertainty')
        parser.add_argument('--current_inhibitory_concentration', nargs=5, default=[], action='append',
                            help='Inhibitory concentrations, one by one e.g. --current_inhibitory_concentration INa '
                                 '0.5 1 0 0', metavar=conc_meta)

    def handle(self, *args, **kwargs):
        kwargs['author'] = User.objects.get(email=kwargs['author_email'])
        title = kwargs['title']
        i = 2
        while Simulation.objects.filter(title=title, author=kwargs['author']).exists():
            title = f"{kwargs['title']} ({i})"
            i += 1

        model = CellmlModel.objects.filter(name=kwargs['model_name'])
        if kwargs.get('model_year', None):
            model = model.filter(year=int(kwargs['model_year']))
        if kwargs.get('model_version', None):
            model = model.filter(version=kwargs['model_version'])
        if not model.count() == 1:
            raise ValueError('Ambiguous specification of model')
        model = model.first()

        ion_current_type = kwargs['ion_current_type'].upper().replace('PIC50', 'pIC50')
        if ion_current_type not in ('pIC50', 'IC50'):
            raise ValueError('Incorrect specification of ion_current_type')

        ion_units = kwargs['ion_units']
        if ion_units == '' and ion_current_type == 'IC50':
            ion_units = 'µM'
        elif ion_units == '' and ion_current_type == 'pIC50':
            ion_units = '-log(M)'

        if ion_current_type == 'pIC50' and ion_units != '-log(M)':
            raise ValueError("pIC50's are only available with ion_units -log(M)")

        if kwargs['pk_or_concs'] not in ('compound_concentration_range', 'compound_concentration_points',
                                         'pharmacokinetics'):
            raise ValueError('Invalid concentration_type')
        if kwargs['maximum_concentration'] <= kwargs['minimum_concentration']:
            raise ValueError('maximum_concentration needs to be larger than minimum_concentration')
        if kwargs['intermediate_point_count'] < 0 or kwargs['intermediate_point_count'] > 10:
            raise ValueError('Invalid intermediate_point_count')

        PK_data = ''
        if kwargs['pk_or_concs'] == 'pharmacokinetics':
            uploaded_file = os.path.join(settings.MEDIA_ROOT, f'{uuid.uuid4()}.tsv')
            copyfile(kwargs['PK_data'], uploaded_file)

            PK_data = TemporaryUploadedFile(os.path.basename(kwargs['PK_data']), 'text/plain',
                                            os.path.getsize(uploaded_file), 'utf-8')
            PK_data.file = open(uploaded_file, 'rb')

        simulation = Simulation(title=title,
                                notes=kwargs['notes'],
                                author=kwargs['author'],
                                model=model,
                                pacing_frequency=kwargs['pacing_frequency'],
                                maximum_pacing_time=kwargs['maximum_pacing_time'],
                                ion_current_type=ion_current_type,
                                ion_units=ion_units, pk_or_concs=kwargs['pk_or_concs'],
                                minimum_concentration=kwargs['minimum_concentration'],
                                maximum_concentration=kwargs['maximum_concentration'],
                                intermediate_point_count=kwargs['intermediate_point_count'],
                                intermediate_point_log_scale=kwargs['intermediate_point_log_scale'],
                                PK_data=PK_data)

        concentration_points = []
        ion_currents = []

        for concentration_point in kwargs['concentration_point']:
            concentration_points.append(CompoundConcentrationPoint(simulation=simulation,
                                                                   concentration=concentration_point))

        for ic in kwargs['current_inhibitory_concentration']:
            ion_current = (IonCurrent.objects.filter(name=ic[0]) |
                           IonCurrent.objects.filter(alternative_name=ic[0])).first()

            ion_currents.append(SimulationIonCurrentParam(simulation=simulation,
                                                          ion_current=ion_current,
                                                          current=float(ic[1]),
                                                          hill_coefficient=float(ic[2]),
                                                          saturation_level=float(ic[3]),
                                                          spread_of_uncertainty=float(ic[4])))

        # save all bits
        simulation.save()
        for cp in concentration_points:
            cp.save()
        for icur in ion_currents:
            icur.save()

        start_simulation(simulation)  # start simulation
