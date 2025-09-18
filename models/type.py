from sqlalchemy import Column, Integer, String
from sqlalchemy.orm import relationship
from database import Base

class Type(Base):
    __tablename__ = "type"

    typeId = Column(Integer, primary_key=True)
    typeName = Column(String)
    meta = relationship("Meta", back_populates='type')