from django.core.management.base import BaseCommand
from accounts.models import User
from files.models import CellmlModel
from simulations.models import Simulation, SimulationIonCurrentParam, CompoundConcentrationPoint

class Command(BaseCommand):

    def add_arguments(self, parser):
        parser.add_argument('title', type=str, help='Title to identify sumulations. Please note: use quotes if the title contains spaces or quotes.')
        parser.add_argument('author_email', type=str, help='Email address of the author for which the simulation is run')
        parser.add_argument('model_name', type=str, help='The name of the model to use. If the name is not unique, please also specify year and/or version. Please note: use quotes if the model name contains spaces or quotes.')

#    Compound concentration points
#    simulation ion current param    : Ion current, Current, Hill coefficient, Saturation level:, Spread of uncertainty:

        # Optional argument
        parser.add_argument('--model_year', type=str, help='The year for a specified model, to tell models with the same name apart e.g. 2020')
        parser.add_argument('--model_version', type=str, help='The model version, where a model has multiple versions e.g. CiPA-v1.0')
        parser.add_argument('--notes', type=str, help='Textual notes for the simulation. Please note: use quotes if the notes contain spaces or quotes.', default='')
        parser.add_argument('--pacing_frequency', type=float, help='(in Hz) Frequency of pacing (between 0.05 and 5).', default=1.0)
        parser.add_argument('--maximum_pacing_time', type=float, help='(in mins) Maximum pacing time (between 0 and 120).', default=5.0)
        parser.add_argument('--ion_current_type', type=str, help='Ion current type: (pIC50 or IC50)', default='pIC50')
        parser.add_argument('--ion_units', type=str, help='Ion current units. (-log(M), M, µM, or nM)', default='-log(M)')
#pk_or_cons
        parser.add_argument('--concentration_type', '--pk_or_concs', type=str, help='Concentration specification type. (compound_concentration_range, compound_concentration_points, or pharmacokinetics)', default='compound_concentration_range', dest='pk_or_concs')
        parser.add_argument('--minimum_concentration', type=float, help='(in µM) at least 0.', default=0.0)
        parser.add_argument('--maximum_concentration', type=float, help='(in µM) > minimum_concentration.', default=100.0)
        parser.add_argument('--intermediate_point_count', type=int, help='Count of plasma concentrations between the minimum and maximum (between 0 and 10).', default=4)
        parser.add_argument('--intermediate_point_log_scale', type=bool, help='Use log scale for intermediate points.', default=True)
        parser.add_argument('--PK_data_file', '--PK_data', type=str, help='File format: tab-seperated values (TSV). Encoding: UTF-8\nColumn 1 : Time (hours)\nColumns 2-31 : Concentrations (µM).', default='', dest='PK_data')
        parser.add_argument('--concentration_point', type=float, help='Specify compound concentrations points one by one. For example for points 0.1 and 0.2 specify as follows: --concentration_point 0.1 --concentration_point 0.2', action='append', default=[])
        conc_metavar = ('<current>', 'concentration', 'hill coefficient', 'saturation level', 'spread of uncertainty')
        parser.add_argument('--current_inhibitory_concentration', nargs=5, default=[], action='append', metavar=conc_metavar, help='Inhibitory concentrations, one by one e.g. --current_inhibitory_concentration INa 0.5 1 0 0')


    def handle(self, *args, **kwargs):
        title = kwargs['title']

        kwargs['author'] = User.objects.get(email=kwargs['author_email'])
        model = CellmlModel.objects.filter(name=kwargs['model_name'])
        if kwargs.get('model_year', None):
            model = model.filter(year=kwargs['mode_year'])
        if kwargs.get('model_version', None):
            model = model.filter(year=kwargs['mode_version'])
        if not model.count() == 1:
           raise ValueError('Ambiguous specification of model')
        kwargs['model'] = model.first()

        kwargs['ion_current_type'] = kwargs['ion_current_type'].upper()
        if kwargs['ion_current_type'] not in ('PIC50', 'IC50'):
            raise ValueError('Incorrect specification of ion_current_type')
        ion_units = kwargs['ion_units']
        if kwargs['ion_current_type'] == 'IC50' and kwargs['ion_units'] == '-log(M)':
            kwargs['ion_units'] = 'µM'
        if kwargs['pk_or_concs'] not in ('compound_concentration_range', 'compound_concentration_points', 'pharmacokinetics'):
            raise ValueError('Invalid concentration_type')
        if kwargs['maximum_concentration'] <= kwargs['minimum_concentration']:
            raise ValueError('maximum_concentration needs to be larger than minimum_concentration')
        if kwargs['intermediate_point_count'] < 0 or kwargs['intermediate_point_count'] > 10:
            raise ValueError('invalid intermediate_point_count')

        simulation = Simulation(title=kwargs['title'], notes=kwargs['notes'], author=kwargs['author'], model=kwargs['model'], pacing_frequency=kwargs['pacing_frequency'], maximum_pacing_time=kwargs['maximum_pacing_time'], ion_current_type=kwargs['ion_current_type'], ion_units=kwargs['ion_units'], pk_or_concs=kwargs['pk_or_concs'], minimum_concentration=kwargs['minimum_concentration'], maximum_concentration=kwargs['maximum_concentration'], intermediate_point_count=kwargs['intermediate_point_count'], intermediate_point_log_scale=kwargs['intermediate_point_log_scale'], PK_data=kwargs['PK_data'])
        simulation.save()
        assert False, str(type(simulation))
#concentration_point
#current_inhibitory_concentration

# from simulations.models import Simulation, SimulationIonCurrentParam, CompoundConcentrationPoint
        assert False, str(CellmlModel.objects.filter(year=2004).filter(name='Shannon et al.'))
#        assert False, str(kwargs.get('title', None))
#        self._create_tags()
