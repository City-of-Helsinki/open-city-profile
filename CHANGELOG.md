# Changelog

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
