import pickle
import sys
from pathlib import Path


def read_configuration_pickle(generation_id: int = 0, base_path: str = "mnt") -> dict:
    """
    Read a configuration pickle file for a specific generation.

    Args:
        generation_id: The generation ID to read (default: 0)
        base_path: Base path for the mnt directory (default: "mnt")

    Returns:
        Dictionary containing configuration and repositories

    Raises:
        FileNotFoundError: If the pickle file doesn't exist
        Exception: For other pickle loading errors
    """
    pickle_path = (
        Path(base_path)
        / "kod"
        / "generations"
        / str(generation_id)
        / "configuration.pkl"
    )

    if not pickle_path.exists():
        raise FileNotFoundError(f"Configuration pickle not found: {pickle_path}")

    print(f"Reading configuration from: {pickle_path}")

    with open(pickle_path, "rb") as f:
        config = pickle.load(f)

    return config


def print_configuration(config: dict) -> None:
    """
    Print the configuration and repositories in a readable format.

    Args:
        config: Configuration dictionary containing 'configuration' and 'repositories'
    """
    print("\n" + "=" * 60)
    print("REPOSITORIES:")
    print("=" * 60)
    if "repositories" in config:
        for repo_name, repo_obj in config["repositories"].items():
            print(f"  • {repo_name}: {type(repo_obj).__name__}")
    else:
        print("  No repositories found in configuration")

    print("\n" + "=" * 60)
    print("CONFIGURATION:")
    print("=" * 60)
    if "configuration" in config:
        config_obj = config["configuration"]
        for attr in dir(config_obj):
            if not attr.startswith("_"):
                try:
                    value = getattr(config_obj, attr)
                    if not callable(value):
                        print(f"  • {attr}: {value}")
                except Exception as e:
                    print(f"  • {attr}: <Error: {e}>")
    else:
        print("  No configuration object found")

    print("\n" + "=" * 60)
    print("RAW KEYS:")
    print("=" * 60)
    for key in config.keys():
        value = config[key]
        value_type = type(value).__name__
        if isinstance(value, (dict, list)):
            value_preview = f"<{value_type} with {len(value)} items>"
        else:
            value_preview = f"<{value_type}>"
        print(f"  • {key}: {value_preview}")


def main():
    """Main entry point for the script."""
    generation_id = 0
    base_path = "mnt"

    if len(sys.argv) > 1:
        try:
            generation_id = int(sys.argv[1])
        except ValueError:
            print(f"Error: Invalid generation ID '{sys.argv[1]}'")
            print(
                "Usage: python3 read_configuration_pickle.py [generation_id] [base_path]"
            )
            sys.exit(1)

    if len(sys.argv) > 2:
        base_path = sys.argv[2]

    try:
        config = read_configuration_pickle(generation_id, base_path)
        print_configuration(config)
        print("\n✅ Successfully read configuration")
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error reading configuration: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
