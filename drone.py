from asyncio import sleep
from djitellopy import tello

def connect_drone() -> tello.Tello:
    drone = tello.Tello()
    drone.RETRY_COUNT = 1
    try:
        drone.connect()
        return drone
    except Exception:
        return None


def check_drone_connection(drone) -> bool:
    try:
        drone.get_battery()
        return True
    except:
        return False
    

def get_drone_battery(drone) -> int:
    try:
        return drone.get_battery()
    except:
        return None


def get_drone_serial_number(drone) -> str:
    try:
        return drone.query_serial_number()
    except:
        return None


def get_drone_SNR(drone) -> str:
    try:
        return drone.query_wifi_signal_noise_ratio()
    except:
        return None
    

def get_drone_temp(drone) -> float:
    try:
        return drone.get_temperature()
    except:
        return None
    

def drone_start(drone) -> bool:
    try:
        # Add drone route
        drone.takeoff()
        sleep(1)
        drone.move_down(40)
        sleep(1)
        drone.land()
        return True
    except:
        return False