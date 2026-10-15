"""Check the separately recorded research-copy Langfuse readback offline."""

from housing.reporting.study_readback import verify_study_readback

if __name__ == "__main__":
    captures, observations = verify_study_readback()
    print(f"Verified {captures} research-copy captures and {observations} observations.")
