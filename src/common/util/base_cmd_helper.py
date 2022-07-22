"""
BaseCmdHelper is an abstract class which provides methods for running commands.
Derived classes must provide implementations for these methods.
Examples of derived classes may include helpers for local command, ssh command, docker command, etc.
"""
from abc import ABC, abstractmethod


class BaseCmdHelper(ABC):
    @abstractmethod
    def run_cmd(self, cmd: str, ignore_errors=False) -> int:
        """
        Method to execute the given command
        :param cmd: cmd to execute
        :param ignore_errors: If set to False, will result in an Exception
        :return: Returns exit code of command
        """
        pass

    @abstractmethod
    def run_cmd_output(self, cmd: str, ignore_errors=False) -> tuple:
        """
        Method to execute the given command and return output
        :param cmd: cmd to execute
        :param ignore_errors: If set to False, will result in an Exception
        :return: Returns a tuple containing exit code and output of the command
        """
        pass
