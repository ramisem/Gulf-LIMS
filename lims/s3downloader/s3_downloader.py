import boto3
import os
import time
import json
from datetime import datetime, timezone
from cryptography.fernet import Fernet

#V1: Fetch Files from s3 bucket to a folder on user machine
#V2: Scan multiple folders on s3 bucket and place on respective folders (introduce config.json)
#V3: Encryting Keys with cryptography.fernet, Move ENCRYPT_KEYS to System Variables

CONFIG_FILE = 'config.json'
ENCRYPTION_KEY_ENV_VAR_NAME = "S3_DOWNLOADER_ENCRYPTION_KEY"

# --- Function to load configuration ---
def load_config():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    config_path = os.path.join(script_dir, CONFIG_FILE)
    if not os.path.exists(config_path):
        raise FileNotFoundError(f"Config file not found at: {config_path}. Please create {CONFIG_FILE}.")
    with open(config_path, 'r') as f:
        config = json.load(f)

    # Get the encryption key from environment variables
    encryption_key_str = os.environ.get(ENCRYPTION_KEY_ENV_VAR_NAME)

    if not encryption_key_str:
        raise ValueError(
            f"Encryption key environment variable '{ENCRYPTION_KEY_ENV_VAR_NAME}' not found. "
            "Please set it (e.g., in Windows Environment Variables)."
        )

    try:
        encryption_key = eval(encryption_key_str)
        if not isinstance(encryption_key, bytes):
             raise ValueError("Encryption key from environment variable is not in the correct byte string format (e.g., b'key_value=').")

    except (SyntaxError, TypeError, NameError) as e:
        raise ValueError(f"Invalid format for encryption key in environment variable: {e}. "
                         "It should be a byte string like b'YOUR_KEY_HERE='")


    f = Fernet(encryption_key)
    try:
        # Decrypt AWS credentials
        config['AWS_ACCESS_KEY_ID'] = f.decrypt(config['ENCRYPTED_AWS_ACCESS_KEY_ID'].encode()).decode()
        config['AWS_SECRET_ACCESS_KEY'] = f.decrypt(config['ENCRYPTED_AWS_SECRET_ACCESS_KEY'].encode()).decode()
        print("AWS credentials decrypted successfully from config.json.")
    except KeyError:
        print("ERROR: Encrypted AWS credentials (ENCRYPTED_AWS_ACCESS_KEY_ID or ENCRYPTED_AWS_SECRET_ACCESS_KEY)")
        print("       not found in config.json. Please ensure they are present and correctly named.")
        exit(1)
    except Exception as e:
        print(f"ERROR: Could not decrypt AWS credentials. Check the encryption key's value in environment variable or encrypted values in config.json. Error: {e}")
        exit(1)

    return config

# Load config early
try:
    CONFIG = load_config()
except FileNotFoundError as e:
    print(f"ERROR: {e}")
    print("Please create a 'config.json' file in the same directory as the script with encrypted credentials.")
    exit(1)
except ValueError as e:
    print(f"Configuration Error: {e}")
    print("Please ensure your encryption key environment variable is correctly set and config.json is properly set up.")
    exit(1)

AWS_ACCESS_KEY_ID = CONFIG['AWS_ACCESS_KEY_ID']
AWS_SECRET_ACCESS_KEY = CONFIG['AWS_SECRET_ACCESS_KEY']
AWS_S3_REGION_NAME = CONFIG['AWS_S3_REGION_NAME']
POLLING_INTERVAL_SECONDS = CONFIG['POLLING_INTERVAL_SECONDS']
DOWNLOAD_PATHS = CONFIG['DOWNLOAD_PATHS']

def get_s3_client():
    """Initializes and returns an S3 client."""
    return boto3.client(
        's3',
        aws_access_key_id=AWS_ACCESS_KEY_ID,
        aws_secret_access_key=AWS_SECRET_ACCESS_KEY,
        region_name=AWS_S3_REGION_NAME
    )

def get_last_download_info(local_metadata_path):
    """Reads the last downloaded file info from a local file, specific to a path."""
    if os.path.exists(local_metadata_path):
        try:
            with open(local_metadata_path, 'r') as f:
                data = json.load(f)
            if data.get('last_modified'):
                data['last_modified'] = datetime.fromisoformat(data['last_modified']).replace(tzinfo=timezone.utc)
            return data
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error reading last download info file ({os.path.basename(local_metadata_path)}): {e}. Starting fresh for this path.")
            return {'last_key': None, 'last_modified': None}
    return {'last_key': None, 'last_modified': None}

