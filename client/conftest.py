import pytest
from accounts.models import User
from core.visibility import Visibility
from django.contrib.auth.models import AnonymousUser
from files.models import CellmlModel


@pytest.fixture
def admin_user():
    return User.objects.create_superuser(
        email='admin@example.com',
        full_name='Admin User',
        institution='UCL',
        password='password',
    )


@pytest.fixture
def anonymous_user():
    return AnonymousUser()


@pytest.fixture
def user():
    return User.objects.create_user(
        email='test@example.com',
        full_name='Test User',
        institution='UCL',
        password='password',
    )


@pytest.fixture
def other_user():
    return User.objects.create_user(
        email='other@example.com',
        full_name='Other User',
        institution='UCL',
        password='password',
    )


@pytest.fixture
def logged_in_user(client, user):
    client.login(username=user.email, password='password')
    return user


@pytest.fixture
def logged_in_admin(client, admin_user):
    client.login(username=admin_user.email, password='password')
    return admin_user


@pytest.fixture
def o_hara_model(user):
    return CellmlModel.objects.create(
        author=user,
        visibility=Visibility.PUBLIC,
        name="O'Hara-Rudy-CiPA",
        description='human ventricular cell model (endocardial)',
        version='v1.0',
        year=2017,
        cellml_link='https://models.cellml.org/e/4e8/',
        paper_link='https://www.ncbi.nlm.nih.gov/pubmed/28878692',
        cellml_file='OHara-Rudy-CiPA-v1.0.cellml',
    )
