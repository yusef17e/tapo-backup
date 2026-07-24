"""Bare-minimum pytapo auth test — straight from the pytapo README, no wrapper code."""
import getpass
from pytapo import Tapo

host = input("Camera IP: ").strip()
user = input("Camera account username (e.g. admin): ").strip()
password = getpass.getpass("Camera account password: ")

tapo = Tapo(host, user, password)
print(tapo.getBasicInfo())
