## Architecture: Founder Signup & Onboarding Entry Point

The signup flow provisions a new tenant (`Company`) and root account (`User` with `FOUNDER` role) in a single transactional write, issuing a JWT token for immediate authenticated onboarding.

```mermaid
graph TD
    Client["Unauthenticated Client<br/>POST /api/v1/auth/signup"]

    subgraph API["FastAPI Layer — app/api/v1/auth.py"]
        SignupEndpoint["signup(payload: SignupRequest)"]
        TokenResp["TokenResponse<br/>access_token, expires_in"]
    end

    subgraph Validation["Pydantic Schemas — app/schemas/"]
        SignupReq["SignupRequest<br/>company_name, industry<br/>company_description (max 4000)<br/>founder_email, founder_password"]
        PersonaCfg["PersonaConfig<br/>company_context = company_description"]
    end

    subgraph Services["Core Security & Repositories"]
        CompanyRepo["CompanyRepository.create()<br/>name, industry, persona_config"]
        UserRepo["UserRepository.create()<br/>email, password_hash, role=FOUNDER"]
        HashPW["hash_password()<br/>passlib + bcrypt"]
        JWTToken["create_access_token()<br/>claims: sub=user.id, company_id=company.id, role=founder"]
    end

    subgraph Storage["PostgreSQL Database (Neon)"]
        Companies[("companies table<br/>name, industry, persona_config")]
        Users[("users table<br/>company_id, email, password_hash, role")]
    end

    Client -->|Payload| SignupEndpoint
    SignupEndpoint --> SignupReq
    SignupEndpoint --> PersonaCfg
    SignupEndpoint --> CompanyRepo
    CompanyRepo --> Companies
    SignupEndpoint --> HashPW
    SignupEndpoint --> UserRepo
    UserRepo --> Users
    Companies -->|"company.id"| UserRepo
    SignupEndpoint --> JWTToken
    JWTToken --> TokenResp
    TokenResp -->|200 OK + JWT Bearer| Client
```

### Key Takeaways
1. **Atomic Creation:** `Company` and founder `User` are flushed and committed together in one database transaction.
2. **Context Persistence:** `company_description` immediately populates `persona_config.company_context` for system prompt extraction.
3. **Immediate Onboarding:** The returned JWT token allows the client to call founder-gated endpoints (`POST /onboarding/employees/bulk`, `PATCH /company`) immediately without a secondary login call.
