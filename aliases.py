from typing import Literal, TypeAlias

# could also use NewType(name, type)

ElementType: TypeAlias = Literal['node', 'way', 'relation']
Identifier: TypeAlias = str
Tags: TypeAlias = dict[str, str]
Selectors: TypeAlias = tuple[str, ...]
