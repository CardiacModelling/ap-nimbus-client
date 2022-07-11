![workflow](https://github.com/CardiacModelling/ap-nimbus-client/actions/workflows/pytest.yml/badge.svg) [![codecov](https://codecov.io/gh/CardiacModelling/ap-nimbus-client/branch/master/graph/badge.svg)](https://codecov.io/gh/CardiacModelling/ap-nimbus-client)

# client-direct
## Web front-end for Action Potential prediction (ApPredict) in containers - AP-Nimbus
[`ApPredict`](https://github.com/Chaste/ApPredict) performs simulations of
drug-induced changes to the cardiac action potential to support the
[CiPA initiative](http://cipaproject.org/). This activity is a continuation of the [ap_predict_online](https://bitbucket.org/gef_work/ap_predict_online/src/) work -- the aim being to containerise the AP-Portal. This repository contains the web-front ent called client-direct

Detailed documentation of the various components can be found at https://ap-nimbus.readthedocs.io/

## Repository content :
The repository contains the Django UI (web-front-end) published as docker image, see: https://hub.docker.com/r/cardiacmodelling/ap-nimbus-client-direct

The repository contains the following folders:
- *client* - the django project that constitutes the web front-end
- *docker* - Docker file and relevant scripts to create a docker image
- *backup* - Backup scripts to backup tha database, uploaded files and logs of the web front-end running in a docker container.
- *requirements* - list of required python components for the web front-end.
