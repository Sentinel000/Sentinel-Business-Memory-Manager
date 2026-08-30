# Founder Signup & Onboarding Entry Point

## Context

Previously, the only way a `Company` + founder `User` row could come into existence was `backend/scripts/seed.py` — a manual, out-of-band script. Every existing API endpoint required an already-authenticated founder (`FounderUser` dependency), meaning there was no mechanism for a new client to self-provision a tenant. 

This feature adds `POST /auth/signup` to establish a clean entry point for the founder onboarding flow (company details → token → optional employee import → optional persona tuning).

## Key Architectural Decisions

- **`company_description`:** Mandatory at signup and stored directly in `persona_config.company_context` — the field consumed by the task extractor system prompt. No separate `company_description` database column is created, avoiding duplicate/drifting free-text fields.
- **`industry` column:** Added as a plain `String(200)` nullable column on `Company`.
- **Onboarding endpoints:** Employee import (`POST /onboarding/employees/bulk`) and persona tuning (`PATCH /company`) remain founder-gated endpoints called by the frontend post-signup using the returned JWT token.
- **Multi-tenancy email uniqueness:** Email uniqueness is scoped per-company (`uq_users_company_email`). Every signup creates a new `Company` tenant, allowing duplicate email addresses across independent company tenants.

## Implementation Detail

### 1. Database Migration & Model (`Company.industry`)
- Added `industry: Mapped[str | None] = mapped_column(String(200), nullable=True)` to `backend/app/models/company.py`.
- Migration revision `d1f89a2b5e01_add_company_industry.py` (`down_revision = 'c8ad23ad5b04'`):
  - `upgrade()`: `op.add_column('companies', sa.Column('industry', sa.String(length=200), nullable=True))`
  - `downgrade()`: `op.drop_column('companies', 'industry')`

### 2. Schemas
- `backend/app/schemas/company.py`: Added `industry: str | None = None` to `CompanyRead` and `CompanyUpdate`.
- `backend/app/schemas/auth.py`: Added `industry: str | None = None` to `CompanySummary` and created `SignupRequest`:
  ```python
  class SignupRequest(BaseModel):
      company_name: str = Field(min_length=1, max_length=200)
      industry: str = Field(min_length=1, max_length=200)
      company_description: str = Field(min_length=1, max_length=MAX_COMPANY_CONTEXT)
      founder_email: EmailStr
      founder_password: str = Field(min_length=8, max_length=128)
      founder_full_name: str | None = None
  ```

### 3. API Route (`POST /auth/signup`)
- Located in `backend/app/api/v1/auth.py`:
  1. Instantiates `PersonaConfig(company_context=payload.company_description)`.
  2. Creates new `Company` tenant via `CompanyRepository.create(name=..., industry=..., persona_config=...)`.
  3. Creates founder `User` via `UserRepository.create(email=..., password_hash=hash_password(...), full_name=..., role=UserRole.FOUNDER)`.
  4. Flushes and commits single transaction.
  5. Generates and returns JWT token via `create_access_token` and `TokenResponse`.

## Verification Plan

1. **Alembic Migration Verification:**
   - Execute `alembic upgrade head` to apply revision `d1f89a2b5e01`.
2. **Endpoint Verification:**
   - Call `POST /api/v1/auth/signup` and verify `200 OK` return with valid JWT.
   - Call `GET /api/v1/auth/me` with token to confirm `role: founder`, `company.industry`, and `company.persona_config.company_context`.
   - Call `POST /api/v1/auth/signup` again with same email for a second company tenant to confirm multi-tenant isolation.
3. **Full Suite Verification:**
   - Execute `scripts/verify.py` to ensure all 74 system tests pass green.
