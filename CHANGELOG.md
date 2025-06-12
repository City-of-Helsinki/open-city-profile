# Changelog

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
