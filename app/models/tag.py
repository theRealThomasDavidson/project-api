from app import db
from sqlalchemy.orm import relationship

# Define the association table for the many-to-many relationship
project_tags = db.Table('project_tags',
    db.Column('project_id', db.Integer, db.ForeignKey('project.id'), primary_key=True),
    db.Column('tag_id', db.Integer, db.ForeignKey('tag.id'), primary_key=True)
)

class Tag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False, unique=True)
    projects = relationship("Project", secondary = 'project_tags')
    # Define the many-to-many relationship with the Project model
    def __init__(self, name):
        self.name = name

    def save(self, new_projects=None):
        existing_tag = Tag.query.filter_by(name=self.name).first()

        if existing_tag:
            if new_projects:
                for project in new_projects:
                    if project not in existing_tag.projects:
                        existing_tag.projects.append(project)
                    if existing_tag not in project.tags:
                        project.tags.append(existing_tag)

        else:
            if new_projects:
                for project in new_projects:
                    if project not in self.projects:
                        self.projects.append(project)
                    if self not in project.tags:
                        project.tags.append(self)

            db.session.add(self)

        db.session.commit()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def serialize(self):
        return {
            "id":self.id,
            "name": self.name, 
            "projects": [p.title for p in self.projects]
        }
    
