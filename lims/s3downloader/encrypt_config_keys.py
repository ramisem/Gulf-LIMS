# encrypt_config_keys.py
from cryptography.fernet import Fernet
import sys

# --- How to use this script: ---
# 1. Run it: python encrypt_config_keys.py
# 2. It will generate a new Fernet encryption key for you. COPY THIS KEY.
# 3. Paste this key as the value for 'ENCRYPTION_KEY =' in BOTH this script AND s3_downloader.py.
#    Example: ENCRYPTION_KEY = b'your_generated_key_here='
# 4. Run it again: python encrypt_config_keys.py
# 5. It will ask for your plain AWS Access Key ID and Secret Access Key.
# 6. It will print the encrypted versions. COPY these into your config.json.

# !!! IMPORTANT: This key MUST be the same as the one used in s3_downloader.py !!!
# This is where you will paste the key generated in step 2 above.
# For example: ENCRYPTION_KEY = b'YOUR_GENERATED_FERNET_KEY_GOES_HERE='
ENCRYPTION_KEY = b'' # <--- Replace this empty byte string with your generated key, including the b' prefix and trailing ='


def generate_and_display_key():
    """Generates a Fernet key and prints it for the user to copy."""
    key = Fernet.generate_key()
    print("\n--- GENERATE YOUR FERNET ENCRYPTION KEY ---")
    print("This is your secret Fernet key. Copy this EXACT value (including b'' and the trailing '='):")
    print(f"ENCRYPTION_KEY = {key}")
    print("--------------------------------------------")
    print("\nPASTE this key into the 'ENCRYPTION_KEY' variable in:")
    print("  1. This 'encrypt_config_keys.py' script (replacing the empty b'').")
    print("  2. Your 's3_downloader.py' script (where 'ENCRYPTION_KEY' is defined).")
    print("\nAfter pasting, RUN THIS SCRIPT AGAIN to encrypt your credentials.")


def encrypt_string(text, key):
    """Encrypts a string using the provided Fernet key."""
    f = Fernet(key)
    return f.encrypt(text.encode()).decode()

if __name__ == "__main__":
    try:
        # Check if the ENCRYPTION_KEY has been set
        if not ENCRYPTION_KEY:
            generate_and_display_key()
            print("\nExiting now. Please update the script with the generated key and run again.")
            sys.exit(0)

        print(f"Using encryption key (first 10 chars): {ENCRYPTION_KEY.decode()[:10]}...")

        print("\n--- Encrypting AWS Credentials ---")
        aws_access_key_id = input("Enter your AWS Access Key ID (plain text): ")
        aws_secret_access_key = input("Enter your AWS Secret Access Key (plain text): ")

        if not aws_access_key_id or not aws_secret_access_key:
            print("Access Key ID and Secret Access Key cannot be empty. Exiting.")
            sys.exit(1)

        encrypted_access_key_id = encrypt_string(aws_access_key_id, ENCRYPTION_KEY)
        encrypted_secret_access_key = encrypt_string(aws_secret_access_key, ENCRYPTION_KEY)

        print("\n--- Encrypted Credentials (Copy these into your config.json) ---")
        print(f'"ENCRYPTED_AWS_ACCESS_KEY_ID": "{encrypted_access_key_id}",')
        print(f'"ENCRYPTED_AWS_SECRET_ACCESS_KEY": "{encrypted_secret_access_key}"')
        print("------------------------------------------------------------------")
        print("\nRemember to REMOVE 'AWS_ACCESS_KEY_ID' and 'AWS_SECRET_ACCESS_KEY'")
        print("from your 'config.json' and REPLACE them with the encrypted values above.")

    except ImportError:
        print("Error: 'cryptography' library not found.")
        print("Please install it using: pip install cryptography")
        sys.exit(1)
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        sys.exit(1)