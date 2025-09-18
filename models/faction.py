from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class Faction(Base):
    __tablename__ = "faction"

    factId = Column(Integer, primary_key=True)
    factionName = Column(String)
    meta = relationship('Meta', back_populates='faction')
    users = relationship("User", back_populates="faction")

