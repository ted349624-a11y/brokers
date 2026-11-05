"""Create the Broker (verified) role and the #verify channel with the ✅ button, then apply permissions."""
import os, sys
sys.path.insert(0, os.path.dirname(__file__))
from setup import call, base, pretty, PRETTY, SEP, TIE_RED
import permissions

PRETTY["verify"] = "✅" + SEP + "verify"


def main():
    gid = call("GET", "/users/@me/guilds")[0]["id"]
    roles = {r["name"]: r for r in call("GET", f"/guilds/{gid}/roles")}
    if "Broker" not in roles:
        call("POST", f"/guilds/{gid}/roles", {"name": "Broker", "color": 0, "permissions": "0", "hoist": True})
        print("Role created: Broker")

    chans = {base(c["name"]): c for c in call("GET", f"/guilds/{gid}/channels") if c["type"] != 4}
    if "verify" in chans:
        vid, new = chans["verify"]["id"], False
    else:
        vid = call("POST", f"/guilds/{gid}/channels", {"name": pretty("verify", False), "type": 0,
                                                        "topic": "Press the button to enter the server.", "position": 0})["id"]
        new = True
        print("Channel created: #verify")
    call("PATCH", f"/guilds/{gid}/channels", [{"id": vid, "position": 0, "parent_id": None}])

    msgs = call("GET", f"/channels/{vid}/messages?limit=10")
    if not any(m.get("components") for m in msgs):
        call("POST", f"/channels/{vid}/messages", {
            "embeds": [{"title": "Welcome to Elysium Broker",
                        "description": "Press **✅ Verify** to enter the server.\n\n"
                                       "By verifying you agree to the rules. The team will never DM you first "
                                       "or ask for your seed phrase.",
                        "color": TIE_RED}],
            "components": [{"type": 1, "components": [
                {"type": 2, "style": 3, "label": "Verify", "emoji": {"name": "✅"}, "custom_id": "eb_verify"}]}]})
        print("Verify button posted")

    permissions.main()


if __name__ == "__main__":
    main()
