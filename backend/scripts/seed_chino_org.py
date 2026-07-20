import asyncio
import sys
from beanie import PydanticObjectId
from src.database import connect_database, disconnect_database
from src.organization.models import Organization, InstitutionAccount
from src.organization.constants import OrganizationStatus, AccountStatus, InstitutionRole
from src.auth.services.crypto import get_password_hash

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8')

async def main():
    print("Connecting to database...")
    await connect_database()
    try:
        org_id_str = "6a59e269c9cd9ac958c05e6a"
        org_id = PydanticObjectId(org_id_str)
        
        # 1. Fetch the organization
        org = await Organization.get(org_id)
        if not org:
            print(f"Error: Organization with ID {org_id_str} not found in database.")
            return

        print(f"Found Organization: {org.name} (Type: {org.type})")
        
        # 2. Ensure the organization is APPROVED and ACTIVE
        if org.status != OrganizationStatus.APPROVED:
            print(f"Updating organization status from {org.status} to {OrganizationStatus.APPROVED}...")
            org.status = OrganizationStatus.APPROVED
            await org.save()
            print("Organization status updated successfully.")
            
        # 3. Create or Update mock InstitutionAccount
        mock_email = "chino_admin@gmail.com"
        mock_password = "Password123!"
        hashed_pw = get_password_hash(mock_password)
        
        account = await InstitutionAccount.find_one({"email": mock_email})
        if account:
            print(f"Institution account '{mock_email}' already exists. Re-seeding details...")
            account.org_id = org_id
            account.password_hash = hashed_pw
            account.role = InstitutionRole.SUPERADMIN
            account.twofa_enabled = False
            account.twofa_method = None
            account.status = AccountStatus.ACTIVE
            await account.save()
            print(f"Successfully updated account '{mock_email}'.")
        else:
            print(f"Creating new institution account '{mock_email}'...")
            account = InstitutionAccount(
                org_id=org_id,
                email=mock_email,
                password_hash=hashed_pw,
                role=InstitutionRole.SUPERADMIN,
                twofa_method=None,
                twofa_enabled=False,
                status=AccountStatus.ACTIVE
            )
            await account.insert()
            print(f"Successfully created account '{mock_email}'.")
            
        print("\n--- Mock Data Summary ---")
        print(f"Organization ID: {org_id_str}")
        print(f"Organization Name: {org.name}")
        print(f"Email: {mock_email}")
        print(f"Password: {mock_password}")
        print(f"Status: {account.status}")
        
    except Exception as e:
        print(f"An error occurred: {e}", file=sys.stderr)
    finally:
        await disconnect_database()

if __name__ == "__main__":
    asyncio.run(main())
