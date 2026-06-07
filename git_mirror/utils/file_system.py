import os

from platformdirs import user_cache_dir, user_config_dir, user_data_dir


def setup_app_directories(app_name: str):
    # Define the directory paths for config, data, and cache
    config_dir = user_config_dir(app_name)
    data_dir = user_data_dir(app_name)
    cache_dir = user_cache_dir(app_name)

    # Create the directories if they don't already exist
    for directory in [config_dir, data_dir, cache_dir]:
        os.makedirs(directory, exist_ok=True)

    # Define the path for the SQLite database file in the data directory
    sqlite_file_path = os.path.join(data_dir, f"{app_name}.sqlite")

    return {
        "config_dir": config_dir,
        "data_dir": data_dir,
        "cache_dir": cache_dir,
        "sqlite_file_path": sqlite_file_path,
    }


if __name__ == "__main__":
    # Example usage
    app_name = "my_app"
    directories = setup_app_directories(app_name)
    print(directories)
