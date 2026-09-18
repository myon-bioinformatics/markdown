# Changelog

## [1.13.3](https://github.com/axios/axios/compare/v1.13.2...v1.13.3) (2026-01-20)

### Bug Fixes

- **http2:** Use port 443 for HTTPS connections by default. ([#7256](https://github.com/axios/axios/issues/7256)) ([d7e6065](https://github.com/axios/axios/commit/d7e60653460480ffacecf85383012ca1baa6263e))
- **interceptor:** handle the error in the same interceptor ([#6269](https://github.com/axios/axios/issues/6269)) ([5945e40](https://github.com/axios/axios/commit/5945e40bb171d4ac4fc195df276cf952244f0f89))
- main field in package.json should correspond to cjs artifacts ([#5756](https://github.com/axios/axios/issues/5756)) ([7373fbf](https://github.com/axios/axios/commit/7373fbff24cd92ce650d99ff6f7fe08c2e2a0a04))
- **package.json:** add 'bun' package.json 'exports' condition. Load the Node.js build in Bun instead of the browser build ([#5754](https://github.com/axios/axios/issues/5754)) ([b89217e](https://github.com/axios/axios/commit/b89217e3e91de17a3d55e2b8f39ceb0e9d8aeda8))
- silentJSONParsing=false should throw on invalid JSON ([#7253](https://github.com/axios/axios/issues/7253)) ([#7257](https://github.com/axios/axios/issues/7257)) ([7d19335](https://github.com/axios/axios/commit/7d19335e43d6754a1a9a66e424f7f7da259895bf))
- turn AxiosError into a native error ([#5394](https://github.com/axios/axios/issues/5394)) ([#5558](https://github.com/axios/axios/issues/5558)) ([1c6a86d](https://github.com/axios/axios/commit/1c6a86dd2c0623ee1af043a8491dbc96d40e883b))
- **types:** add handlers to AxiosInterceptorManager interface ([#5551](https://github.com/axios/axios/issues/5551)) ([8d1271b](https://github.com/axios/axios/commit/8d1271b49fc226ed7defd07cd577bd69a55bb13a))
- **types:** restore AxiosError.cause type from unknown to Error ([#7327](https://github.com/axios/axios/issues/7327)) ([d8233d9](https://github.com/axios/axios/commit/d8233d9e8e9a64bfba9bbe01d475ba417510b82b))
- unclear error message is thrown when specifying an empty proxy authorization ([#6314](https://github.com/axios/axios/issues/6314)) ([6ef867e](https://github.com/axios/axios/commit/6ef867e684adf7fb2343e3b29a79078a3c76dc29))

### Features

- add `undefined` as a value in AxiosRequestConfig ([#5560](https://github.com/axios/axios/issues/5560)) ([095033c](https://github.com/axios/axios/commit/095033c626895ecdcda2288050b63dcf948db3bd))
- add automatic minor and patch upgrades to dependabot ([#6053](https://github.com/axios/axios/issues/6053)) ([65a7584](https://github.com/axios/axios/commit/65a7584eda6164980ddb8cf5372f0afa2a04c1ed))
- add Node.js coverage script using c8 (closes [#7289](https://github.com/axios/axios/issues/7289)) ([#7294](https://github.com/axios/axios/issues/7294)) ([ec9d94e](https://github.com/axios/axios/commit/ec9d94e9f88da13e9219acadf65061fb38ce080a))
- added copilot instructions ([3f83143](https://github.com/axios/axios/commit/3f83143bfe617eec17f9d7dcf8bafafeeae74c26))
- compatibility with frozen prototypes ([#6265](https://github.com/axios/axios/issues/6265)) ([860e033](https://github.com/axios/axios/commit/860e03396a536e9b926dacb6570732489c9d7012))
- enhance pipeFileToResponse with error handling ([#7169](https://github.com/axios/axios/issues/7169)) ([88d7884](https://github.com/axios/axios/commit/88d78842541610692a04282233933d078a8a2552))
- **types:** Intellisense for string literals in a widened union ([#6134](https://github.com/axios/axios/issues/6134)) ([f73474d](https://github.com/axios/axios/commit/f73474d02c5aa957b2daeecee65508557fd3c6e5)), closes [/github.com/microsoft/TypeScript/issues/33471#issuecomment-1376364329](https://github.com//github.com/microsoft/TypeScript/issues/33471/issues/issuecomment-1376364329)

### Reverts

- Revert "fix: silentJSONParsing=false should throw on invalid JSON (#7253) (#7…" (#7298) ([a4230f5](https://github.com/axios/axios/commit/a4230f5581b3f58b6ff531b6dbac377a4fd7942a)), closes [#7253](https://github.com/axios/axios/issues/7253) [#7](https://github.com/axios/axios/issues/7) [#7298](https://github.com/axios/axios/issues/7298)
- **deps:** bump peter-evans/create-pull-request from 7 to 8 in the github-actions group ([#7334](https://github.com/axios/axios/issues/7334)) ([2d6ad5e](https://github.com/axios/axios/commit/2d6ad5e48bd29b0b2b5e7e95fb473df98301543a))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/175160345?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Ashvin Tiwari](https://github.com/ashvin2005 "+1752/-4 (#7218 #7218 )")
- <img src="https://avatars.githubusercontent.com/u/71729144?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Nikunj Mochi](https://github.com/mochinikunj "+940/-12 (#7294 #7294 )")
- <img src="https://avatars.githubusercontent.com/u/128113546?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Anchal Singh](https://github.com/imanchalsingh "+544/-102 (#7169 #7185 )")
- <img src="https://avatars.githubusercontent.com/u/4814473?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [jasonsaayman](https://github.com/jasonsaayman "+317/-73 (#7334 #7298 )")
- <img src="https://avatars.githubusercontent.com/u/377911?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Julian Dax](https://github.com/brodo "+99/-120 (#5558 )")
- <img src="https://avatars.githubusercontent.com/u/184285082?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Akash Dhar Dubey](https://github.com/AKASHDHARDUBEY "+167/-0 (#7287 #7288 )")
- <img src="https://avatars.githubusercontent.com/u/145687605?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Madhumita](https://github.com/madhumitaaa "+20/-68 (#7198 )")
- <img src="https://avatars.githubusercontent.com/u/24915252?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Tackoil](https://github.com/Tackoil "+80/-2 (#6269 )")
- <img src="https://avatars.githubusercontent.com/u/145078271?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Justin Dhillon](https://github.com/justindhillon "+41/-41 (#6324 #6315 )")
- <img src="https://avatars.githubusercontent.com/u/184138832?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Rudransh](https://github.com/Rudrxxx "+71/-2 (#7257 )")
- <img src="https://avatars.githubusercontent.com/u/146366930?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [WuMingDao](https://github.com/WuMingDao "+36/-36 (#7215 )")
- <img src="https://avatars.githubusercontent.com/u/46827243?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [codenomnom](https://github.com/codenomnom "+70/-0 (#7201 #7201 )")
- <img src="https://avatars.githubusercontent.com/u/189698992?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Nandan Acharya](https://github.com/Nandann018-ux "+60/-10 (#7272 )")
- <img src="https://avatars.githubusercontent.com/u/7225168?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Eric Dubé](https://github.com/KernelDeimos "+22/-40 (#7042 )")
- <img src="https://avatars.githubusercontent.com/u/915045?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Tibor Pilz](https://github.com/tiborpilz "+40/-4 (#5551 )")
- <img src="https://avatars.githubusercontent.com/u/23138717?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Gabriel Quaresma](https://github.com/joaoGabriel55 "+31/-4 (#6314 )")
- <img src="https://avatars.githubusercontent.com/u/21505?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Turadg Aleahmad](https://github.com/turadg "+23/-6 (#6265 )")
- <img src="https://avatars.githubusercontent.com/u/4273631?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [JohnTitor](https://github.com/kiritosan "+14/-14 (#6155 )")
- <img src="https://avatars.githubusercontent.com/u/39668736?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [rohit miryala](https://github.com/rohitmiryala "+22/-0 (#7250 )")
- <img src="https://avatars.githubusercontent.com/u/30316250?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Wilson Mun](https://github.com/wmundev "+20/-0 (#6053 )")
- <img src="https://avatars.githubusercontent.com/u/184506226?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [techcodie](https://github.com/techcodie "+7/-7 (#7236 )")
- <img src="https://avatars.githubusercontent.com/u/187598667?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Ved Vadnere](https://github.com/Archis009 "+5/-6 (#7283 )")
- <img src="https://avatars.githubusercontent.com/u/115612815?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [svihpinc](https://github.com/svihpinc "+5/-3 (#6134 )")
- <img src="https://avatars.githubusercontent.com/u/123884782?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [SANDESH LENDVE](https://github.com/mrsandy1965 "+3/-3 (#7246 )")
- <img src="https://avatars.githubusercontent.com/u/12529395?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Lubos](https://github.com/mrlubos "+5/-1 (#7312 )")
- <img src="https://avatars.githubusercontent.com/u/709451?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Jarred Sumner](https://github.com/Jarred-Sumner "+5/-1 (#5754 )")
- <img src="https://avatars.githubusercontent.com/u/17907922?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Adam Hines](https://github.com/thebanjomatic "+2/-1 (#5756 )")
- <img src="https://avatars.githubusercontent.com/u/177472603?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Subhan Kumar Rai](https://github.com/Subhan030 "+2/-1 (#7256 )")
- <img src="https://avatars.githubusercontent.com/u/6473925?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Joseph Frazier](https://github.com/josephfrazier "+1/-1 (#7311 )")
- <img src="https://avatars.githubusercontent.com/u/184906930?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [KT0803](https://github.com/KT0803 "+0/-2 (#7229 )")
- <img src="https://avatars.githubusercontent.com/u/6703955?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Albie](https://github.com/AlbertoSadoc "+1/-1 (#5560 )")
- <img src="https://avatars.githubusercontent.com/u/9452325?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Jake Hayes](https://github.com/thejayhaykid "+1/-0 (#5999 )")

## [1.13.2](https://github.com/axios/axios/compare/v1.13.1...v1.13.2) (2025-11-04)

### Bug Fixes

- **http:** fix 'socket hang up' bug for keep-alive requests when using timeouts; ([#7206](https://github.com/axios/axios/issues/7206)) ([8d37233](https://github.com/axios/axios/commit/8d372335f5c50ecd01e8615f2468a9eb19703117))
- **http:** use default export for http2 module to support stubs; ([#7196](https://github.com/axios/axios/issues/7196)) ([0588880](https://github.com/axios/axios/commit/0588880ac7ddba7594ef179930493884b7e90bf5))

### Performance Improvements

- **http:** fix early loop exit; ([#7202](https://github.com/axios/axios/issues/7202)) ([12c314b](https://github.com/axios/axios/commit/12c314b603e7852a157e93e47edb626a471ba6c5))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+28/-9 (#7206 #7202 )")
- <img src="https://avatars.githubusercontent.com/u/1174718?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Kasper Isager Dalsgarð](https://github.com/kasperisager "+9/-9 (#7196 )")

## [1.13.1](https://github.com/axios/axios/compare/v1.13.0...v1.13.1) (2025-10-28)

### Bug Fixes

- **http:** fixed a regression that caused the data stream to be interrupted for responses with non-OK HTTP statuses; ([#7193](https://github.com/axios/axios/issues/7193)) ([bcd5581](https://github.com/axios/axios/commit/bcd5581d208cd372055afdcb2fd10b68ca40613c))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/128113546?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Anchal Singh](https://github.com/imanchalsingh "+220/-111 (#7173 )")
- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+18/-1 (#7193 )")

# [1.13.0](https://github.com/axios/axios/compare/v1.12.2...v1.13.0) (2025-10-27)

### Bug Fixes

- **fetch:** prevent TypeError when config.env is undefined ([#7155](https://github.com/axios/axios/issues/7155)) ([015faec](https://github.com/axios/axios/commit/015faeca9f26db76f9562760f04bb9f8229f4db1))
- resolve issue [#7131](https://github.com/axios/axios/issues/7131) (added spacing in mergeConfig.js) ([#7133](https://github.com/axios/axios/issues/7133)) ([9b9ec98](https://github.com/axios/axios/commit/9b9ec98548d93e9f2204deea10a5f1528bf3ce62))

### Features

- **http:** add HTTP2 support; ([#7150](https://github.com/axios/axios/issues/7150)) ([d676df7](https://github.com/axios/axios/commit/d676df772244726533ca320f42e967f5af056bac))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+794/-180 (#7186 #7150 #7039 )")
- <img src="https://avatars.githubusercontent.com/u/189505037?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Noritaka Kobayashi](https://github.com/noritaka1166 "+24/-509 (#7032 )")
- <img src="https://avatars.githubusercontent.com/u/195581631?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Aviraj2929](https://github.com/Aviraj2929 "+211/-93 (#7136 #7135 #7134 #7112 )")
- <img src="https://avatars.githubusercontent.com/u/181717941?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [prasoon patel](https://github.com/Prasoon52 "+167/-6 (#7099 )")
- <img src="https://avatars.githubusercontent.com/u/141911040?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Samyak Dandge](https://github.com/Samy-in "+134/-0 (#7171 )")
- <img src="https://avatars.githubusercontent.com/u/128113546?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Anchal Singh](https://github.com/imanchalsingh "+53/-56 (#7170 )")
- <img src="https://avatars.githubusercontent.com/u/146073621?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Rahul Kumar](https://github.com/jaiyankargupta "+28/-28 (#7073 )")
- <img src="https://avatars.githubusercontent.com/u/148716794?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Amit Verma](https://github.com/Amitverma0509 "+24/-13 (#7129 )")
- <img src="https://avatars.githubusercontent.com/u/141427581?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Abhishek3880](https://github.com/abhishekmaniy "+23/-4 (#7119 #7117 #7116 #7115 )")
- <img src="https://avatars.githubusercontent.com/u/91522146?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dhvani Maktuporia](https://github.com/Dhvani365 "+14/-5 (#7175 )")
- <img src="https://avatars.githubusercontent.com/u/41838423?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Usama Ayoub](https://github.com/sam3690 "+4/-4 (#7133 )")
- <img src="https://avatars.githubusercontent.com/u/79366821?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [ikuy1203](https://github.com/ikuy1203 "+3/-3 (#7166 )")
- <img src="https://avatars.githubusercontent.com/u/74639234?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Nikhil Simon Toppo](https://github.com/Kirito-Excalibur "+1/-1 (#7172 )")
- <img src="https://avatars.githubusercontent.com/u/200562195?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Jane Wangari](https://github.com/Wangarijane "+1/-1 (#7155 )")
- <img src="https://avatars.githubusercontent.com/u/78318848?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Supakorn Ieamgomol](https://github.com/Supakornn "+1/-1 (#7065 )")
- <img src="https://avatars.githubusercontent.com/u/134518?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Kian-Meng Ang](https://github.com/kianmeng "+1/-1 (#7046 )")
- <img src="https://avatars.githubusercontent.com/u/13148112?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [UTSUMI Keiji](https://github.com/k-utsumi "+1/-1 (#7037 )")

## [1.12.2](https://github.com/axios/axios/compare/v1.12.1...v1.12.2) (2025-09-14)

### Bug Fixes

- **fetch:** use current global fetch instead of cached one when env fetch is not specified to keep MSW support; ([#7030](https://github.com/axios/axios/issues/7030)) ([cf78825](https://github.com/axios/axios/commit/cf78825e1229b60d1629ad0bbc8a752ff43c3f53))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+247/-16 (#7030 #7022 #7024 )")
- <img src="https://avatars.githubusercontent.com/u/189505037?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Noritaka Kobayashi](https://github.com/noritaka1166 "+2/-6 (#7028 #7029 )")

## [1.12.1](https://github.com/axios/axios/compare/v1.12.0...v1.12.1) (2025-09-12)

### Bug Fixes

- **types:** fixed env config types; ([#7020](https://github.com/axios/axios/issues/7020)) ([b5f26b7](https://github.com/axios/axios/commit/b5f26b75bdd9afa95016fb67d0cab15fc74cbf05))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+10/-4 (#7020 )")

# [1.12.0](https://github.com/axios/axios/compare/v1.11.0...v1.12.0) (2025-09-11)

### Bug Fixes

- adding build artifacts ([9ec86de](https://github.com/axios/axios/commit/9ec86de257bfa33856571036279169f385ed92bd))
- dont add dist on release ([a2edc36](https://github.com/axios/axios/commit/a2edc3606a4f775d868a67bb3461ff18ce7ecd11))
- **fetch-adapter:** set correct Content-Type for Node FormData ([#6998](https://github.com/axios/axios/issues/6998)) ([a9f47af](https://github.com/axios/axios/commit/a9f47afbf3224d2ca987dbd8188789c7ea853c5d))
- **node:** enforce maxContentLength for data: URLs ([#7011](https://github.com/axios/axios/issues/7011)) ([945435f](https://github.com/axios/axios/commit/945435fc51467303768202250debb8d4ae892593))
- package exports ([#5627](https://github.com/axios/axios/issues/5627)) ([aa78ac2](https://github.com/axios/axios/commit/aa78ac23fc9036163308c0f6bd2bb885e7af3f36))
- **params:** removing '[' and ']' from URL encode exclude characters ([#3316](https://github.com/axios/axios/issues/3316)) ([#5715](https://github.com/axios/axios/issues/5715)) ([6d84189](https://github.com/axios/axios/commit/6d84189349c43b1dcdd977b522610660cc4c7042))
- release pr run ([fd7f404](https://github.com/axios/axios/commit/fd7f404488b2c4f238c2fbe635b58026a634bfd2))
- **types:** change the type guard on isCancel ([#5595](https://github.com/axios/axios/issues/5595)) ([0dbb7fd](https://github.com/axios/axios/commit/0dbb7fd4f61dc568498cd13a681fa7f907d6ec7e))

### Features

- **adapter:** surface low‑level network error details; attach original error via cause ([#6982](https://github.com/axios/axios/issues/6982)) ([78b290c](https://github.com/axios/axios/commit/78b290c57c978ed2ab420b90d97350231c9e5d74))
- **fetch:** add fetch, Request, Response env config variables for the adapter; ([#7003](https://github.com/axios/axios/issues/7003)) ([c959ff2](https://github.com/axios/axios/commit/c959ff29013a3bc90cde3ac7ea2d9a3f9c08974b))
- support reviver on JSON.parse ([#5926](https://github.com/axios/axios/issues/5926)) ([2a97634](https://github.com/axios/axios/commit/2a9763426e43d996fd60d01afe63fa6e1f5b4fca)), closes [#5924](https://github.com/axios/axios/issues/5924)
- **types:** extend AxiosResponse interface to include custom headers type ([#6782](https://github.com/axios/axios/issues/6782)) ([7960d34](https://github.com/axios/axios/commit/7960d34eded2de66ffd30b4687f8da0e46c4903e))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/22686401?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Willian Agostini](https://github.com/WillianAgostini "+132/-16760 (#7002 #5926 #6782 )")
- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+4263/-293 (#7006 #7003 )")
- <img src="https://avatars.githubusercontent.com/u/53833811?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [khani](https://github.com/mkhani01 "+111/-15 (#6982 )")
- <img src="https://avatars.githubusercontent.com/u/7712804?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Ameer Assadi](https://github.com/AmeerAssadi "+123/-0 (#7011 )")
- <img src="https://avatars.githubusercontent.com/u/70265727?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Emiedonmokumo Dick-Boro](https://github.com/emiedonmokumo "+55/-35 (#6998 )")
- <img src="https://avatars.githubusercontent.com/u/47859767?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Zeroday BYTE](https://github.com/opsysdebug "+8/-8 (#6980 )")
- <img src="https://avatars.githubusercontent.com/u/4814473?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Jason Saayman](https://github.com/jasonsaayman "+7/-7 (#6985 #6985 )")
- <img src="https://avatars.githubusercontent.com/u/13010755?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [최예찬](https://github.com/HealGaren "+5/-7 (#5715 )")
- <img src="https://avatars.githubusercontent.com/u/7002604?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Gligor Kotushevski](https://github.com/gligorkot "+3/-1 (#5627 )")
- <img src="https://avatars.githubusercontent.com/u/15893?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Aleksandar Dimitrov](https://github.com/adimit "+2/-1 (#5595 )")

# [1.11.0](https://github.com/axios/axios/compare/v1.10.0...v1.11.0) (2025-07-22)

### Bug Fixes

- form-data npm pakcage ([#6970](https://github.com/axios/axios/issues/6970)) ([e72c193](https://github.com/axios/axios/commit/e72c193722530db538b19e5ddaaa4544d226b253))
- prevent RangeError when using large Buffers ([#6961](https://github.com/axios/axios/issues/6961)) ([a2214ca](https://github.com/axios/axios/commit/a2214ca1bc60540baf2c80573cea3a0ff91ba9d1))
- **types:** resolve type discrepancies between ESM and CJS TypeScript declaration files ([#6956](https://github.com/axios/axios/issues/6956)) ([8517aa1](https://github.com/axios/axios/commit/8517aa16f8d082fc1d5309c642220fa736159110))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/12534341?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [izzy goldman](https://github.com/izzygld "+186/-93 (#6970 )")
- <img src="https://avatars.githubusercontent.com/u/142807367?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Manish Sahani](https://github.com/manishsahanidev "+70/-0 (#6961 )")
- <img src="https://avatars.githubusercontent.com/u/189505037?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Noritaka Kobayashi](https://github.com/noritaka1166 "+12/-10 (#6938 #6939 )")
- <img src="https://avatars.githubusercontent.com/u/392612?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [James Nail](https://github.com/jrnail23 "+13/-2 (#6956 )")
- <img src="https://avatars.githubusercontent.com/u/163745239?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Tejaswi1305](https://github.com/Tejaswi1305 "+1/-1 (#6894 )")

# [1.10.0](https://github.com/axios/axios/compare/v1.9.0...v1.10.0) (2025-06-14)

### Bug Fixes

- **adapter:** pass fetchOptions to fetch function ([#6883](https://github.com/axios/axios/issues/6883)) ([0f50af8](https://github.com/axios/axios/commit/0f50af8e076b7fb403844789bd5e812dedcaf4ed))
- **form-data:** convert boolean values to strings in FormData serialization ([#6917](https://github.com/axios/axios/issues/6917)) ([5064b10](https://github.com/axios/axios/commit/5064b108de336ff34862650709761b8a96d26be0))
- **package:** add module entry point for React Native; ([#6933](https://github.com/axios/axios/issues/6933)) ([3d343b8](https://github.com/axios/axios/commit/3d343b86dc4fd0eea0987059c5af04327c7ae304))

### Features

- **types:** improved fetchOptions interface ([#6867](https://github.com/axios/axios/issues/6867)) ([63f1fce](https://github.com/axios/axios/commit/63f1fce233009f5db1abf2586c145825ac98c3d7))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+30/-19 (#6933 #6920 #6893 #6892 )")
- <img src="https://avatars.githubusercontent.com/u/189505037?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Noritaka Kobayashi](https://github.com/noritaka1166 "+2/-6 (#6922 #6923 )")
- <img src="https://avatars.githubusercontent.com/u/48370490?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dimitrios Lazanas](https://github.com/dimitry-lzs "+4/-0 (#6917 )")
- <img src="https://avatars.githubusercontent.com/u/71047946?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Adrian Knapp](https://github.com/AdrianKnapp "+2/-2 (#6867 )")
- <img src="https://avatars.githubusercontent.com/u/16129206?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Howie Zhao](https://github.com/howiezhao "+3/-1 (#6872 )")
- <img src="https://avatars.githubusercontent.com/u/6788611?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Uhyeon Park](https://github.com/warpdev "+1/-1 (#6883 )")
- <img src="https://avatars.githubusercontent.com/u/20028934?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Sampo Silvennoinen](https://github.com/stscoundrel "+1/-1 (#6913 )")

# [1.9.0](https://github.com/axios/axios/compare/v1.8.4...v1.9.0) (2025-04-24)

### Bug Fixes

- **core:** fix the Axios constructor implementation to treat the config argument as optional; ([#6881](https://github.com/axios/axios/issues/6881)) ([6c5d4cd](https://github.com/axios/axios/commit/6c5d4cd69286868059c5e52d45085cb9a894a983))
- **fetch:** fixed ERR_NETWORK mapping for Safari browsers; ([#6767](https://github.com/axios/axios/issues/6767)) ([dfe8411](https://github.com/axios/axios/commit/dfe8411c9a082c3d068bdd1f8d6e73054f387f45))
- **headers:** allow iterable objects to be a data source for the set method; ([#6873](https://github.com/axios/axios/issues/6873)) ([1b1f9cc](https://github.com/axios/axios/commit/1b1f9ccdc15f1ea745160ec9a5223de9db4673bc))
- **headers:** fix `getSetCookie` by using 'get' method for caseless access; ([#6874](https://github.com/axios/axios/issues/6874)) ([d4f7df4](https://github.com/axios/axios/commit/d4f7df4b304af8b373488fdf8e830793ff843eb9))
- **headers:** fixed support for setting multiple header values from an iterated source; ([#6885](https://github.com/axios/axios/issues/6885)) ([f7a3b5e](https://github.com/axios/axios/commit/f7a3b5e0f7e5e127b97defa92a132fbf1b55cf15))
- **http:** send minimal end multipart boundary ([#6661](https://github.com/axios/axios/issues/6661)) ([987d2e2](https://github.com/axios/axios/commit/987d2e2dd3b362757550f36eab875e60640b6ddc))
- **types:** fix autocomplete for adapter config ([#6855](https://github.com/axios/axios/issues/6855)) ([e61a893](https://github.com/axios/axios/commit/e61a8934d8f94dd429a2f309b48c67307c700df0))

### Features

- **AxiosHeaders:** add getSetCookie method to retrieve set-cookie headers values ([#5707](https://github.com/axios/axios/issues/5707)) ([80ea756](https://github.com/axios/axios/commit/80ea756e72bcf53110fa792f5d7ab76e8b11c996))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+200/-34 (#6890 #6889 #6888 #6885 #6881 #6767 #6874 #6873 )")
- <img src="https://avatars.githubusercontent.com/u/4814473?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Jay](https://github.com/jasonsaayman "+26/-1 ()")
- <img src="https://avatars.githubusercontent.com/u/22686401?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Willian Agostini](https://github.com/WillianAgostini "+21/-0 (#5707 )")
- <img src="https://avatars.githubusercontent.com/u/2500247?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [George Cheng](https://github.com/Gerhut "+3/-3 (#5096 )")
- <img src="https://avatars.githubusercontent.com/u/30260221?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [FatahChan](https://github.com/FatahChan "+2/-2 (#6855 )")
- <img src="https://avatars.githubusercontent.com/u/49002?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Ionuț G. Stan](https://github.com/igstan "+1/-1 (#6661 )")

## [1.8.4](https://github.com/axios/axios/compare/v1.8.3...v1.8.4) (2025-03-19)

### Bug Fixes

- **buildFullPath:** handle `allowAbsoluteUrls: false` without `baseURL` ([#6833](https://github.com/axios/axios/issues/6833)) ([f10c2e0](https://github.com/axios/axios/commit/f10c2e0de7fde0051f848609a29c2906d0caa1d9))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/8029107?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Marc Hassan](https://github.com/mhassan1 "+5/-1 (#6833 )")

## [1.8.3](https://github.com/axios/axios/compare/v1.8.2...v1.8.3) (2025-03-10)

### Bug Fixes

- add missing type for allowAbsoluteUrls ([#6818](https://github.com/axios/axios/issues/6818)) ([10fa70e](https://github.com/axios/axios/commit/10fa70ef14fe39558b15a179f0e82f5f5e5d11b2))
- **xhr/fetch:** pass `allowAbsoluteUrls` to `buildFullPath` in `xhr` and `fetch` adapters ([#6814](https://github.com/axios/axios/issues/6814)) ([ec159e5](https://github.com/axios/axios/commit/ec159e507bdf08c04ba1a10fe7710094e9e50ec9))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/3238291?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Ashcon Partovi](https://github.com/Electroid "+6/-0 (#6811 )")
- <img src="https://avatars.githubusercontent.com/u/28559054?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [StefanBRas](https://github.com/StefanBRas "+4/-0 (#6818 )")
- <img src="https://avatars.githubusercontent.com/u/8029107?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Marc Hassan](https://github.com/mhassan1 "+2/-2 (#6814 )")

## [1.8.2](https://github.com/axios/axios/compare/v1.8.1...v1.8.2) (2025-03-07)

### Bug Fixes

- **http-adapter:** add allowAbsoluteUrls to path building ([#6810](https://github.com/axios/axios/issues/6810)) ([fb8eec2](https://github.com/axios/axios/commit/fb8eec214ce7744b5ca787f2c3b8339b2f54b00f))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/14166260?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Fasoro-Joseph Alexander](https://github.com/lexcorp16 "+1/-1 (#6810 )")

## [1.8.1](https://github.com/axios/axios/compare/v1.8.0...v1.8.1) (2025-02-26)

### Bug Fixes

- **utils:** move `generateString` to platform utils to avoid importing crypto module into client builds; ([#6789](https://github.com/axios/axios/issues/6789)) ([36a5a62](https://github.com/axios/axios/commit/36a5a620bec0b181451927f13ac85b9888b86cec))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+51/-47 (#6789 )")

# [1.8.0](https://github.com/axios/axios/compare/v1.7.9...v1.8.0) (2025-02-25)

### Bug Fixes

- **examples:** application crashed when navigating examples in browser ([#5938](https://github.com/axios/axios/issues/5938)) ([1260ded](https://github.com/axios/axios/commit/1260ded634ec101dd5ed05d3b70f8e8f899dba6c))
- missing word in SUPPORT_QUESTION.yml ([#6757](https://github.com/axios/axios/issues/6757)) ([1f890b1](https://github.com/axios/axios/commit/1f890b13f2c25a016f3c84ae78efb769f244133e))
- **utils:** replace getRandomValues with crypto module ([#6788](https://github.com/axios/axios/issues/6788)) ([23a25af](https://github.com/axios/axios/commit/23a25af0688d1db2c396deb09229d2271cc24f6c))

### Features

- Add config for ignoring absolute URLs ([#5902](https://github.com/axios/axios/issues/5902)) ([#6192](https://github.com/axios/axios/issues/6192)) ([32c7bcc](https://github.com/axios/axios/commit/32c7bcc0f233285ba27dec73a4b1e81fb7a219b3))

### Reverts

- Revert "chore: expose fromDataToStream to be consumable (#6731)" (#6732) ([1317261](https://github.com/axios/axios/commit/1317261125e9c419fe9f126867f64d28f9c1efda)), closes [#6731](https://github.com/axios/axios/issues/6731) [#6732](https://github.com/axios/axios/issues/6732)

### BREAKING CHANGES

- code relying on the above will now combine the URLs instead of prefer request URL

- feat: add config option for allowing absolute URLs

- fix: add default value for allowAbsoluteUrls in buildFullPath

- fix: typo in flow control when setting allowAbsoluteUrls

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/7661715?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Michael Toscano](https://github.com/GethosTheWalrus "+42/-8 (#6192 )")
- <img src="https://avatars.githubusercontent.com/u/22686401?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Willian Agostini](https://github.com/WillianAgostini "+26/-3 (#6788 #6777 )")
- <img src="https://avatars.githubusercontent.com/u/72578270?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Naron](https://github.com/naronchen "+27/-0 (#5901 )")
- <img src="https://avatars.githubusercontent.com/u/47430686?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [shravan || श्रvan](https://github.com/shravan20 "+7/-3 (#6116 )")
- <img src="https://avatars.githubusercontent.com/u/145078271?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Justin Dhillon](https://github.com/justindhillon "+0/-7 (#6312 )")
- <img src="https://avatars.githubusercontent.com/u/30925732?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [yionr](https://github.com/yionr "+5/-1 (#6129 )")
- <img src="https://avatars.githubusercontent.com/u/534166?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Shin&#x27;ya Ueoka](https://github.com/ueokande "+3/-3 (#5935 )")
- <img src="https://avatars.githubusercontent.com/u/33569?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dan Dascalescu](https://github.com/dandv "+3/-3 (#5908 #6757 )")
- <img src="https://avatars.githubusercontent.com/u/16476523?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Nitin Ramnani](https://github.com/NitinRamnani "+2/-2 (#5938 )")
- <img src="https://avatars.githubusercontent.com/u/152275799?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Shay Molcho](https://github.com/shaymolcho "+2/-2 (#6770 )")
- <img src="https://avatars.githubusercontent.com/u/4814473?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Jay](https://github.com/jasonsaayman "+0/-3 (#6732 )")
- fancy45daddy
- <img src="https://avatars.githubusercontent.com/u/127725897?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Habip Akyol](https://github.com/habipakyol "+1/-1 (#6030 )")
- <img src="https://avatars.githubusercontent.com/u/54869395?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Bailey Lissington](https://github.com/llamington "+1/-1 (#6771 )")
- <img src="https://avatars.githubusercontent.com/u/14969290?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Bernardo da Eira Duarte](https://github.com/bernardoduarte "+1/-1 (#6480 )")
- <img src="https://avatars.githubusercontent.com/u/117800149?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Shivam Batham](https://github.com/Shivam-Batham "+1/-1 (#5949 )")
- <img src="https://avatars.githubusercontent.com/u/67861627?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Lipin Kariappa](https://github.com/lipinnnnn "+1/-1 (#5936 )")

## [1.7.9](https://github.com/axios/axios/compare/v1.7.8...v1.7.9) (2024-12-04)

### Reverts

- Revert "fix(types): export CJS types from ESM (#6218)" (#6729) ([c44d2f2](https://github.com/axios/axios/commit/c44d2f2316ad289b38997657248ba10de11deb6c)), closes [#6218](https://github.com/axios/axios/issues/6218) [#6729](https://github.com/axios/axios/issues/6729)

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/4814473?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Jay](https://github.com/jasonsaayman "+596/-108 (#6729 )")

## [1.7.8](https://github.com/axios/axios/compare/v1.7.7...v1.7.8) (2024-11-25)

### Bug Fixes

- allow passing a callback as paramsSerializer to buildURL ([#6680](https://github.com/axios/axios/issues/6680)) ([eac4619](https://github.com/axios/axios/commit/eac4619fe2e0926e876cd260ee21e3690381dbb5))
- **core:** fixed config merging bug ([#6668](https://github.com/axios/axios/issues/6668)) ([5d99fe4](https://github.com/axios/axios/commit/5d99fe4491202a6268c71e5dcc09192359d73cea))
- fixed width form to not shrink after 'Send Request' button is clicked ([#6644](https://github.com/axios/axios/issues/6644)) ([7ccd5fd](https://github.com/axios/axios/commit/7ccd5fd42402102d38712c32707bf055be72ab54))
- **http:** add support for File objects as payload in http adapter ([#6588](https://github.com/axios/axios/issues/6588)) ([#6605](https://github.com/axios/axios/issues/6605)) ([6841d8d](https://github.com/axios/axios/commit/6841d8d18ddc71cc1bd202ffcfddb3f95622eef3))
- **http:** fixed proxy-from-env module import ([#5222](https://github.com/axios/axios/issues/5222)) ([12b3295](https://github.com/axios/axios/commit/12b32957f1258aee94ef859809ed39f8f88f9dfa))
- **http:** use `globalThis.TextEncoder` when available ([#6634](https://github.com/axios/axios/issues/6634)) ([df956d1](https://github.com/axios/axios/commit/df956d18febc9100a563298dfdf0f102c3d15410))
- ios11 breaks when build ([#6608](https://github.com/axios/axios/issues/6608)) ([7638952](https://github.com/axios/axios/commit/763895270f7b50c7c780c3c9807ae8635de952cd))
- **types:** add missing types for mergeConfig function ([#6590](https://github.com/axios/axios/issues/6590)) ([00de614](https://github.com/axios/axios/commit/00de614cd07b7149af335e202aef0e076c254f49))
- **types:** export CJS types from ESM ([#6218](https://github.com/axios/axios/issues/6218)) ([c71811b](https://github.com/axios/axios/commit/c71811b00f2fcff558e4382ba913bdac4ad7200e))
- updated stream aborted error message to be more clear ([#6615](https://github.com/axios/axios/issues/6615)) ([cc3217a](https://github.com/axios/axios/commit/cc3217a612024d83a663722a56d7a98d8759c6d5))
- use URL API instead of DOM to fix a potential vulnerability warning; ([#6714](https://github.com/axios/axios/issues/6714)) ([0a8d6e1](https://github.com/axios/axios/commit/0a8d6e19da5b9899a2abafaaa06a75ee548597db))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/779047?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Remco Haszing](https://github.com/remcohaszing "+108/-596 (#6218 )")
- <img src="https://avatars.githubusercontent.com/u/4814473?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Jay](https://github.com/jasonsaayman "+281/-19 (#6640 #6619 )")
- <img src="https://avatars.githubusercontent.com/u/140250471?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Aayush Yadav](https://github.com/aayushyadav020 "+124/-111 (#6617 )")
- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+12/-65 (#6714 )")
- <img src="https://avatars.githubusercontent.com/u/479715?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Ell Bradshaw](https://github.com/cincodenada "+29/-0 (#6489 )")
- <img src="https://avatars.githubusercontent.com/u/60218780?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Amit Saini](https://github.com/amitsainii "+13/-3 (#5237 )")
- <img src="https://avatars.githubusercontent.com/u/19817867?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Tommaso Paulon](https://github.com/guuido "+14/-1 (#6680 )")
- <img src="https://avatars.githubusercontent.com/u/63336443?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Akki](https://github.com/Aakash-Rana "+5/-5 (#6668 )")
- <img src="https://avatars.githubusercontent.com/u/20028934?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Sampo Silvennoinen](https://github.com/stscoundrel "+3/-3 (#6633 )")
- <img src="https://avatars.githubusercontent.com/u/1174718?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Kasper Isager Dalsgarð](https://github.com/kasperisager "+2/-2 (#6634 )")
- <img src="https://avatars.githubusercontent.com/u/3709715?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Christian Clauss](https://github.com/cclauss "+4/-0 (#6683 )")
- <img src="https://avatars.githubusercontent.com/u/1639119?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Pavan Welihinda](https://github.com/pavan168 "+2/-2 (#5222 )")
- <img src="https://avatars.githubusercontent.com/u/5742900?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Taylor Flatt](https://github.com/taylorflatt "+2/-2 (#6615 )")
- <img src="https://avatars.githubusercontent.com/u/79452224?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Kenzo Wada](https://github.com/Kenzo-Wada "+2/-2 (#6608 )")
- <img src="https://avatars.githubusercontent.com/u/50064240?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Ngole Lawson](https://github.com/echelonnought "+3/-0 (#6644 )")
- <img src="https://avatars.githubusercontent.com/u/1262198?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Haven](https://github.com/Baoyx007 "+3/-0 (#6590 )")
- <img src="https://avatars.githubusercontent.com/u/149003676?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Shrivali Dutt](https://github.com/shrivalidutt "+1/-1 (#6637 )")
- <img src="https://avatars.githubusercontent.com/u/1304290?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Henco Appel](https://github.com/hencoappel "+1/-1 (#6605 )")

## [1.7.7](https://github.com/axios/axios/compare/v1.7.6...v1.7.7) (2024-08-31)

### Bug Fixes

- **fetch:** fix stream handling in Safari by fallback to using a stream reader instead of an async iterator; ([#6584](https://github.com/axios/axios/issues/6584)) ([d198085](https://github.com/axios/axios/commit/d1980854fee1765cd02fa0787adf5d6e34dd9dcf))
- **http:** fixed support for IPv6 literal strings in url ([#5731](https://github.com/axios/axios/issues/5731)) ([364993f](https://github.com/axios/axios/commit/364993f0d8bc6e0e06f76b8a35d2d0a35cab054c))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/10539109?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Rishi556](https://github.com/Rishi556 "+39/-1 (#5731 )")
- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+27/-7 (#6584 )")

## [1.7.6](https://github.com/axios/axios/compare/v1.7.5...v1.7.6) (2024-08-30)

### Bug Fixes

- **fetch:** fix content length calculation for FormData payload; ([#6524](https://github.com/axios/axios/issues/6524)) ([085f568](https://github.com/axios/axios/commit/085f56861a83e9ac02c140ad9d68dac540dfeeaa))
- **fetch:** optimize signals composing logic; ([#6582](https://github.com/axios/axios/issues/6582)) ([df9889b](https://github.com/axios/axios/commit/df9889b83c2cc37e9e6189675a73ab70c60f031f))

### Contributors to this release

- <img src="https://avatars.githubusercontent.com/u/12586868?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Dmitriy Mozgovoy](https://github.com/DigitalBrainJS "+98/-46 (#6582 )")
- <img src="https://avatars.githubusercontent.com/u/3534453?v&#x3D;4&amp;s&#x3D;18" alt="avatar" width="18"/> [Jacques Germishuys](https://github.com/jacquesg "+5/-1 (#6524 )")

<!-- Truncated: this is the first 400 of 1416 lines of the real CHANGELOG.md as of the pinned commit. See fixtures/provenance.yaml for the exact source. -->
