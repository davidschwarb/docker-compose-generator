# docker-compose-generator
#### WIP: This is by no means a finished project, but I will be adding more compatability in the future.

Converts docker service commands to docker compose file .yml structure.

Steps to use:
---
Import the file 'composeGenerator' and then call the function with a multi line string argument.

```python
from composeGenerator import dockerComposeGenerator as g
g('''
#Docker service commands go here.
''')
```
