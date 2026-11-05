"""Rename channels and categories to the decorated style (emoji｜name, Category ════)."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, pretty


def main():
    gid = call("GET", "/users/@me/guilds")[0]["id"]
    for c in call("GET", f"/guilds/{gid}/channels"):
        new = pretty(c["name"], c["type"] == 4)
        if new and new != c["name"]:
            call("PATCH", f"/channels/{c['id']}", {"name": new})
            print(f"{c['name']}  ->  {new}")
        else:
            print(f"unchanged: {c['name']}")
    print("\nDone.")


if __name__ == "__main__":
    main()
