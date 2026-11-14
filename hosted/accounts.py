"""Create a staff password hash interactively; never put passwords in arguments."""
import getpass
import json
from hosted.app import password_hash


def main():
    email = input("Staff email: ").strip().lower()
    if "@" not in email:
        raise SystemExit("Enter a valid staff email.")
    password = getpass.getpass("Choose a password (14+ characters): ")
    if len(password) < 14:
        raise SystemExit("Use at least 14 characters.")
    if password != getpass.getpass("Repeat password: "):
        raise SystemExit("Passwords did not match.")
    print("Add this account to STAFF_ACCOUNTS_JSON in Render (merge with existing accounts):")
    print(json.dumps({email: password_hash(password)}))


if __name__ == "__main__":
    main()
