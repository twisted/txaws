class Bucket(object):
    """An Amazon S3 storage bucket."""

    def __init__(self, name, creation_date):
        self.name = name
        self.creation_date = creation_date


class FileChunk(object):
    """
    An Amazon S3 file chunk. 
    
    S3 returns file chunks, 10 MB at a time, until the entire file is returned.
    These chunks need to be assembled once they are all returned.
    """

