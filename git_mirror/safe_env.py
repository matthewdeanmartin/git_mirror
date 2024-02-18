from dotenv import load_dotenv


def load_env():
    try:
        load_dotenv()  # Load environment variables from .env file if present
    except Exception as e:
        print(f"Error loading .env file: {e}")
        print("Continuing without .env file.")
