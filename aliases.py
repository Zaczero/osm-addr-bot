from typing import TypeAlias, Literal

# could also use NewType(name, type)

ElementType: TypeAlias = Literal['node', 'way', 'relation']
Identifier: TypeAlias = str
Tags: TypeAlias = dict[str, str]
