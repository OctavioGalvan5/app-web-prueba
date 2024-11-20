from werkzeug.security import check_password_hash, generate_password_hash
from flask_login import UserMixin


class User(UserMixin):

    def __init__(self, id, username, password, fullname="", credito=0) -> None:
        self.id = id
        self.username = username
        self.password = password
        self.fullname = fullname
        self.credito = credito  


    @classmethod
    def check_password(cls, hashed_password, password):
        return check_password_hash(hashed_password, password)



#password= "Belgrano1188"
#hashed_password = generate_password_hash(password, method='pbkdf2:sha256', salt_length=16)
#print(hashed_password)
# python models/entities/User.py