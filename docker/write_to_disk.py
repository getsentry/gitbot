#!/usr/bin/env python3
# This script is temporary until we can switch to using Google Secret Manager
import os

KEY = os.environ["DEPLOY_SSH_KEY"]
FILE = "private_ssh_key"

# When the key is a single line, it will contain \n characters representing new lines
# that need to be removed when writing to disk
# This is to support local development versus GCR execution
if KEY.find("\n") != -1:
    contents = KEY.split("\n")
    with open(FILE, "w") as f:
        f.writelines("%s\n" % line for line in contents)
elif KEY.find("\\n") != -1:
    contents = KEY.split("\\n")
    with open(FILE, "w") as f:
        f.writelines("%s\n" % line for line in contents)
else:
    with open(FILE, "w") as f:
        f.write(KEY + "\n")
