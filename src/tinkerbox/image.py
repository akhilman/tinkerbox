from pprint import pp

from tinkerbox.profile.image import ImageProfile


def build_image(profile: ImageProfile, replace=False):
    pp(profile.flatten().substitute().to_object())
    # raise NotImplementedError
