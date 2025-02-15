import logging
from src.monitor import SeatMonitor

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("seat_monitor.log"), logging.StreamHandler()],
)


def main():
    monitor = SeatMonitor()
    monitor.run()


if __name__ == "__main__":
    main()
