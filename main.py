import code
from typing import Final
import os

import hfs_api
from hfs_api import HFS

domain: Final[str] = os.environ["DOMAIN"]
hfs = HFS(domain)

hfs.authorize("admin", os.environ["ADMIN_PASSWORD"])

print(hfs.get_cookies())

resp = hfs.upload_file("C:/9384.img", "/a1/a2/a3/a4/9384.img", hfs_api.OVERWRITE)

code.interact(local=locals())
