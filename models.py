import datetime
from insta_cfg import SECRET_KEY
from app import db
from flask_security import RoleMixin, UserMixin
from sqlalchemy.orm import backref
from sqlalchemy.schema import UniqueConstraint
from passlib.apps import custom_app_context as pwd_context
from itsdangerous import (TimedJSONWebSignatureSerializer
                          as Serializer, BadSignature, SignatureExpired)
roles_users = db.Table(
    'roles_users',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('role_id', db.Integer(), db.ForeignKey('role.id'))
)

users_iprofiles = db.Table(
    'users_iprofiles',
    db.Column('user_id', db.Integer(), db.ForeignKey('user.id')),
    db.Column('iprofile_id', db.Integer(), db.ForeignKey('iprofile.id'))
)

class Role(db.Model, RoleMixin):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)

    def __str__(self):
        return self.name

    def __hash__(self):
        return hash(self.name)

class Tier(db.Model):
    id = db.Column(db.Integer(), primary_key=True)
    name = db.Column(db.String(80), unique=True)
    min_accounts = db.Column(db.Integer, nullable = False)
    max_accounts = db.Column(db.Integer, nullable = False)
    price_pm = db.Column(db.Float, nullable = False)
    paypal_button_link = db.Column(db.String(80), unique = True)

class User(db.Model, UserMixin):
    def hash_password(self, password):
        self.password = pwd_context.encrypt(password)

    def verify_password(self, password):
        return pwd_context.verify(password, self.password)

    def generate_auth_token(self, expiration=3600):
        s = Serializer(SECRET_KEY, expires_in=expiration)
        return s.dumps({'id': self.id})

    @staticmethod
    def verify_auth_token(token):
        s = Serializer(SECRET_KEY)
        data = None
        try:
            data = s.loads(token)
        except SignatureExpired:
            return None    # valid token, but expired
        except BadSignature:
            return None    # invalid token
        user = User.query.get(data['id'])
        return user

    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable = False)
    password = db.Column(db.String(130))
    username = db.Column(db.String(), nullable = False)
    start_date = db.Column(db.DateTime, default = datetime.datetime.utcnow)
    tier_id = db.Column(db.Integer, db.ForeignKey('tier.id'), nullable = False, default = 1)
    tier = db.relationship('Tier', backref=backref("tier", cascade="all,delete"), lazy = True)
    max_insta_accounts = db.Column(db.Integer, default = 3, nullable = False)
    profile_pic = db.Column(db.String(255), nullable = False, default = "dummy_profile_pic.jpg")
    roles = db.relationship(
        'Role',
        secondary=roles_users,
        backref=db.backref('users', lazy='dynamic'),
        lazy = 'dynamic'
    )
    iprofiles = db.relationship(
        'Iprofile',
        secondary=users_iprofiles,
        backref=db.backref('users', lazy='dynamic'),
        lazy = 'dynamic'
    )

class Iprofile(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    instagram_id = db.Column(db.String(255), unique=True, nullable = False)

class IprofileData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.DateTime)
    followers_count = db.Column(db.Integer, default = 0)
    following_count = db.Column(db.Integer, default = 0)
    media_likes = db.Column(db.Integer, default = 0)
    engagement_rate = db.Column(db.Float, default = 0.0)
    iprofile_id = db.Column(db.String(255), db.ForeignKey('iprofile.instagram_id'), nullable=False)
    iprofile = db.relationship('Iprofile', backref=backref("iprof_data", cascade="all,delete"), lazy = True)
    __table_args__ = (UniqueConstraint('iprofile_id', 'date', name='_profile_data_uc'),)
