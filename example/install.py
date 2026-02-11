from configuration_final import conf

from pykod.repositories.base import Repository

print("-" * 100)
# Print all attributes from conf
print("Configuration attributes:")
for attr_name in dir(conf):
    if not attr_name.startswith("_"):
        attr_value = getattr(conf, attr_name)
        print(f"> {attr_name}: {attr_value} :: {type(attr_value)}")
# pprint.pp(conf)
# print(dir(objx))

print("\n", "-" * 100)
# print(conf.repos)
# for k, v in conf.get("repos", {}).items():
#     print(k)
#     v.install()

for attr_name in dir(conf):
    if not attr_name.startswith("_"):
        attr_value = getattr(conf, attr_name)
        if isinstance(attr_value, Repository):
            print(f"====> {attr_name}: {attr_value} :: {type(attr_value)}")
            attr_value.install()

# print(conf.ret)
print(conf.archpkgs._pkgs)
print(conf.aurpkgs._pkgs)
