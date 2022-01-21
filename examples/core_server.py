import logging

from birge_comm_net import CommNetCore

if __name__ == "__main__":
    server = CommNetCore(("localhost", 8000), log_level=logging.INFO)
    server.run()
