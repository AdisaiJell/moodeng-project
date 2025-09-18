from sqlalchemy import Column, ForeignKey, Integer, String, LargeBinary, Boolean
from sqlalchemy.orm import relationship
from database import Base

class Document(Base):
    __tablename__ = "document"

    docId = Column(Integer, primary_key=True)
    docName = Column(String)
    ocrText = Column(String)
    ocrTextWithFormat = Column(String)
    status = Column(Boolean)
    file = Column(LargeBinary)  # ใช้ LargeBinary เก็บไฟล์s
    
    metaId = Column(Integer, ForeignKey("meta.metaId"))
    meta = relationship('Meta', back_populates='document')

    wikiId = Column(Integer, ForeignKey("wiki.wikiId"), nullable=True)
    wiki = relationship('Wiki', back_populates='document')
