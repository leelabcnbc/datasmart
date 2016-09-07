import random
from faker import Factory

fake = Factory.create()


def reseed(seed=None):
    fake.seed(seed)
    random.seed(seed)
