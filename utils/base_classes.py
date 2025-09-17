from abc import ABC
from typing import TypeVar, Type

T = TypeVar('T', bound='Singleton')


class Singleton(ABC):
    """
    Thread-safe singleton base class that eliminates duplicate singleton pattern implementations
    """
    _instances = {}
    _initialized = {}

    def __new__(cls: Type[T]) -> T:
        if cls not in cls._instances:
            cls._instances[cls] = super().__new__(cls)
            cls._initialized[cls] = False
        return cls._instances[cls]

    def __init__(self):
        # Prevent re-initialization
        if self.__class__ in self._initialized and self._initialized[self.__class__]:
            return
        self._initialize()
        self._initialized[self.__class__] = True

    def _initialize(self):
        """
        Override this method in subclasses to implement initialization logic.
        This method is called only once per singleton instance.
        """
        pass

    @classmethod
    def get_instance(cls: Type[T]) -> T:
        """Get singleton instance with lazy loading"""
        if cls not in cls._instances:
            cls._instances[cls] = cls()
        return cls._instances[cls]

    @classmethod
    def clear_instance(cls):
        """Clear singleton instance (mainly for testing)"""
        if cls in cls._instances:
            del cls._instances[cls]
        if cls in cls._initialized:
            del cls._initialized[cls]