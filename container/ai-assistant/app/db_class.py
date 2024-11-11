import chainlit.data as cl_data
from sqlalchemy import (
    create_engine,
    Column,
    String,
    JSON,
    DateTime,
    Integer,
    ForeignKey,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
from dotenv import load_dotenv
import os

# Used only for dev environment
load_dotenv()

MYSQL_ENDPOINT = str(os.getenv("MYSQL_ENDPOINT"))
MYSQL_DB_NAME = str(os.getenv("MYSQL_DB_NAME"))
MYSQL_USER = str(os.getenv("MYSQL_USER"))
MYSQL_TCP_PORT = str(os.getenv("MYSQL_TCP_PORT"))
MYSQL_PWD = str(os.getenv("MYSQL_PWD"))

Base = declarative_base()


class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    identifier = Column(String, unique=True, nullable=False)
    metadata = Column(JSON, nullable=False)
    createdAt = Column(DateTime, default=datetime.utcnow)


class Feedback(Base):
    __tablename__ = "feedbacks"
    id = Column(Integer, primary_key=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False)
    value = Column(Integer, nullable=False)  # 1 for positive, -1 for negative
    comment = Column(String)

    user = relationship("User")


class CustomDataLayer(cl_data.BaseDataLayer):
  def __init__(self, connection_string):
      self.engine = create_engine(connection_string)
      Base.metadata.create_all(self.engine)
      self.Session = sessionmaker(bind=self.engine)

  # Implement required methods from BaseDataLayer
  def create_user(self, identifier, metadata):
      session = self.Session()
      user = User(identifier=identifier, metadata=metadata)
      session.add(user)
      session.commit()
      session.close()

  def upsert_feedback(self, user_id: str, value: int, comment: str):
      session = self.Session()
      feedback = Feedback(user_id=user_id, value=value, comment=comment)
      session.add(feedback)
      session.commit()
      session.close()


# Set the custom data layer
connection_string = f"mysql+mysqlconnector://{MYSQL_USER}:{MYSQL_PWD}@{MYSQL_ENDPOINT}:{MYSQL_TCP_PORT}/{MYSQL_DB_NAME}"
cl_data._data_layer = CustomDataLayer(connection_string)
