"""Compatibility imports for the data pipeline now housed in backend.src."""

from backend.src.data_pipeline import *  # noqa: F401,F403

if __name__ == "__main__":
    frame = build_processed_observations()
    print(f"Wrote {len(frame)} processed observation rows to {OUT_FILE}")
