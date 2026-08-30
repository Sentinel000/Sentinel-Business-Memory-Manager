# Tasks: Founder Signup & Onboarding Entry Point

- [x] Add `industry` column to `Company` model in `app/models/company.py`
- [x] Create Alembic migration `d1f89a2b5e01_add_company_industry.py`
- [x] Expose `industry` on `CompanyRead` and `CompanyUpdate` schemas in `app/schemas/company.py`
- [x] Expose `industry` on `CompanySummary` schema in `app/schemas/auth.py`
- [x] Add `SignupRequest` model to `app/schemas/auth.py` with `company_description` context validation
- [x] Add `POST /auth/signup` endpoint in `app/api/v1/auth.py` to provision company and founder user
- [x] Run Alembic migration `alembic upgrade head`
- [x] Verify signup and authentication flow with integration tests
- [x] Run `scripts/verify.py` full suite green
- [x] Add entry to `CHANGELOG.md`
