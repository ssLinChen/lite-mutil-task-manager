# Base configuration
class Config:
    DEBUG = False
    TESTING = False
    REDIS_HOST = 'localhost'
    REDIS_PORT = 6379
    REDIS_DB = 0
    REDIS_PASSWORD = None
    
class DevelopmentConfig(Config):
    DEBUG = True
    
class TestingConfig(Config):
    TESTING = True
    REDIS_DB = 1
    
class ProductionConfig(Config):
    REDIS_HOST = 'redis-prod.example.com'
    REDIS_PASSWORD = 'your-redis-password'