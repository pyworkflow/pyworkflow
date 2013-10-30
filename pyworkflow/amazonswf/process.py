from .. import Process

class AmazonSWFProcess(Process):
    """
    Amazon SWF requires token to be used when completing activities or decisions.
    """

    def __init__(self, token, *args, **kwargs):
        self.token = token
        super(AmazonSWFProcess, self).__init__(*args, **kwargs)