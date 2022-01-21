# Birge Comm Net

## Installation

```
pip install ./dist/birge_comm_net-0.0.1.tar.gz
```

## Examples

### Server

```python
from birge_comm_net import CommNetCore

server = CommNetCore(("localhost", 8000), log_level=logging.INFO)
server.run()
```

### Client 

```python
from birge_comm_net import CommNetNode

    
key = "/sensor_node_0/temperature"
val = -100

client = CommNetNode()
client.connect(("localhost", 8000))

while True:
    client.set(key, val)
    data = client.get(key)

    #data = client.getAll()
    
    val = data["data"][key] + 1

    print(val)     
```

### WebSocket Transponder

see `examples/ws_transponder.py`
