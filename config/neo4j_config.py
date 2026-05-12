import os
from neo4j import GraphDatabase
from dotenv import load_dotenv

from .logger import logger

load_dotenv()

class Neo4jConfig:
    def __init__(self):
        self.uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        self.username = os.getenv("NEO4J_USER", os.getenv("NEO4J_USERNAME", "neo4j"))
        self.password = os.getenv("NEO4J_PASSWORD")
        self.driver = None

    def connect(self):
        try:
            if not self.driver:
                self.driver = GraphDatabase.driver(self.uri, auth=(self.username, self.password))
                # Verify connectivity
                self.driver.verify_connectivity()
                logger.info("Successfully connected to Neo4j")
            return self.driver
        except Exception as e:
            logger.error(f"Failed to connect to Neo4j: {str(e)}")
            return None

    def close(self):
        if self.driver:
            self.driver.close()
            logger.info("Neo4j connection closed")

neo4j_manager = Neo4jConfig()
# Proactively connect on module load (similiar to Redis)
neo4j_manager.connect()
