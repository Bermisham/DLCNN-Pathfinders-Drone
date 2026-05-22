from djitellopy import tello

def connect_drone():
    drone = tello.Tello()
    drone.RETRY_COUNT = 1
    try:
        drone.connect()
        return drone
    except Exception:
        return None


def check_drone_connection(drone):
    try:
        drone.get_battery()
        return True
    except:
        return False
    

def get_drone_battery(drone):
    try:
        return drone.get_battery()
    except:
        return None


def get_drone_serial_number(drone):
    try:
        return drone.query_serial_number()
    except:
        return None


def get_drone_SNR(drone):
    try:
        return drone.query_wifi_signal_noise_ratio()
    except:
        return None