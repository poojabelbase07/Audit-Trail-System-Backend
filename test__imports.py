# save as test_imports.py
print("Testing imports step by step...")

try:
    print("1. Importing config...")
    from app.core.config import settings
    print("   ✅ Config OK")
except Exception as e:
    print(f"   ❌ Config failed: {e}")
    exit(1)

try:
    print("2. Importing security...")
    from app.core.security import hash_password
    print("   ✅ Security OK")
except Exception as e:
    print(f"   ❌ Security failed: {e}")
    exit(1)

try:
    print("3. Importing database...")
    from app.database import Base, engine, get_db
    print("   ✅ Database OK")
except Exception as e:
    print(f"   ❌ Database failed: {e}")
    exit(1)

try:
    print("4. Importing models...")
    from app.models import User, Task, AuditLog
    print("   ✅ Models OK")
except Exception as e:
    print(f"   ❌ Models failed: {e}")
    exit(1)

try:
    print("5. Importing dependencies...")
    from app.core.dependencies import get_current_user
    print("   ✅ Dependencies OK")
except Exception as e:
    print(f"   ❌ Dependencies failed: {e}")
    exit(1)

try:
    print("6. Initializing database...")
    from app.database import init_db
    init_db()
    print("   ✅ Database initialized")
except Exception as e:
    print(f"   ❌ Init failed: {e}")
    exit(1)

print("\n🎉 ALL TESTS PASSED!")