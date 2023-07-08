from dataclasses import dataclass

@dataclass
class Artist:
    id: str
    name: str
    genres: 'list[str]'
