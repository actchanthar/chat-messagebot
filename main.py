import logging
import logging.handlers
import sys

# Set up logging before imports
log_file = '/tmp/test.log'
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.DEBUG,
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.handlers.RotatingFileHandler(log_file, maxBytes=10*1024*1024, backupCount=5)
    ]
)
logger = logging.getLogger(__name__)
logger.debug("Logging initialized in test.py")

try:
    import os
    from motor.motor_asyncio import AsyncIOMotorClient
    from config import MONGODB_URL, MONGODB_NAME

    logger.debug("Imports completed successfully")

    def test():
        try:
            logger.debug("Starting test script")
            logger.debug(f"Python version: {sys.version}")

            # Log environment variables
            logger.info("Checking environment variables")
            required_vars = ['MONGODB_URL', 'MONGODB_NAME']
            env_vars = {var: os.getenv(var) for var in required_vars}
            missing_vars = [var for var in required_vars if not env_vars[var]]
            if missing_vars:
                logger.warning(f"Missing environment variables: {', '.join(missing_vars)}. Using config.py values.")
            else:
                logger.info(f"Environment variables found: {', '.join(var for var in required_vars if env_vars[var])}")

            # Use environment variable with fallback to config.py
            mongo_url = os.getenv('MONGODB_URL', MONGODB_URL)
            mongo_db_name = os.getenv('MONGODB_NAME', MONGODB_NAME)
            logger.debug(f"MongoDB URL (partial): {mongo_url[:30]}...")
            logger.debug(f"MongoDB database name: {mongo_db_name}")

            if not mongo_url or not mongo_db_name:
                logger.error("MONGODB_URL or MONGODB_NAME is not set")
                raise ValueError("MONGODB_URL or MONGODB_NAME is not set")

            # Test MongoDB connection
            logger.info("Attempting to connect to MongoDB")
            client = AsyncIOMotorClient(mongo_url)
            db = client[mongo_db_name]
            logger.info("MongoDB client initialized successfully")

            logger.debug("Testing MongoDB connection with ping")
            client.admin.command('ping')
            logger.info("MongoDB connection test successful")

        except Exception as e:
            logger.error(f"Test failed: {e}", exc_info=True)
            raise

    if __name__ == "__main__":
        logger.debug("Entering test script")
        test()

except Exception as e:
    logger.error(f"Critical error before test: {e}", exc_info=True)
    raise