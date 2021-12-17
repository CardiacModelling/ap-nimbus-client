from model_bakery.recipe import Recipe, seq

from .visibility import Visibility


cellml_model = Recipe('CellmlModel', name=seq('my model'), description=seq('my descr'),
                      year=2021, visibility=Visibility.PUBLIC)
