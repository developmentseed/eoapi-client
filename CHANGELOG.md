# Changelog

## 0.1.0 (2026-09-28)


### ⚠ BREAKING CHANGES

* **stac:** list_collections and download_asset are removed; use Stac(url, ...).collections() / .download_asset(...).
* **raster:** Raster.tilejson/tile_url_template/collection_tilejson removed; use raster.search(id).tilejson() / .tile_url_template() or raster.collection(id).tilejson().
* the eoapi_client.collections and eoapi_client.assets modules were merged into eoapi_client.stac. Top-level imports are unchanged.
* **http:** TransactionError now subclasses EoApiError and takes `status_code` as a keyword argument instead of `(status_code, message)`.

### Features

* add EoApi entry point with one shared httpx client ([db536f4](https://github.com/developmentseed/eoapi-client/commit/db536f44623dbd7b59ae417047a932d70c6553d6))
* add raster client for titiler-pgstac mosaics ([7073a99](https://github.com/developmentseed/eoapi-client/commit/7073a9954b9fb86cc8ce98d55d9f07ab718207ff))
* add STAC collection listing and asset download helpers ([4f8d996](https://github.com/developmentseed/eoapi-client/commit/4f8d99656c9574977563de158e926090a8f8c372))
* add STAC Transactions client ([436ad88](https://github.com/developmentseed/eoapi-client/commit/436ad884cfb805636404cd513415fc9bb394b79e))
* add vector client via OWSLib, spike-tested against tipg ([f25a5e1](https://github.com/developmentseed/eoapi-client/commit/f25a5e108f74279279cc343fdacf5131072331c0))
* **auth:** add TokenAuth with client-credentials and mock-OIDC token fetching ([066e027](https://github.com/developmentseed/eoapi-client/commit/066e027ed2fdb9ab10db9cddb84348b4864dcf22))
* bootstrap eoapi-client python package ([2a63f33](https://github.com/developmentseed/eoapi-client/commit/2a63f3397ca1810d50a1ba8da877681128842b55))
* **raster:** add search/collection/item targets with info, point, statistics, bbox and preview ([aafa830](https://github.com/developmentseed/eoapi-client/commit/aafa8305c9426cd331a0ca5011a9f0dd218b01f8))
* **raster:** drop search shortcuts in favour of targets ([0071acc](https://github.com/developmentseed/eoapi-client/commit/0071acce68442da35392fd6bf6764e0378de1c3b))
* **stac:** drop module-level list_collections and download_asset ([8988584](https://github.com/developmentseed/eoapi-client/commit/8988584275eeffa399b4b8b362d1f9df19c2f1e5))
* **transactions:** add item/collection update, patch, delete and bulk inserts ([e10ff73](https://github.com/developmentseed/eoapi-client/commit/e10ff7386ce246cfd75a824019a955b4d0697fe1))
* **vector:** add VectorTiles for tipg MVT tilejson, style and tiles ([c871f3f](https://github.com/developmentseed/eoapi-client/commit/c871f3f635c46c7e218198883bc6177c0cbce0eb))


### Bug Fixes

* **http:** raise EoApiError for all failures, including transport errors ([f824958](https://github.com/developmentseed/eoapi-client/commit/f824958fce8054ab220e261233270fc0c17b02fe))
* **stac:** follow pagination in collections and add iter_items ([4c0915c](https://github.com/developmentseed/eoapi-client/commit/4c0915c2e84ee8c9e23c01a469a2e3f5d475c02b))


### Documentation

* add AGENTS.md ([6369ccb](https://github.com/developmentseed/eoapi-client/commit/6369ccb0f897015f2f777bd63159ad01544be909))
* add README ([be6bbef](https://github.com/developmentseed/eoapi-client/commit/be6bbef0f47e8722a8fad80a59e52bf9366d9959))
* document auth ([ed6a7d9](https://github.com/developmentseed/eoapi-client/commit/ed6a7d96685f2f4b835d18dd82d5b659f365af88))
* document error hierarchy ([2db9594](https://github.com/developmentseed/eoapi-client/commit/2db959421f845466ab381967b86eade18d22842f))
* document integration tests ([80308c9](https://github.com/developmentseed/eoapi-client/commit/80308c9ebba8e4d246bddac0c4a640e8d401c045))
* document raster targets ([2ab9b05](https://github.com/developmentseed/eoapi-client/commit/2ab9b057033342d4443acad227191ad99dd4111d))
* document STAC pagination ([5beff11](https://github.com/developmentseed/eoapi-client/commit/5beff11655b4ba03bd4708c94fbc8c3adccd1efe))
* document Transactions methods ([dd9a5bc](https://github.com/developmentseed/eoapi-client/commit/dd9a5bc51477d348e9bf55311f0550cbabef2718))
* document vector tiles ([53453ab](https://github.com/developmentseed/eoapi-client/commit/53453abe0ccc8e6ce36cf29eb015f843c219c0f0))
* record new module layout in AGENTS.md ([f15c765](https://github.com/developmentseed/eoapi-client/commit/f15c765fd0f619fcfc3e6b089618cbd0c9f45328))
* refresh service signatures ([64dd8e9](https://github.com/developmentseed/eoapi-client/commit/64dd8e9ca4e6f785e3a0477c1d204d01d67a683d))


### Build System

* **deps-dev:** update uv-build requirement ([#2](https://github.com/developmentseed/eoapi-client/issues/2)) ([ad847f7](https://github.com/developmentseed/eoapi-client/commit/ad847f720648e2c1f11ab4484ddebd22757b4372))
* manage project with uv ([0c57aba](https://github.com/developmentseed/eoapi-client/commit/0c57abab4ca85ce1f6014c7ebd369d436c3304e4))
* type-check src with mypy --strict in pre-commit ([33e05b4](https://github.com/developmentseed/eoapi-client/commit/33e05b4cee623aa2cbdb007fa5d87644c6f25075))


### CI/CD

* add pre-commit checks ([41dbbe9](https://github.com/developmentseed/eoapi-client/commit/41dbbe91a4b21738faffd16c9e67af1854be9e16))
* add release-please ([0fffaaa](https://github.com/developmentseed/eoapi-client/commit/0fffaaa42c11ef9dabb55a9ebcc2fe79020e21b7))
* configure dependabot ([a6f84a9](https://github.com/developmentseed/eoapi-client/commit/a6f84a9ac61fd9db123963b0dc7c196f396b6ae1))
* run integration tests against eoapi-k8s on k3s ([9711d2f](https://github.com/developmentseed/eoapi-client/commit/9711d2fecdf66b435c2e9aecdb2da9a71ae90a39))
