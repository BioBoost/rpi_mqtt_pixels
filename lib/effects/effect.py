class Effect(object):

    def __init__(self, pixelStrip):
        self.pixelStrip = pixelStrip

    def start(self):
        """ Implement the starting of the effect here """
        raise NotImplementedError("Please Implement this method")

    def stop(self):
        """ Implement the stopping of the effect here """
        raise NotImplementedError("Please Implement this method")

    def run(self):
        """ Implement the actual effect here """
        raise NotImplementedError("Please Implement this method")
