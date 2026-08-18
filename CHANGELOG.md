# Changelog

Notable changes to `ap-nimbus-client-direct` in each version.

## [2.1.0] - 2026-08-17

### Added

- **LDAP authentication**, enabled with `AP_PREDICT_LDAP=1`, off by default.
  - Directory `mail` and `cn` map to the account's email address and full name,
    so LDAP users sign in with their email like other users.
  - Configurable search filter, for directories that identify users by something
    other than `mail`.
  - Optional group rules to restrict logins or grant privileges.
  - Registration links are hidden across the templates when LDAP is enabled.
  - `django-auth-ldap` added to the requirements.
- A docker compose example which reads from the `docker/env` template and
  publishes `4240:80`, matching the example in the Dockerfile.
- A `.dockerignore` that keeps secrets, virtualenvs and version control out of
  the build context.

### Changed

- Blank and whitespace-only environment variables are now treated as unset and
  fall back to their defaults. This affects `ALLOWED_HOSTS`, `subfolder` and
  every LDAP setting.
- Multi-architecture builds: the image is now published for `linux/amd64` and
  `linux/arm64`, via the shared `docker/github-builder` reusable workflow.
- Version label advanced to `2.1.0`, and the app-manager image in docker compose
  pinned to `2.1.0`.

### Fixed

- The `docker/env` template quoted its empty values, which env-files read as
  literal quote characters rather than as empty strings.
- The `AP_PREDICT_ENDPOINT` default in `docker/env` pointed at
  `ap-nimbus-network` — the Docker network rather than a container — so a
  deployment using the template unchanged could not reach app-manager. It now
  points at `name-app-manager`.
- Spelling and capitalisation corrected throughout the `docker/env` comments.

## [2.0.0] - 2024-09-10

### Added

- A GitHub Action to build and publish the image.

### Changed

- Requirements updated to support Python 3.8 through 3.12.
- `numpy` constrained to `<2.0` for cellmlmanip compatibility.
- flake8 configuration updated for 7.1.0, isort version fixed, and pytest-httpx
  upgraded for Python 3.12 support.
- Test runs now list the installed dependency versions.
- Updated the license.

### Fixed

- The Docker image name and the Docker build context.

## [1.0.1] - 2023-12-19

### Changed

- Security bumps:
  - Django 4.1.10 → 4.1.13
  - uWSGI 2.0.21 → 2.0.22

## [1.0.0] - 2023-07-14

### Added

- The privacy notice, the contact link and the contact text are now set from
  environment variables, so a deployment can supply its own without a rebuild.
- `AP_PREDICT_STATUS_TIMEOUT` exposed in the env file, so the wait for the API
  can be tuned without rebuilding.
- `DJANGO_SUPERUSER_FULLNAME`, and superuser creation that only creates the
  account when one does not already exist.
- Nginx logging, and in-container access to `uwsgi.log`.

### Changed

- Graph controls reworked: log scale is applied only when selected, the buttons
  stay disabled until the data has loaded, and the qNet and ΔAPD90 series are
  shown on first render.
- The PKPD timepoint axis is no longer logarithmic.
- Reworded the new-user emails and the registration messages.
- Security bumps: Django 4.1.3 → 4.1.10.

### Fixed

- Regenerated the minified JavaScript, which had gone stale and at one point
  corrupt.

## [0.0.10] - 2022-12-12

### Added

- ApPredict version information is captured with each simulation, shown in the
  results page and included in the spreadsheet export.
- Status icons on the simulation list, and a restart button offered only for
  simulations that failed.
- Bulk user upload, and admin-side password changing, in the admin interface.
- Model name tags, used to match a model against the available lookup tables and
  to keep tags unique between predefined and user-supplied models.

### Changed

- Rebased the image on Debian, and the portal no longer runs as root.
- Reworked the results page layout; simulations are listed newest first, with
  year/month/day dates in place of the short US format.
- Spreadsheet export is offered only once a simulation has finished.

### Fixed

- The graph legend was re-added periodically on the results page, and
  confidence-interval entries were not cleared when a simulation was re-run.
- Zero concentrations are rejected, and unintended rounding in the input form
  removed.

## [0.0.9] - 2022-09-06

### Added

- The `pythonpath` variable.

### Changed

- Django 4.0.6 → 4.0.7.

## [0.0.8] - 2022-07-11

### Changed

- Dockerfile and README updates.

## [0.0.7] - 2022-07-06

Earliest tagged release of the Django client. The prototype that preceded it is
tagged `last_client_direct_prototype` (2022-04-06) in the AP-Nimbus umbrella
repository.

[2.1.0]: https://github.com/CardiacModelling/ap-nimbus-client/compare/v2.0.0...v2.1.0
[2.0.0]: https://github.com/CardiacModelling/ap-nimbus-client/compare/v1.0.1...v2.0.0
[1.0.1]: https://github.com/CardiacModelling/ap-nimbus-client/compare/v1.0.0...v1.0.1
[1.0.0]: https://github.com/CardiacModelling/ap-nimbus-client/compare/0.0.10...v1.0.0
[0.0.10]: https://github.com/CardiacModelling/ap-nimbus-client/compare/0.0.9...0.0.10
[0.0.9]: https://github.com/CardiacModelling/ap-nimbus-client/compare/0.0.8...0.0.9
[0.0.8]: https://github.com/CardiacModelling/ap-nimbus-client/compare/0.0.7...0.0.8
[0.0.7]: https://github.com/CardiacModelling/ap-nimbus-client/releases/tag/0.0.7
