from model_bakery.recipe import Recipe, seq


user = Recipe('accounts.User', institution='UCL', full_name=seq('test user '))