def save_last_download_info(last_key, last_modified, local_metadata_path):
    """Saves the last downloaded file info to a local file, specific to a path."""
    data = {
        'last_key': last_key,
        'last_modified': last_modified.isoformat() if last_modified else None
    }
    os.makedirs(os.path.dirname(local_metadata_path), exist_ok=True)
    with open(local_metadata_path, 'w') as f:
        json.dump(data, f, indent=4)

def download_new_files():
    s3 = get_s3_client()
    print("\n--- Starting New Polling Cycle ---")

    for path_config in DOWNLOAD_PATHS:
        s3_bucket = path_config['s3_bucket']
        s3_prefix = path_config['s3_prefix']
        current_local_download_base_path = path_config['local_full_path'] 
        
        import hashlib
        prefix_hash = hashlib.md5(s3_prefix.encode()).hexdigest()
        metadata_filename = f".last_download_info_{prefix_hash}.json"
        local_metadata_file_path = os.path.join(current_local_download_base_path, metadata_filename)


        last_info = get_last_download_info(local_metadata_file_path)
        last_modified_timestamp = last_info.get('last_modified')

        print(f"\nScanning: s3://{s3_bucket}/{s3_prefix}")
        print(f"Downloading to: {current_local_download_base_path}")
        print(f"Last downloaded file's modified time for this path: {last_modified_timestamp}")

        try:
            # Ensure the base download directory exists
            os.makedirs(current_local_download_base_path, exist_ok=True)

            response = s3.list_objects_v2(
                Bucket=s3_bucket,
                Prefix=s3_prefix
            )

            new_files_downloaded = False
            latest_key_in_bucket = last_info.get('last_key')
            latest_modified_in_bucket = last_info.get('last_modified')

            if 'Contents' in response:
                objects = sorted(response['Contents'], key=lambda x: x['LastModified'])

                for obj in objects:
                    key = obj['Key']
                    if key == s3_prefix: # Skip the "folder" itself (if it exists as an object)
                        continue

                    last_modified = obj['LastModified']

                    if last_modified_timestamp is None or last_modified > last_modified_timestamp:
                        relative_path_in_s3_prefix = os.path.relpath(key, s3_prefix)
                        local_filename = os.path.join(current_local_download_base_path, relative_path_in_s3_prefix)
                        
                        os.makedirs(os.path.dirname(local_filename), exist_ok=True)

                        print(f"  Downloading: s3://{s3_bucket}/{key} to {local_filename}")
                        s3.download_file(s3_bucket, key, local_filename)
                        print(f"  Successfully downloaded: {os.path.basename(key)}")
                        new_files_downloaded = True
                        latest_key_in_bucket = key
                        latest_modified_in_bucket = last_modified

            if new_files_downloaded:
                save_last_download_info(latest_key_in_bucket, latest_modified_in_bucket, local_metadata_file_path)
                print(f"Download process complete for {s3_prefix}. Saved last download info.")
            else:
                print(f"No new files to download from {s3_prefix}.")

        except boto3.exceptions.ClientError as e:
            error_code = e.response.get("Error", {}).get("Code")
            print(f"An S3 client error occurred for {s3_prefix}: {e}")
            if error_code == "AccessDenied":
                print(f"  ACCESS DENIED: Check permissions for bucket '{s3_bucket}' and prefix '{s3_prefix}'.")
            elif error_code == "NoSuchBucket":
                print(f"  NO SUCH BUCKET: Check if bucket '{s3_bucket}' exists and region is correct.")
            else:
                print(f"  Unhandled S3 Client Error: {error_code} - {e}")
        except Exception as e:
            print(f"An unexpected error occurred for {s3_prefix}: {e}")

if __name__ == "__main__":
    print(f"Starting S3 file downloader. Polling every {POLLING_INTERVAL_SECONDS} seconds.")

    while True:
        download_new_files()
        print(f"\nNext poll in {POLLING_INTERVAL_SECONDS} seconds...")
        time.sleep(POLLING_INTERVAL_SECONDS)