"""
User defined exceptions based on Python base Exception class. Used to raise specific exception to provide more
information to end user regarding exception.

For Example, a method can raise “NotImplementedError” user defined exception when it detects that this method is not
implemented in this class
"""


class NotImplementedException(Exception):
    """
    Exception Class - Block Iteration
    Raise this Exception when we want to block the test execution.

    Usage:
    raise BlockTestException('Required Arguments Missing [%s]'% str(""))
    """

    def __init__(self, value):
        super(NotImplementedException, self).__init__(value)
        self.value = value


class JsonReadException(Exception):
    """
    Exception Class - Json Read Exception

    Usage:
    raise JsonReadException("Json Read Exception occurred") from e*
    """

    # Constructor
    def __init__(self, value):
        self.value = value

    def __str__(self) -> object:
        """
        Method to define Exception
        :return:
        """
        return "Exception: %s" % self.value


class IterationBlockedException(Exception):
    """
    Exception Class - Block Iteration
    Raise this Exception when we want to end Iteration.

    Usage:
    raise IterationBlockedException('Required JSON file is missing [%s]'% str(""))
    """

    # Constructor
    def __init__(self, value):
        self.value = value

    def __str__(self) -> object:
        """
        Method to define Exception
        :return:
        """
        return "Exception: %s" % self.value


class LoginFailedException(Exception):
    """
    Exception Class - Login Failed
    Raise this Exception when there is a login Failed to external services.

    Usage:
    raise LoginFailedException('Login to market place failed')
    """

    # Constructor
    def __init__(self, value):
        self.value = value

    def __str__(self) -> object:
        """
        Method to define Exception
        :return:
        """
        return self.value
