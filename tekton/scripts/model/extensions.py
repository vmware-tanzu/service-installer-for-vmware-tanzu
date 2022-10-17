from abc import abstractmethod


class extensions_types():
    @abstractmethod
    def fluent_bit(self,fluent_bit_type):
        pass

    @abstractmethod
    def grafana(self):
        pass

    @abstractmethod
    def logging(self):
        pass

    @abstractmethod
    def prometheus(self):
        pass


class deploy_extensions():
    @abstractmethod
    def deploy(self, extention_name):
        pass
