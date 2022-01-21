from birge_comm_net import CommNetNode

key = "/sensor_node_0/temperature"
val = -100

if __name__ == "__main__":
    client = CommNetNode()
    client.connect(("localhost", 8000))

    while True:
        client.set(key, val)
        data = client.get(key)

        #data = client.getAll()
        
        val = data["data"][key] + 1

        print(val)
        
