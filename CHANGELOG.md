# Changelog

## [2.6.2](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.6.1...open-city-profile-v2.6.2) (2025-12-12)


### Bug Fixes

* **auditlog:** Fix IPv6 client address extraction ([2d2dde8](https://github.com/City-of-Helsinki/open-city-profile/commit/2d2dde8cb7a6d9eff5d71b92bdb65ad74840844c))

## [2.6.1](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.6.0...open-city-profile-v2.6.1) (2025-12-11)


### Bug Fixes

* Bump urllib3 ([1f53380](https://github.com/City-of-Helsinki/open-city-profile/commit/1f53380756ad9c84009c18ce25a95e16d1472cb1))

## [2.6.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.5.1...open-city-profile-v2.6.0) (2025-12-04)


### Features

* Add django-resilient-logger model to sanitizer config ([bce97ae](https://github.com/City-of-Helsinki/open-city-profile/commit/bce97aed57ad4db386a8bab67dae650acd354bcf))
* Remove using file as output for audit logs ([7d40f9f](https://github.com/City-of-Helsinki/open-city-profile/commit/7d40f9f5f5758a66376c16146ca948ad32fa6c0b))
* Remove using stdout as output for audit logs ([a41ceb3](https://github.com/City-of-Helsinki/open-city-profile/commit/a41ceb34dfb31e167631a25e73efbec74532981a))
* Use django-resilient-logger for audit logging ([11ec909](https://github.com/City-of-Helsinki/open-city-profile/commit/11ec9094c4ad6292d91b45b1e45ca9559c37326b))


### Bug Fixes

* Strip port from audit log ip address ([eb4b14b](https://github.com/City-of-Helsinki/open-city-profile/commit/eb4b14b0ac666dfbac18796541c0ac3a0652dbad))


### Dependencies

* Add django-resilient-logger ([58233b3](https://github.com/City-of-Helsinki/open-city-profile/commit/58233b3849bae9e977b54a019e269f3aa7d6707d))
* Bump django from 5.2.8 to 5.2.9 ([014d4aa](https://github.com/City-of-Helsinki/open-city-profile/commit/014d4aa396d470f3c3f765bdbc96b019ee6c2523))
* Bump django-resilient-logger ([1ba0eca](https://github.com/City-of-Helsinki/open-city-profile/commit/1ba0eca7c2021616d263c0ea512a15e7eb6a6569))
* Remove ruff from requirements ([3ff7571](https://github.com/City-of-Helsinki/open-city-profile/commit/3ff75719257844c8dc903ea0f9e728156439a897))

## [2.5.1](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.5.0...open-city-profile-v2.5.1) (2025-11-25)


### Reverts

* "fix: include ModelBackend conditionally to..." ([ccf6b27](https://github.com/City-of-Helsinki/open-city-profile/commit/ccf6b27012265cbc9adac0106e9b9e022133d710))

## [2.5.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.4.0...open-city-profile-v2.5.0) (2025-11-24)


### Features

* Change logging format to json ([b2bc936](https://github.com/City-of-Helsinki/open-city-profile/commit/b2bc93634ce91c0fa43a71ab9dd98d28f8ba5961))
* Support AD login in admin ([d9f3f94](https://github.com/City-of-Helsinki/open-city-profile/commit/d9f3f9463c32bdfd20e5667877a7c88f56aa302e))


### Bug Fixes

* Include ModelBackend conditionally to AUTHENTICATION_BACKENDS ([4d69c02](https://github.com/City-of-Helsinki/open-city-profile/commit/4d69c02cfe92ac0a5c80cca8a7b34d24e193d1c0))
* Wrong extend in admin_index.html ([e50fb51](https://github.com/City-of-Helsinki/open-city-profile/commit/e50fb51fe04c8d6f228f9b1451093201c288ec6d))


### Dependencies

* Bump pip-tools ([ad95a88](https://github.com/City-of-Helsinki/open-city-profile/commit/ad95a88ef3b48d959935da78a245e75ce850eda4))
* Update django-helusers to 0.14.4 and add last_api_use migration ([5db1a9e](https://github.com/City-of-Helsinki/open-city-profile/commit/5db1a9e4f79bc4f93e8bba09b77eb99bf2433dd8))

## [2.4.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.3.0...open-city-profile-v2.4.0) (2025-11-10)


### Features

* **sentry:** Update sentry configuration ([0bd087e](https://github.com/City-of-Helsinki/open-city-profile/commit/0bd087ee9c68e66fb626ff8a1c82425d96d89705))


### Dependencies

* Bump django from 5.2.7 to 5.2.8 ([59937ac](https://github.com/City-of-Helsinki/open-city-profile/commit/59937ac77077f67541ebbfdb38ec65f242d01a9f))
* Bump pip from 25.2 to 25.3 ([8f1e8ab](https://github.com/City-of-Helsinki/open-city-profile/commit/8f1e8ab9d8f90cd67c453af0ce09b85092787655))
* Bump sentry-sdk from 2.35.1 to 2.41.0 ([dc1605a](https://github.com/City-of-Helsinki/open-city-profile/commit/dc1605acfef65d5eb04547c1567ce1cd78896096))

## [2.3.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.2.0...open-city-profile-v2.3.0) (2025-10-02)


### Features

* Add pyupgrade to pre-commit ([ef6f3da](https://github.com/City-of-Helsinki/open-city-profile/commit/ef6f3da2327a5126bc2d7cbee3979e378bf21ee0))
* Bump django 5.2 ([e232b63](https://github.com/City-of-Helsinki/open-city-profile/commit/e232b63a5d8eadfe287dd87ab2e7b3863490d37f))


### Dependencies

* Bump development requirements ([ff2c9b4](https://github.com/City-of-Helsinki/open-city-profile/commit/ff2c9b479276d7787bdebf16ccb7aaa57c117649))
* Bump django from 5.2.6 to 5.2.7 ([bc20bef](https://github.com/City-of-Helsinki/open-city-profile/commit/bc20bef7c1a0a432683f51ee838a06cb7ceb2524))
* Bump ruff ([141e330](https://github.com/City-of-Helsinki/open-city-profile/commit/141e33016225ff282b3ab9d439041b97d669bcbf))


### Documentation

* Remove postgis from README ([f6533ab](https://github.com/City-of-Helsinki/open-city-profile/commit/f6533ab3dce9fcb9a74f5a3c4fc4d935ea01fca2))

## [2.2.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.1.1...open-city-profile-v2.2.0) (2025-09-10)


### Features

* Update Python to 3.12 ([8df633b](https://github.com/City-of-Helsinki/open-city-profile/commit/8df633b4a0cb441feaa53938bda6f2bdf4094b4b))


### Dependencies

* Bump django from 4.2.23 to 4.2.24 ([8d18d13](https://github.com/City-of-Helsinki/open-city-profile/commit/8d18d13604005ddd1b2c6f0eba455ba1be7b2707))
* Move uwsgi to main requirements ([ad4fa63](https://github.com/City-of-Helsinki/open-city-profile/commit/ad4fa63aafd08e7e4dcc528de2afc005cfeabb35))
* Update snapshottest to pre-release version for Python 3.12 ([11eb908](https://github.com/City-of-Helsinki/open-city-profile/commit/11eb908be2e656da93e5896db05a7964fc080a8e))


### Documentation

* Update docker compose commands ([f685ee0](https://github.com/City-of-Helsinki/open-city-profile/commit/f685ee080fee8219b563665b6b2875544bfa981d))

## [2.1.1](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.1.0...open-city-profile-v2.1.1) (2025-06-12)


### Dependencies

* Bump django from 4.2.22 to 4.2.23 ([4a0382b](https://github.com/City-of-Helsinki/open-city-profile/commit/4a0382bc1ee482d8ea527e6d7a92ffea3eb0b01f))
* Bump requests from 2.32.3 to 2.32.4 ([a346ea6](https://github.com/City-of-Helsinki/open-city-profile/commit/a346ea62ea0b6ba2526ca73b125ccc71bdf2be1a))

## [2.1.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.0.4...open-city-profile-v2.1.0) (2025-06-11)


### Features

* Increase uWSGI buffer size ([53fc776](https://github.com/City-of-Helsinki/open-city-profile/commit/53fc776ef9cd7b8a9b06e767e02cfe1fe3b4c101))


### Dependencies

* Bump django from 4.2.21 to 4.2.22 ([91a472b](https://github.com/City-of-Helsinki/open-city-profile/commit/91a472be3b0163a57d1d09cee4b3b547d5bbfbc5))

## [2.0.4](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.0.3...open-city-profile-v2.0.4) (2025-06-06)


### Bug Fixes

* Amr claim is a list ([869180f](https://github.com/City-of-Helsinki/open-city-profile/commit/869180f4f733b7fd0808fa6f62138a32c8cffdc8))

## [2.0.3](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.0.2...open-city-profile-v2.0.3) (2025-05-13)


### Dependencies

* Bump python-jose ([ca78091](https://github.com/City-of-Helsinki/open-city-profile/commit/ca7809170cb3d1d7512a4a4563f86892762988e0))

## [2.0.2](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.0.1...open-city-profile-v2.0.2) (2025-05-12)


### Dependencies

* Bump django from 4.2.20 to 4.2.21 ([6fd0269](https://github.com/City-of-Helsinki/open-city-profile/commit/6fd02699573f39195aca1049b8a52a8eb8024fd9))

## [2.0.1](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v2.0.0...open-city-profile-v2.0.1) (2025-05-08)


### Bug Fixes

* Robustify _require_service check ([291e1c7](https://github.com/City-of-Helsinki/open-city-profile/commit/291e1c700104a9d0545d060d1752b06ee2ad859f))

## [2.0.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.21.1...open-city-profile-v2.0.0) (2025-04-10)


### ⚠ BREAKING CHANGES

* **api:** remove tunnistamo support from the api

### Features

* **admin:** Gdpr audience required for an ok ([98df9ca](https://github.com/City-of-Helsinki/open-city-profile/commit/98df9ca105c9af59e8c0b72fca3c9f2e1e2c5524))
* **admin:** Profile service itself is always ok for gdpr ([f8d9077](https://github.com/City-of-Helsinki/open-city-profile/commit/f8d90778af9125829acf2ba23d49e63b9ee09dd8))
* **api:** Remove tunnistamo support from the api ([98e60cf](https://github.com/City-of-Helsinki/open-city-profile/commit/98e60cff21b5e4c58f7f0c0359a0cb6997000a95))
* Remove amr-claim check from loging methods query ([7b46dee](https://github.com/City-of-Helsinki/open-city-profile/commit/7b46dee7e8e3ad3abd0a02d78c2e0e38c54d1c31))
* Remove field Service.idp ([0031fd9](https://github.com/City-of-Helsinki/open-city-profile/commit/0031fd9233dbb988edf447d353df71dc49c18385))
* Remove TunnistamoTokenExchange ([3a3e94c](https://github.com/City-of-Helsinki/open-city-profile/commit/3a3e94c05a97caf80e8c6d1eef2cc751d28a1156))
* Remove unused property Service.is_pure_keycloak ([26890f4](https://github.com/City-of-Helsinki/open-city-profile/commit/26890f483c8af7d5afa52f31392dd7585c6037b0))


### Dependencies

* Bump Django to latest patch version ([c8bceae](https://github.com/City-of-Helsinki/open-city-profile/commit/c8bceaea7a885c138143796012824f9100e1c757))
* Bump ruff ([3f97802](https://github.com/City-of-Helsinki/open-city-profile/commit/3f97802973e5b82435a397fef85dc03cb0678f4f))
* Remove factory_boy from production requirements ([1c2b9e8](https://github.com/City-of-Helsinki/open-city-profile/commit/1c2b9e8414200fdb0c64055c7f76c9317f5462d1))


### Documentation

* Remove tunnistamo from documentation ([e97a06b](https://github.com/City-of-Helsinki/open-city-profile/commit/e97a06bfa83c42ef435c6ab7a889e0bc9f8c0dc0))

## [1.21.1](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.21.0...open-city-profile-v1.21.1) (2025-02-19)


### Dependencies

* Bump cryptography from 43.0.1 to 44.0.1 ([0f23596](https://github.com/City-of-Helsinki/open-city-profile/commit/0f235967993345a698823285409b8faa147d4b98))

## [1.21.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.20.1...open-city-profile-v1.21.0) (2025-01-23)


### Features

* Add LoginMethodNode.credentialId field ([371582b](https://github.com/City-of-Helsinki/open-city-profile/commit/371582b9a3871b7383797744b6de18dd5bcf3273))


### Dependencies

* Bump django from 4.2.17 to 4.2.18 ([c985274](https://github.com/City-of-Helsinki/open-city-profile/commit/c98527493e8328acea084ca96557172b6e2ea101))
* Bump virtualenv from 20.26.5 to 20.26.6 ([9714d35](https://github.com/City-of-Helsinki/open-city-profile/commit/9714d35c87025f8bea9634a2d5e7192aa027b11a))

## [1.20.1](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.20.0...open-city-profile-v1.20.1) (2024-12-12)


### Bug Fixes

* Remove unsafe packages from requirements ([6479ad4](https://github.com/City-of-Helsinki/open-city-profile/commit/6479ad436b280c19500806fcdd0ee1d122c4e75e))

## [1.20.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.19.0...open-city-profile-v1.20.0) (2024-12-12)


### Features

* Add ProfileNode.availableLoginMethods ([2f04126](https://github.com/City-of-Helsinki/open-city-profile/commit/2f041267a31e764023687c67214b634abe343050))


### Dependencies

* Bump django from 4.2.16 to 4.2.17 ([81d25d7](https://github.com/City-of-Helsinki/open-city-profile/commit/81d25d7ff989f206ea340b2ef4e7a3925ca2c337))

## [1.19.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.18.2...open-city-profile-v1.19.0) (2024-11-07)


### Features

* **db-con:** Use database password if present in env ([78bceaa](https://github.com/City-of-Helsinki/open-city-profile/commit/78bceaad8c12522818807df374d0937af860e8f5))

## [1.18.2](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.18.1...open-city-profile-v1.18.2) (2024-10-08)


### Dependencies

* Upgrade dependencies ([b329ce0](https://github.com/City-of-Helsinki/open-city-profile/commit/b329ce0d19ea127d1a4909c4dbb49e6cd41312fa))

## [1.18.1](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.18.0...open-city-profile-v1.18.1) (2024-09-16)


### Bug Fixes

* Allow always allowed data fields regardless of service ([1af82bd](https://github.com/City-of-Helsinki/open-city-profile/commit/1af82bd02d513a1fb01ae439b43f3cec3e504cd9))
* Always allow __typename ([327bbfa](https://github.com/City-of-Helsinki/open-city-profile/commit/327bbfa9325a38aa238bd65925857a5cbb209246))
* Always allow __typename in all AllowedDataFieldsMixin models ([3e0de6b](https://github.com/City-of-Helsinki/open-city-profile/commit/3e0de6b72dd8f5341f8ec1f147041215c1e3c3ad))

## [1.18.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.17.1...open-city-profile-v1.18.0) (2024-07-24)


### Features

* Add enum in login_methods field ([c081f4f](https://github.com/City-of-Helsinki/open-city-profile/commit/c081f4f98ad466b347e81f18ca31c912543248ea))
* Add login_methods field in ProfileNode ([f36ce8f](https://github.com/City-of-Helsinki/open-city-profile/commit/f36ce8f7c6734ca2cec8b2f431a995d163366153))
* **keycloak:** Add federated identity in admin client ([b545d8e](https://github.com/City-of-Helsinki/open-city-profile/commit/b545d8ebb2aaca6b69c92b19293a994fa65728d9))
* **keycloak:** Add get user credentials in admin client ([1054eb7](https://github.com/City-of-Helsinki/open-city-profile/commit/1054eb705499cdd962191620cd34f4f655ba2c86))
* **keycloak:** Add get_user_login_methods function ([1bb620d](https://github.com/City-of-Helsinki/open-city-profile/commit/1bb620d06ac9789654e29b6a53801a59e9399fd7))


### Bug Fixes

* Force amr claim to list ([a69f136](https://github.com/City-of-Helsinki/open-city-profile/commit/a69f1360edc6c495ba4a8a2a42bd6198482e2ed5))
* Ignore unknown login methods ([9016a41](https://github.com/City-of-Helsinki/open-city-profile/commit/9016a41a5a935d1d8229403672623c78d4262d41))

## [1.17.1](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.17.0...open-city-profile-v1.17.1) (2024-07-05)


### Bug Fixes

* Use getattr to access the original_error ([cb22b59](https://github.com/City-of-Helsinki/open-city-profile/commit/cb22b594fd39370f1d180ef650f7ea002b9be524))

## [1.17.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.16.0...open-city-profile-v1.17.0) (2024-06-04)


### Features

* Add feature flag for checking allowed data fields ([3b18fbc](https://github.com/City-of-Helsinki/open-city-profile/commit/3b18fbceab4d941fe59a1fa0fc94009cdc1c0def))
* Add FieldNotAllowedError ([e4e901f](https://github.com/City-of-Helsinki/open-city-profile/commit/e4e901f66d56b19055a8b09fc5e92443d2bedd23))
* Add middleware for checking allowed data fields ([2a10287](https://github.com/City-of-Helsinki/open-city-profile/commit/2a1028764aa514efddf02958e512106f6d7952ee))
* Override DataError's message in GraphQLView ([803c0ea](https://github.com/City-of-Helsinki/open-city-profile/commit/803c0eade7c4cca8ac6c373b79c08b5b1c243ed6))


### Bug Fixes

* Dont check fields in middleware when missing service ([8aeaeac](https://github.com/City-of-Helsinki/open-city-profile/commit/8aeaeacaba1fd5e75c60d0a8562367e590824a71))


### Dependencies

* Upgrade dependencies ([4c01383](https://github.com/City-of-Helsinki/open-city-profile/commit/4c01383fa28dc7ecd5119789b9c701bd8d4c9d02))

## [1.16.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.15.0...open-city-profile-v1.16.0) (2024-05-02)


### Features

* Disable query suggestions ([8556826](https://github.com/City-of-Helsinki/open-city-profile/commit/85568265501c2fa7b2e2302bf8fa2594754a872f))


### Bug Fixes

* Query suggestions are enabled when debugging ([0e2ad73](https://github.com/City-of-Helsinki/open-city-profile/commit/0e2ad73c7076d0c63f25cfec476a236d53bf4cab))

## [1.15.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.14.0...open-city-profile-v1.15.0) (2024-04-24)


### Features

* Prevent GDPR features with insufficient loa ([51069d3](https://github.com/City-of-Helsinki/open-city-profile/commit/51069d33a5829686c5c82c47ae91503374bdddee))
* Add support for CSP headers ([ce8818e](https://github.com/City-of-Helsinki/open-city-profile/commit/ce8818e94697cec5228868034339121202fded9a))


## [1.14.0](https://github.com/City-of-Helsinki/open-city-profile/compare/open-city-profile-v1.13.1...open-city-profile-v1.14.0) (2024-04-19)


### Features

* Add privacy policy and terms of use urls to gql api ([04929c9](https://github.com/City-of-Helsinki/open-city-profile/commit/04929c92e889b0e8e8c280a9ddcb972fe75d5bbc))
* Add privacy policy and terms to django admin ([810316b](https://github.com/City-of-Helsinki/open-city-profile/commit/810316bd9e710da0cad369a0611405deacde93d3))
* Add privacy policy and terms url fields to service ([6b77ac8](https://github.com/City-of-Helsinki/open-city-profile/commit/6b77ac89302fd0f5130de79a8656607bf6ac948b))
* Disable graphql introspection queries ([4f65ed7](https://github.com/City-of-Helsinki/open-city-profile/commit/4f65ed7835956190d0a981da0866b46d7f53d3f2))
* Readiness return version info, sentry get git commit hash ([#479](https://github.com/City-of-Helsinki/open-city-profile/issues/479)) ([fce8d90](https://github.com/City-of-Helsinki/open-city-profile/commit/fce8d901f0c5a37edd8c0060d6dbb11bc4525b72))
* Shorten profile name fields to 150 characters ([0ee92ae](https://github.com/City-of-Helsinki/open-city-profile/commit/0ee92ae2f0ffda1e28941da06f850349b25851fb))
* Validate GraphQL query depth ([72c1f1e](https://github.com/City-of-Helsinki/open-city-profile/commit/72c1f1eb684f56f96ac2913c152b9072a7104265))


### Bug Fixes

* Add ProfileAlreadyExistsForUserError ([d367b8e](https://github.com/City-of-Helsinki/open-city-profile/commit/d367b8e0761f83b9ba1dec9821531024cce25356))


### Documentation

* Update isort url ([616c262](https://github.com/City-of-Helsinki/open-city-profile/commit/616c26226820609ac499b31e11e0ff05a6029bf8))
