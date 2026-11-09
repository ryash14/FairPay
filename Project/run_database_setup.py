"""Step 1: create the database, its six tables and the seeded accounts.

Safe to run again: existing tables and accounts are left exactly as they are.

    python run_database_setup.py
"""
import os
import secrets

from config import config


def main():
    os.makedirs(config.DATABASE_DIRECTORY, exist_ok=True)
    from access.password_security import hash_password
    from persistence import repository
    from persistence.database import database_engine, session_factory
    from persistence.models import Base, UserAccount

    Base.metadata.create_all(database_engine)
    print(f"database: {config.APPLICATION_DATABASE_FILE}")
    print(f"tables: {', '.join(sorted(Base.metadata.tables))}")
    created = present = 0
    with session_factory() as session:
        for account in config.SEED_USER_ACCOUNTS:
            if repository.fetch_user_account(session, UserAccount.username == account["username"]) is not None:
                present += 1
                continue
            salt = secrets.token_hex(config.PASSWORD_SALT_BYTES)
            repository.insert_user_account(session, {
                "username": account["username"], "display_name": account["display_name"], "role": account["role"],
                "password_hash": hash_password(account["password"], salt), "password_salt": salt,
            })
            created += 1
            print(f"account created {account['username']:<10}{account['display_name']:<20}{account['role']}")
    print(f"accounts created: {created}, already present: {present}")
    return created


if __name__ == "__main__":
    main()
