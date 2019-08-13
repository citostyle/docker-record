import os
from .container.instrumented_container import InstrumentedContainer
from .curators.curation import NaiveCuration
from .transformers.naive_docker_transformer import NaiveDockerTransformer


"""
## restructure
# c = InstrumentedContainer(name)
# c.record()
# --> introduce another abstracted helper function for stuff like
# execute(['docker', 'exec', container_name, '>', '/tmp/record/diff_trigger'])
# c.exec('>', '/tmp/record/diff_trigger')
#
# Make container util class for stuff like container_exists
#
# There is a central place where we store info on where the state changes are persisted
# right now it's statically encoded in read_fs_changes (track_state_changes then takes these to not start from scratch)
#
# Have exclusion patterns for limiting the queries to filesystem in container for timing information
#
# Introduce transient change tracking (probably in track_state_changes)
#
# Have another class that takes in all the state change information and tries to create the Dockerfile
# That can be totally abstracted away, probably we can provide a super simple base class for this
# class Generator:
#   def generate <-- weird name, I can probably do better than this
#
#   --> base generator also has a standard I/O provider
#
# Probably it's actually that simple, because then I can have subclasses like
# DockerfileGenerator
# AnsibleGenerator
# DockerfileIdiomaticGenerator (inherits from DockerfileGenerator and
# adds the opaque function from our probabilistic model)
#
# g = DockerfileGenerator()
#
# g.generate()
# In that sense, the InstrumentedContainer and the generators can be
# seen as two totally orthogonal programs  that only communicate over
# the shared state change data structures
#
# Although it might make sense to do some of the optimizations on the fly
# (like remove commands that have no state changes, might make tracking harder and more convoluted though)
#
# class DockerfileGenerator()
#    def __init__(container_name):
#
#    # returns a Dockerfile Object
#    def generate():
#
#
# class OutputProvider() # base class
#   def __init__():
#
#   def ... <-- not sure how the output provider should look like
#
#
#
"""

def record(container_name):
    container = InstrumentedContainer(container_name)

    pid = os.fork()
    #TODO: clean up background process
    if pid > 0:
        # starts interactive session
        container.start()
    else:
        # initialize and track
        container.initialize()
        container.track_state_changes()

def replay(container_name):
    container = InstrumentedContainer(container_name)
    curated_stg = NaiveCuration(container).curate()
    dockerfile = NaiveDockerTransformer(curated_stg).transform()













