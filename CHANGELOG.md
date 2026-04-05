# Changelog

All notable changes to the Talenti platform will be documented in this file.

## [0.2.0](https://github.com/dcava30/Talenti_MVP/compare/v0.1.0...v0.2.0) (2026-03-20)


### Features

* add blob-first candidate uploads, interview lifecycle APIs, and db-backed worker jobs ([85627de](https://github.com/dcava30/Talenti_MVP/commit/85627de9ace09a995e5110ab993b522ae76d8f62))
* add bulk resume ingestion, claimable prefilled candidate accounts, and interview gating ([eef4f17](https://github.com/dcava30/Talenti_MVP/commit/eef4f172debcf0f63b477232a5e5c6c8eb0d32f7))
* align blob-first uploads, backend-worker deployment, and orchestration docs ([dc51b79](https://github.com/dcava30/Talenti_MVP/commit/dc51b7916e39ab38b8117d3b4688eca18ff50b9a))
* **db:** migrate repo to PostgreSQL-only defaults with startup Alembic auto-migrations ([c6de2fa](https://github.com/dcava30/Talenti_MVP/commit/c6de2fa44ab08688625cdb6708a7737bdcbbf6b3))
* **devops:** implement v2 deploy architecture with backend-owned ACS orchestration ([aeb8b81](https://github.com/dcava30/Talenti_MVP/commit/aeb8b816e7c221eb4876f61d9fa53cb49f774a02))
* **devops:** implement v2 dev deployment architecture (backend public, internal ACS worker) ([82399d5](https://github.com/dcava30/Talenti_MVP/commit/82399d542831fb3e725e1c0f0df235e7ff22c701))
* **frontend:** split hosting by environment for dev, uat, and prod ([3ff5453](https://github.com/dcava30/Talenti_MVP/commit/3ff5453980a38df0ec404b7d3acc74d3cef6e476))
* **infra:** add Azure env export script for local config ([d300707](https://github.com/dcava30/Talenti_MVP/commit/d30070740cc4b40a32250197587b43b04884eb96))
* **local-dev:** split local startup and test flow into smaller scripts ([ef83487](https://github.com/dcava30/Talenti_MVP/commit/ef83487a35e049e5b34f13b718347cbd017dd082))
* **local:** complete local bring-up readiness and path/config fixes ([c3d90bb](https://github.com/dcava30/Talenti_MVP/commit/c3d90bb0cee932b141430a209eceda26d604e357))
* **local:** complete local bring-up readiness and path/config fixes ([8be389b](https://github.com/dcava30/Talenti_MVP/commit/8be389b7d27cdf4fdafdc086fc49ecbe79724a4a))
* migrate platform from SQLite to PostgreSQL with startup Alembic auto-migrations ([1faa6e3](https://github.com/dcava30/Talenti_MVP/commit/1faa6e34528ccae43f50013687c7cd93b6497058))
* **platform:** add Codex bootstrap for SSH model repos, Azure OIDC environments, and day-one deployment access ([7096d86](https://github.com/dcava30/Talenti_MVP/commit/7096d8677fa43a7cbb5334f274ab4a0d600847c0))
* **platform:** add Codex bootstrap for SSH repos, Azure OIDC, and env setup ([1a3e0ea](https://github.com/dcava30/Talenti_MVP/commit/1a3e0eac2563062743e42fca0adcdcb755769d7b))
* **postgres:** full SQLite-&gt;PostgreSQL migration, startup auto-migrations, and isolated test DBs ([77ccd99](https://github.com/dcava30/Talenti_MVP/commit/77ccd9926a95d23a31924ede975d31984a10c6e0))
* **postgres:** migrate from SQLite to PostgreSQL with startup auto-migrations and isolated test DBs ([856c012](https://github.com/dcava30/Talenti_MVP/commit/856c01292069bab0850cfd51b67699c11ce5bd17))
* **release:** add trunk-based release, promotion, and observability pipeline ([871fa38](https://github.com/dcava30/Talenti_MVP/commit/871fa3840b4b7385f65ddd903baa2f8b00fea72d))


### Bug Fixes

* **acs-worker:** bump psycopg binary pin ([eb9c421](https://github.com/dcava30/Talenti_MVP/commit/eb9c421922b89944656df7b87f316128186b5ca0))
* **alembic:** shorten overlong revision ids for postgres compatibility ([23cf443](https://github.com/dcava30/Talenti_MVP/commit/23cf443a82c1d09440596736de0e2bfc6d8a0e14))
* **backend:** pin bcrypt below v5 for passlib compatibility ([0501f72](https://github.com/dcava30/Talenti_MVP/commit/0501f72c0b00108b36be55c2faadf37da67ac383))
* **config:** tolerate azure list env formatting ([67c6216](https://github.com/dcava30/Talenti_MVP/commit/67c621611d7d5baa2935f66a8b42bb1a22564318))
* **dev-bootstrap:** harden recovery flow and acs image build ([6c60509](https://github.com/dcava30/Talenti_MVP/commit/6c605099717d4ddcc891f5838ea79c2e387b8c4a))
* **dev-deploy:** harden model rollout and normalize scoring integration ([4b8288d](https://github.com/dcava30/Talenti_MVP/commit/4b8288d26eb6d37bb62030d16f58ca1a6ff1fc32))
* **dev-deploy:** harden model rollout and normalize scoring integration ([1645734](https://github.com/dcava30/Talenti_MVP/commit/1645734ffbdab196858607f3403d1568ef4a46f3))
* **migrations:** resolve alembic path in ci ([5b2f906](https://github.com/dcava30/Talenti_MVP/commit/5b2f90680f75c5f9a99634a44e946b5b5d4c700d))
* **release:** enable GitHub Actions PR creation for release-please ([c20a920](https://github.com/dcava30/Talenti_MVP/commit/c20a920fc68d4218e06b8af448cb30ee085d20a8))


### Documentation

* refresh architecture diagrams with system design and deployment views ([6140597](https://github.com/dcava30/Talenti_MVP/commit/6140597d892e43b05571700559b4614e7deee6a4))


### CI

* **actions:** upgrade workflow actions for Node 24 compatibility ([64312d7](https://github.com/dcava30/Talenti_MVP/commit/64312d7993be20070f263e8f944d37ec82ef07e0))
* **deploy-dev:** switch model deployments to pinned ACR digests from dev env vars ([9d3abeb](https://github.com/dcava30/Talenti_MVP/commit/9d3abeb85070e31dd73842a6d58ee935b0512f37))

## 0.1.0

- Initial tracked platform release baseline.
