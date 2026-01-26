from abc import ABC, abstractmethod

class BaseAgent(ABC):
    name: str

    @abstractmethod
    async def run(self, context: dict) -> dict:
        pass