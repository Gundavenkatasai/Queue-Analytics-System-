"""
Real-time Detection Simulator - Simulates person detection without needing a camera
Sends continuous updates to the API to demonstrate live dashboard updates
"""

import time
import random
import logging
from datetime import datetime
from api_client import APIClient

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DetectionSimulator:
    """Simulates real-time person detection data"""

    def __init__(self):
        """Initialize simulator with API client"""
        self.api_client = APIClient()
        self.people_count = 5
        self.queue_length = 2
        self.entry_count = 10
        self.exit_count = 5
        self.frame_count = 0
        logger.info("🎬 Detection Simulator initialized")

    def generate_realistic_data(self):
        """Generate realistic changing data to simulate live detection"""
        # Simulate people count changes (people entering/leaving)
        change = random.randint(-2, 3)
        self.people_count = max(0, min(80, self.people_count + change))

        # Queue length often correlates with people count
        queue_change = random.randint(-1, 2)
        self.queue_length = max(0, min(self.people_count, self.queue_length + queue_change))

        # Entries increase over time
        entry_change = random.randint(0, 2)
        self.entry_count += entry_change

        # Exits increase (but usually less than entries)
        exit_change = random.randint(0, 1)
        self.exit_count += exit_change

        # Calculate derived metrics
        occupancy_percentage = (self.people_count / 50) * 100
        queue_detected = self.queue_length > 3
        dwell_time_avg = random.uniform(20, 120)
        dwell_time_max = dwell_time_avg + random.uniform(10, 50)
        avg_wait_time = self.queue_length * random.uniform(2, 5) if queue_detected else 0

        return {
            'people_count': self.people_count,
            'queue_length': self.queue_length,
            'entry_count': self.entry_count,
            'exit_count': self.exit_count,
            'occupancy_percentage': occupancy_percentage,
            'queue_detected': queue_detected,
            'dwell_time_avg': dwell_time_avg,
            'dwell_time_max': dwell_time_max,
            'avg_wait_time': avg_wait_time,
        }

    def run(self, interval=1):
        """
        Run the simulator
        
        Args:
            interval: Seconds between updates (default 1 second)
        """
        logger.info(f"🚀 Starting detection simulator (updating every {interval}s)")
        logger.info("✓ Press Ctrl+C to stop\n")

        try:
            while True:
                # Generate realistic data
                data = self.generate_realistic_data()
                self.frame_count += 1

                # Send to API
                success, response = self.api_client.send_analytics(data)

                if success:
                    # Display update
                    logger.info(
                        f"✓ Frame #{self.frame_count:04d} | "
                        f"People: {data['people_count']:2d} | "
                        f"Queue: {data['queue_length']:2d} | "
                        f"Entries: {data['entry_count']:3d} | "
                        f"Exits: {data['exit_count']:3d}"
                    )
                else:
                    logger.error(f"✗ Failed to send data: {response}")

                # Wait before next update
                time.sleep(interval)

        except KeyboardInterrupt:
            logger.info("\n\n✓ Simulator stopped by user")
        except Exception as e:
            logger.error(f"✗ Simulator error: {e}")


if __name__ == "__main__":
    simulator = DetectionSimulator()
    simulator.run(interval=1)  # Update every 1 second
