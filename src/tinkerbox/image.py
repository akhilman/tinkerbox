from pprint import pp
from tinkerbox.profile import Profile


def build_image(profile: Profile, replace=False):
    pp(profile.flatten().substitute().to_object())
    # raise NotImplementedError
