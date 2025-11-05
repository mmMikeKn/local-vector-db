import os
import time
import csv
import signal
import matplotlib.pyplot as plt
from collections import deque

# Global variables to store data
timestamps = deque()
param1 = deque()
param2 = deque()
param3 = deque()

# Signal handler for keyboard interrupt
def signal_handler(sig, frame):
    print("\nKeyboard interrupt received. Saving plot...")
    create_plot()
    exit(0)

def create_plot():
    plt.figure(figsize=(10, 6))
    
    plt.plot(timestamps, param1, label="GPU Mem.Utilization")
    plt.plot(timestamps, param2, label="GPU Temperature")
    plt.plot(timestamps, param3, label="GPU Utilization")
    
    plt.xlabel("Time (seconds)")
    plt.ylabel("Value")
    plt.title("Time-Value Diagram")
    plt.legend()
    plt.grid(True)
    plt.savefig("gpu-inf.jpg")
    print("Plot saved as 'gpu-diag.jpg'")

def parse_data():
# https://nvidia.custhelp.com/app/answers/detail/a_id/3751/~/useful-nvidia-smi-queries
    result = os.popen("nvidia-smi --query-gpu=temperature.gpu,utilization.memory,utilization.gpu --format=csv,noheader,nounits").read()
    list = [float(num.strip()) for num in result.split(',')]
    temperature = list[0]
    mem_utilization = list[1]
    gpu_utilization = list[2]
    timestamps.append(time.time())
    param1.append(mem_utilization)
    param2.append(temperature)
    param3.append(gpu_utilization)
    print("temperature {:.1f},  mem.utilization {:.1f} %,  gpu.utilization {:.1f} % ".format(temperature, mem_utilization, gpu_utilization))

def main():
    signal.signal(signal.SIGINT, signal_handler)
    try:
        while True:
            parse_data()
            time.sleep(1)
    except KeyboardInterrupt:
        pass

if __name__ == "__main__":
    main()