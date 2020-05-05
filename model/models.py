

class TableProcessor:
    """Class to interface with the database for exports messages
     and keep channels list and revisions list """

    def __init__(self, config):
        """
        Initialise the table processor. `config` should be a dict-like
        object from the config file's Database section".
        """
        self.config = config

