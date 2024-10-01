class Config:
     SECRET_KEY = 'b1f9c8f4a86b4e209c3457d0a6e3a4b2' # Indentación corregida

class DevelopmentConfig(Config):
    DEBUG = True

config = {
    'development': DevelopmentConfig
}
