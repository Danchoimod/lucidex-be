import asyncio
from pathlib import Path
import sys

# Ensure backend directory is in sys.path
backend_dir = Path(__file__).resolve().parent.parent
if str(backend_dir) not in sys.path:
    sys.path.insert(0, str(backend_dir))

# Force UTF-8 output
sys.stdout.reconfigure(encoding="utf-8")

from src.database import connect_database, disconnect_database
from src.otp.models import OtpCode


async def clean_otp_codes():
    print("Connecting to database...")
    await connect_database()
    try:
        # Delete all documents in otp_codes collection via Beanie
        await OtpCode.delete_all()
        print("✅ Successfully cleaned collection 'otp_codes'. All documents removed.")
    except Exception as e:
        print(f"❌ An error occurred while cleaning 'otp_codes': {e}", file=sys.stderr)
    finally:
        await disconnect_database()


if __name__ == "__main__":
    asyncio.run(clean_otp_codes())
