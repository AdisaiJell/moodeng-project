from sqlalchemy import Column,  Integer, String
from sqlalchemy.orm import relationship
from database import Base

class Wiki(Base):
    __tablename__ = "wiki"

    wikiId = Column(Integer, primary_key=True)
    title = Column(String)
    summary = Column(String)
    content = Column(String)

    # document = relationship("Document", back_populates="wiki") 

    # one-to-one: เอกสารหนึ่งตัวผูกกับวิกิเดียว
    document = relationship("Document", back_populates="wiki", uselist=False)
