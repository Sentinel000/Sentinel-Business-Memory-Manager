"""Provisioning a company's HydraDB database.

Done lazily rather than only at signup, because companies created before this feature
existed have no database, and a founder should not have to re-onboard to get memory.
Called on the write path; provisioning is idempotent and cheap once the id is stored.
"""

import logging
import uuid

from sqlalchemy.orm import Session

from app.knowledge.store import get_knowledge_store
from app.models.company import Company

logger = logging.getLogger(__name__)


def database_name_for(company_id: uuid.UUID) -> str:
    """A stable, collision-free database name.

    Derived from the company id rather than its name: names are edited, and the
    tenant boundary must not move when someone fixes a typo.
    """
    return f"sentinel_{company_id.hex}"


def ensure_knowledge_database(db: Session, company: Company) -> str | None:
    """Return the company's HydraDB database, creating it if needed.

    Returns None when knowledge memory is unconfigured or provisioning fails — the
    caller carries on without it rather than failing the request.
    """
    if company.hydra_tenant_id:
        return company.hydra_tenant_id

    store = get_knowledge_store()
    if store is None:
        return None

    database = database_name_for(company.id)
    if not store.provision(database):
        logger.warning("Could not provision knowledge database for company %s", company.id)
        return None

    company.hydra_tenant_id = database
    db.commit()
    logger.info("Company %s provisioned knowledge database %s", company.id, database)
    return database
