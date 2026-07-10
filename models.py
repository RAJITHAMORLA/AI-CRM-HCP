
from sqlalchemy import Column, Integer, String, Text
from database import Base


class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(100))
    interaction_type = Column(String(50))
    interaction_date = Column(String(20))
    interaction_time = Column(String(20))
    topics = Column(Text)
    sentiment = Column(String(50))
    followup = Column(Text)