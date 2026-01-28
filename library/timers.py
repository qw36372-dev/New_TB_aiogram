import asyncio
import logging
from concurrent.futures import ThreadPoolExecutor

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class Timer:
    def __init__(self, interval, callback):
        self.interval = interval
        self.callback = callback
        self._loop = asyncio.get_event_loop()  # Ensure loop is obtained in a thread-safe way
        self._stop_event = asyncio.Event()
        self._task = None

    async def _run(self):
        while not self._stop_event.is_set():
            logging.info('Timer triggered')
            await self.callback()  # Run callback
            await asyncio.sleep(self.interval)

    def start(self):
        if self._task is None:
            self._task = self._loop.create_task(self._run())
            logging.info('Timer started')

    def stop(self):
        if self._task:
            self._stop_event.set()  # Signal to stop the loop
            self._task.cancel()  # Cancel the task
            self._task = None
            logging.info('Timer stopped')

# Example usage of Timer class
async def example_callback():
    try:
        logging.info('Executing callback...')
        # Your callback logic here...
    except Exception as e:
        logging.error(f'Error in callback: {e}')  # Log any errors that occur

if __name__ == '__main__':
    timer = Timer(5, example_callback)  # A timer that triggers every 5 seconds
    timer.start()
    try:
        asyncio.get_event_loop().run_forever()
    except KeyboardInterrupt:
        timer.stop()
        logging.info('Program terminated by user.')
